#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import tempfile

import pytest
import requests
import requests_mock

from omps.errors import (
    KojiNVRBuildNotFound,
    KojiNotAnOperatorImage,
    KojiManifestsArchiveNotFound,
    KojiError,
)


class TestKojiUtil:
    """Tests for KojiUtil class"""

    FILENAME = 'testfile.zip'
    FILEPATH = 'path/to/archive.zip'

    def _mock_getBuild(self, mocked_koji, rdata=None):
        if rdata is None:
            meta = {
                "extra": {'operator_manifests_archive': self.FILENAME},
                "build_id": 12345,
            }
        else:
            meta = rdata
        mocked_koji.session.should_receive('getBuild').and_return(meta)

    def _mock_getBuildLogs(self, mocked_koji, rdata=None):
        if rdata is None:
            logs = [
                {
                    'name': self.FILENAME,
                    "path": self.FILEPATH,
                },
            ]
        else:
            logs = rdata

        (mocked_koji.session
         .should_receive('getBuildLogs')
         .and_return(logs))

    def test_download_manifest_archive_no_nvr(self, mocked_koji):
        """Test if proper exception is raised when NVR is not found in koji"""
        mocked_koji.session.should_receive('getBuild').and_return(None).once()

        with pytest.raises(KojiNVRBuildNotFound):
            mocked_koji.download_manifest_archive('test', None)

    def test_download_manifest_archive_no_operator_img(self, mocked_koji):
        """Test if proper exception is raised when build is not an operator
        image"""
        self._mock_getBuild(mocked_koji, rdata={"extra": {}})

        with pytest.raises(KojiNotAnOperatorImage):
            mocked_koji.download_manifest_archive('test', None)

    def test_download_manifest_archive_no_file(self, mocked_koji):
        """Test if proper exception is raised when build miss the archive
        file"""
        self._mock_getBuild(mocked_koji)
        logs = [
            {
                'name': 'something_else',
                "path": "path/to/something_else.log"
            },
        ]
        self._mock_getBuildLogs(mocked_koji, rdata=logs)

        with pytest.raises(KojiManifestsArchiveNotFound):
            mocked_koji.download_manifest_archive('test', None)

    def test_download_manifest_archive_download_error(self, mocked_koji):
        """Test if proper exception is raised when download fails"""
        self._mock_getBuild(mocked_koji)
        self._mock_getBuildLogs(mocked_koji)

        with requests_mock.Mocker() as m:
            m.get(
                mocked_koji._kojiroot_url + self.FILEPATH,
                status_code=requests.codes.not_found)
            with pytest.raises(KojiError):
                with tempfile.NamedTemporaryFile() as target_f:
                    mocked_koji.download_manifest_archive('test', target_f)

    def test_download_manifest_archive(self, mocked_koji):
        """Positive test, everything should work now"""
        self._mock_getBuild(mocked_koji)
        self._mock_getBuildLogs(mocked_koji)

        data = b"I'm a zip archive!"

        with requests_mock.Mocker() as m:
            m.get(
                mocked_koji._kojiroot_url + self.FILEPATH,
                content=data)
            with tempfile.NamedTemporaryFile() as target_f:
                mocked_koji.download_manifest_archive('test', target_f)
                target_f.seek(0)
                assert target_f.read() == data
