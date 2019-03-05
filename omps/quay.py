#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

"""Module related to quay operations"""

import re
from functools import total_ordering
import logging

import requests
from operatorcourier import api as courier_api

from .errors import (
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
                logger.debug("Ignoring version: %s: %s", release, e)
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

        logger.info('Deleting release %s/%s, v:%s',
                    self._organization, repo, version)

        r = requests.delete(url, headers=headers)

        if r.status_code != requests.codes.ok:

            try:
                msg = r.json()['error']['message']
            except Exception:
                msg = "Unknown error"

            if r.status_code == requests.codes.not_found:
                logger.info("Delete release (404): %s", msg)
                raise QuayPackageNotFound(msg)

            logger.error("Delete release (%s): %s", r.status_code, msg)
            raise QuayPackageError(msg)
