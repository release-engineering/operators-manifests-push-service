#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import koji
import requests

from omps import constants
from omps.errors import (
    KojiError,
    KojiManifestsArchiveNotFound,
    KojiNVRBuildNotFound,
    KojiNotAnOperatorImage,
)


class KojiUtil:
    """Utils for koji"""

    def __init__(self):
        self._session = None
        self._kojihub_url = None
        self._kojiroot_url = None

    def initialize(self, conf):
        self._kojihub_url = conf.kojihub_url
        self._kojiroot_url = conf.kojiroot_url
        opts = dict()
        if conf.request_timeout is not None:
            opts['timeout'] = conf.request_timeout
        self._session = koji.ClientSession(self._kojihub_url, opts=opts)

        if not self._kojihub_url.endswith('/'):
            self._kojihub_url += '/'

        if not self._kojiroot_url.endswith('/'):
            self._kojiroot_url += '/'

    @property
    def session(self):
        return self._session

    def _file_download(self, url, target_fd):
        # inspired by: https://stackoverflow.com/a/16696317
        with requests.get(url, stream=True) as r:
            try:
                r.raise_for_status()
            except Exception as e:
                raise KojiError(str(e))
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    target_fd.write(chunk)
        target_fd.flush()

    def download_manifest_archive(self, nvr, target_fd):
        """Downloads operators

        :param str koji_url: url for koji connection
        :param str nvr: koji image nvr
        :param FileObject target_fd: output file object (opened in binary mode)
        """
        metadata = self.session.getBuild(nvr)
        if metadata is None:
            raise KojiNVRBuildNotFound("NVR not found: {}".format(nvr))

        try:
            key = constants.KOJI_OPERATOR_MANIFESTS_ARCHIVE_KEY
            filename = metadata['extra'][key]
        except KeyError:
            raise KojiNotAnOperatorImage("Not an operator image: {}".format(nvr))

        # OSBS stores manifests archive in zip files (will be moved in future)
        logs = self.session.getBuildLogs(metadata['build_id'])
        path = None
        for logfile in logs:
            if logfile['name'] == filename:
                path = logfile['path']
                break

        if path is None:
            raise KojiManifestsArchiveNotFound(
                "Expected archive '{}' with manifests not found in build: "
                "{}".format(filename, nvr))

        url = self._kojiroot_url + path
        self._file_download(url, target_fd)

    def get_api_version(self):
        """Returns API version of koji

        :rtype: int
        :return: Koji API version
        """
        try:
            ver = self.session.getAPIVersion()
        except Exception as e:
            raise KojiError(str(e))

        return ver


KOJI = KojiUtil()
