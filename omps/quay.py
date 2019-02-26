#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

"""Module related to quay operations"""

import re
from functools import total_ordering
import logging

import jsonschema
import requests
from operatorcourier import api as courier_api

from .errors import (
    QuayLoginError,
    OMPSOrganizationNotFound,
    QuayCourierError,
    QuayPackageNotFound,
    QuayPackageError,
)

logger = logging.getLogger(__name__)


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


class QuayOrganizationManager:
    """Class responsible for handling configured organizations"""

    SCHEMA_ORGANIZATIONS = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Configuration for accessing Quay.io organizations",
        "type": ["object"],
        "patternProperties": {
            "^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}": {
                "description": "Organization name",
                "type": "object",
                "properties": {
                    "username": {
                        "description": "quay.io username",
                        "type": "string",
                    },
                    "password": {
                        "description": "quay.io password",
                        "type": "string",
                    },
                },
                "required": ['username', 'password'],
            },
        },
        "uniqueItems": True,
        "additionalProperties": False,
    }

    @classmethod
    def validate_config(cls, organizations):
        """Validate quay organizations configuration

        :param organizations: dictionary with configuration
        :raises jsonschema.ValidationError: when configuration doesn't meet
            expectations
        """
        jsonschema.validate(organizations, cls.SCHEMA_ORGANIZATIONS)

    def __init__(self):
        self._organizations = {}
        self._quay_url = "https://quay.io"

    def init_from_config(self, config):
        """Initialize object from config"""
        self.validate_config(config.quay_organizations)
        self._organizations = config.quay_organizations
        if not self._organizations:
            logger.error('No organizations configured')

    def _login(self, username, password):
        endpoint = '/cnr/api/v1/users/login'
        data = {
            "user": {
                "username": username,
                "password": password,
            },
        }
        url = self._quay_url + endpoint
        r = requests.post(url, json=data)

        if r.status_code != requests.codes.ok:
            details = 'unknown details'
            try:
                details = r.json()['error']
            except Exception:
                pass
            msg = 'Failed to login: {} ({})'.format(r.status_code, details)
            logger.error(msg)
            raise QuayLoginError(msg)

        content = r.json()
        if 'token' not in content:
            raise QuayLoginError("Answer from quay doesn't contain token")
        return content['token']

    def organization_login(self, organization):
        """Login to organization and return QuayOrganization object

        :param organization: organization name
        :return: QuayOrganization object
        """
        org_config = self._organizations.get(organization)
        if org_config is None:
            raise OMPSOrganizationNotFound(
                "Organization '{}' not found in configuration".format(
                    organization
                )
            )
        token = self._login(org_config['username'], org_config['password'])
        return QuayOrganization(organization, token)


class QuayOrganization:
    """Class for operations on organization"""

    def __init__(self, organization, token):
        """
        :param organization: organization name
        :param token: organization login token
        """
        self._quay_url = "https://quay.io"
        self._organization = organization
        self._token = token

    def push_operator_manifest(self, repo, version, source_dir):
        try:
            courier_api.build_verify_and_push(
                self._organization, repo, version, self._token,
                source_dir=source_dir
            )
        except Exception as e:
            logger.error(
                "push_operator_manifest: Operator courier call failed: %s", e
            )
            raise QuayCourierError("Failed to push manifest: {}".format(e))

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
        res = requests.get(url, headers=headers)

        res.raise_for_status()
        return res.json()

    def get_latest_release_version(self, repo):
        """Get the latest release version

        :param repo: repository name
        :raise QuayPackageNotFound: package doesn't exist
        :raise QuayPackageError: failed to retrieve info about package
        :return: Latest release version
        :rtype: PackageRelease
        """
        def _raise(exc):
            raise QuayPackageError(
                "Cannot retrieve information about package {}/{}: {}".format(
                    self._organization, repo, exc
                ))

        try:
            res = self._get_repo_content(repo)
        except requests.exceptions.HTTPError as http_e:
            if http_e.response.status_code == 404:
                raise QuayPackageNotFound(
                    "Package {}/{} not found".format(
                        self._organization, repo
                    )
                )
            _raise(http_e)
        except requests.exceptions.RequestException as e:
            _raise(e)

        releases = []
        for package in res:
            release = package['release']
            try:
                version = ReleaseVersion.from_str(release)
            except ValueError as e:
                # ignore incorrect versions
                logger.debug("Ignoring version: %s: %s", release, e)
                continue
            else:
                releases.append(version)

        if not releases:
            # no valid versions found, assume that this will be first package
            # uploaded by service
            raise QuayPackageNotFound(
                    "Package {}/{} has not valid versions uploaded".format(
                        self._organization, repo
                    )
                )

        return max(releases)


QUAY_ORG_MANAGER = QuayOrganizationManager()
