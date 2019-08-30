#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

"""Module related to quay operations"""

import re
from functools import total_ordering
import logging

from jsonschema import validate
import requests
from operatorcourier import api as courier_api

from .errors import (
    QuayPackageNotFound,
    QuayPackageError,
    QuayAuthorizationError,
    raise_for_courier_exception
)

logger = logging.getLogger(__name__)


def get_error_msg(res):
    """Returns error message from quay's response

    :param res: response
    :rtype: str
    :return: error message
    """
    try:
        msg = res.json()['error']['message']
    except Exception:
        msg = "Unknown error"
    return msg


@total_ordering
class ReleaseVersion:
    """Quay package version"""

    @classmethod
    def validate_version(cls, version):
        """Quay requires version format 'x.y.z' (example: 1.5.1-6)

        Due release autoincrement feature in OMPS lets make it stricter and
        support only "<int>.<int>.<int>"

        :param str version: release version
        :raises: ValueError when version doesn't follow required format
        """
        def _raise(msg):
            raise ValueError(
                "Version '{}' must be in format '<int>.<int>.<int>': {}".format(
                    version, msg
                ))

        assert isinstance(version, str)

        r_int_part = r"(0|[1-9][0-9]*)"
        regexp = r"^{p}\.{p}\.{p}$".format(p=r_int_part)
        match = re.match(regexp, version)
        if not match:
            _raise("must match regexp '{}'".format(regexp))

    @classmethod
    def from_str(cls, version):
        """Create version object from string

        :param str version: release version
        :raises: ValueError when version doesn't follow required format
        :return: version object
        :rtype: ReleaseVersion
        """
        cls.validate_version(version)
        x, y, z = version.split('.')
        return cls(int(x), int(y), int(z))

    def __init__(self, x, y, z):
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert isinstance(z, int)
        self._x = x
        self._y = y
        self._z = z

    @property
    def version_tuple(self):
        return self._x, self._y, self._z

    def _is_valid_operand(self, other):
        return hasattr(other, 'version_tuple')

    def __eq__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        return self.version_tuple == other.version_tuple

    def __lt__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        return self.version_tuple < other.version_tuple

    def __str__(self):
        return '{}.{}.{}'.format(self._x, self._y, self._z)

    def __repr__(self):
        return "{}({}, {}, {})".format(
            self.__class__.__name__, self._x, self._y, self._z
        )

    def increment(self):
        """Increments the most significant part of version by 1, zeroing
        other positions"""
        self._x += 1
        self._y = 0
        self._z = 0


class OrgManager:

    SCHEMA_ORGANIZATIONS = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Configuration for accessing Quay.io organizations",
        "type": "object",
        "patternProperties": {
            "^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$": {
                "description": "Organization name",
                "type": "object",
                "properties": {
                    "public": {
                        "description": "True if organization is public",
                        "type": "boolean",
                    },
                    "oauth_token": {
                        "description": "quay.io application oauth access token",
                        "type": "string",
                    },
                    "replace_registry": {
                        "description": "definitions how to replace registries",
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "old": {
                                    "type": "string",
                                    "description": "url fo registry to be "
                                                   "replaced",
                                },
                                "new": {
                                    "type": "string",
                                    "description": "new url of registry"
                                }
                            },
                            "required": ["old", "new"],
                        }
                    }
                },
            },
        },
        "uniqueItems": True,
        "additionalProperties": False,
    }

    @classmethod
    def validate_conf(cls, organizations):
        """Validate if config meets the schema expectations

        :param organizations: organizations config
        :raises jsonschema.ValidationError: when config doesn't meet criteria
        """
        validate(organizations, cls.SCHEMA_ORGANIZATIONS)

    def __init__(self):
        self._organizations = None
        self._timeout = None

    def initialize(self, config):
        self.validate_conf(config.organizations)
        self._organizations = config.organizations
        self._timeout = config.request_timeout
        for org_name, org_conf in self._organizations.items():
            logger.info(
                'Organization "%s" configured: public=%s, oauth_access=%s, '
                'replacing_registry_enabled=%s',
                org_name,
                org_conf.get('public', False),
                bool(org_conf.get('oauth_token')),
                bool(org_conf.get('replace_registry'))
            )

    def get_org(self, organization, cnr_token):
        org_config = self._organizations.get(organization, {})
        return QuayOrganization(
            organization,
            cnr_token,
            oauth_token=org_config.get('oauth_token'),
            public=org_config.get('public', False),
            timeout=self._timeout,
            replace_registry_conf=org_config.get('replace_registry')
        )


class QuayOrganization:
    """Class for operations on organization"""

    def __init__(
        self, organization, cnr_token, oauth_token=None, public=False,
        timeout=None, replace_registry_conf=None
    ):
        """
        :param organization: organization name
        :param cnr_token: organization login token (cnr endpoint)
        :param oauth_token: oauth_access_token
        :param public: organization is public
        :param int timeout: timeout for Quay requests in seconds
        """
        self.logger = logging.getLogger(
            '{0}[{1}]'.format(self.__class__.__name__, organization))
        self._quay_url = "https://quay.io"
        self._organization = organization
        self._token = cnr_token
        self._oauth_token = oauth_token
        self._public = public
        self._timeout = timeout
        self._replace_registry_conf = replace_registry_conf

    @property
    def public(self):
        return self._public

    @property
    def oauth_access(self):
        return bool(self._oauth_token)

    @property
    def organization(self):
        return self._organization

    @property
    def registry_replacing_enabled(self):
        return bool(self._replace_registry_conf)

    def replace_registries(self, text):
        """Returns new text with replaced registries

        This implementation does just simple text replacement

        :param str text: source text
        :rtype: str
        :return: text with replaced registries
        """
        if not self.registry_replacing_enabled:
            # no rules for replacing, return original
            return text

        for conf in self._replace_registry_conf:
            old = conf['old']
            new = conf['new']
            if old in text:
                self.logger.info("Replacing registry '%s' with '%s'", old, new)
                text = text.replace(old, new)

        return text

    def push_operator_manifest(self, repo, version, source_dir):
        """Build, verify and push operators artifact to quay.io registry

        If organization is "public=True" this method ensures that repo will be
        published.

        :param repo: name of repository
        :param version: release version
        :param source_dir: path to directory with manifests
        """
        try:
            courier_api.build_verify_and_push(
                self._organization, repo, version, self._token,
                source_dir=source_dir
            )
        except Exception as e:
            self._handle_courier_exception(e)
        else:
            if not self.public:
                self.logger.info(
                    "Organization '%s' is private, skipping publishing",
                    self._organization)
                return
            if not self.oauth_access:
                self.logger.error(
                    "Cannot publish repository %s, Oauth access is not "
                    "configured for organization %s",
                    repo, self._organization)
                return
            self.publish_repo(repo)

    def _handle_courier_exception(self, e):
        self.logger.error(
            "push_operator_manifest: Operator courier call failed: %s", e
        )
        msg = "Failed to push manifest: {}".format(e)
        raise_for_courier_exception(e, new_msg=msg)

    def _get_repo_content(self, repo):
        """Return content of repository"""
        endpoint = '/cnr/api/v1/packages/'
        url = '{q}{e}{o}/{r}'.format(
            q=self._quay_url,
            e=endpoint,
            o=self._organization,
            r=repo,
        )
        headers = {'Authorization': self._token}
        res = requests.get(url, headers=headers, timeout=self._timeout)

        res.raise_for_status()
        return res.json()

    def get_releases_raw(self, repo):
        """Get raw releases from quay, these release may not be compatible
        with OMPS versioning

        :param repo: repository name
        :raise QuayPackageNotFound: package doesn't exist
        :raise QuayPackageError: failed to retrieve info about package
        :return: Releases
        :rtype: List[str]
        """
        def _raise(exc):
            msg = ("Cannot retrieve information about package {}/{}: {}"
                   .format(self._organization, repo, exc))

            if isinstance(exc, requests.exceptions.HTTPError):
                if exc.response.status_code == 403:
                    try:
                        quay_response = exc.response.json()
                    except ValueError:
                        quay_response = {}
                    raise QuayAuthorizationError(msg, quay_response)
                elif exc.response.status_code == 404:
                    msg = ("Package {}/{} not found"
                           .format(self._organization, repo))
                    raise QuayPackageNotFound(msg)

            raise QuayPackageError(msg)

        try:
            res = self._get_repo_content(repo)
        except requests.exceptions.RequestException as e:
            _raise(e)

        releases = [package['release'] for package in res]
        return releases

    def get_releases(self, repo):
        """Get release versions (only valid)

        :param repo: repository name
        :raise QuayPackageNotFound: package doesn't exist
        :raise QuayPackageError: failed to retrieve info about package
        :return: valid releases
        :rtype: List[ReleaseVersion]
        """
        releases_raw = self.get_releases_raw(repo)

        releases = []
        for release in releases_raw:
            try:
                version = ReleaseVersion.from_str(release)
            except ValueError as e:
                # ignore incorrect versions
                self.logger.debug("Ignoring version: %s: %s", release, e)
                continue
            else:
                releases.append(version)

        return releases

    def get_latest_release_version(self, repo):
        """Get the latest release version

        :param repo: repository name
        :raise QuayPackageNotFound: package doesn't exist
        :raise QuayPackageError: failed to retrieve info about package
        :return: Latest release version
        :rtype: ReleaseVersion
        """
        releases = self.get_releases(repo)
        if not releases:
            # no valid versions found, assume that this will be first package
            # uploaded by service
            raise QuayPackageNotFound(
                "Package {}/{} has not valid versions uploaded".format(
                    self._organization, repo
                )
            )

        return max(self.get_releases(repo))

    def delete_release(self, repo, version):
        """
        Delete specified version of release from repository

        :param str repo: name of repository
        :param ReleaseVersion|str version: version of release
        :raises QuayPackageNotFound: when package is not found
        :raises QuayPackageError: when an error happened during removal
        """
        endpoint = '/cnr/api/v1/packages/{org}/{repo}/{version}/helm'
        url = '{q}{e}'.format(
            q=self._quay_url,
            e=endpoint.format(
                org=self._organization,
                repo=repo,
                version=version,
            )
        )
        headers = {'Authorization': self._token}

        self.logger.info(
            'Deleting release %s/%s, v:%s',
            self._organization, repo, version)

        r = requests.delete(url, headers=headers, timeout=self._timeout)

        if r.status_code != requests.codes.ok:

            msg = get_error_msg(r)

            if r.status_code == requests.codes.not_found:
                self.logger.info("Delete release (404): %s", msg)
                raise QuayPackageNotFound(msg)

            self.logger.error("Delete release (%s): %s", r.status_code, msg)
            raise QuayPackageError(msg)

    def publish_repo(self, repo):
        """Make repository public

        Needs OAUTH access

        :param str repo: repository name
        """
        assert self.oauth_access, "Needs Oauth access"
        endpoint = '/api/v1/repository/{org}/{repo}/changevisibility'.format(
            org=self._organization,
            repo=repo,
        )
        url = '{q}{e}'.format(q=self._quay_url, e=endpoint)
        data = {
            "visibility": "public",
        }
        headers = {
            "Authorization": "Bearer {}".format(self._oauth_token)
        }
        self.logger.info("Publishing repository %s", repo)
        r = requests.post(url, headers=headers, json=data, timeout=self._timeout)
        if r.status_code != requests.codes.ok:
            msg = get_error_msg(r)
            self.logger.error("Publishing repository: %s", msg)
            raise QuayPackageError(msg)


def get_cnr_api_version(timeout):
    """Returns quay's CNR api version

    :param int timeout: timeout for Quay requests in seconds
    :raises: HTTPError if version cannot be fetched
    :rtype: str
    :returns: API version
    """
    url = "https://quay.io/cnr/version"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()['cnr-api']


ORG_MANAGER = OrgManager()
