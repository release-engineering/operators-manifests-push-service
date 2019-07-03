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
    PKGNAME = "test_package"
    VERSION = "1.0"
    RELEASE = "1"
    FILEPATH_ARCHIVE_IN_LOGS = 'path/to/archive.zip'

    ARCHIVE_KOJI_PATH = (
        f'/packages/{PKGNAME}/{VERSION}/{RELEASE}/'
        f'files/operator-manifests/{FILENAME}'
    )
    META_ARCHIVE_IN_LOGS = {
        "extra": {'operator_manifests_archive': FILENAME},
        "build_id": 12345,
    }

    def _mock_getBuild(self, mocked_koji, rdata=None):
        if rdata is None:
            meta = {
                "name": self.PKGNAME,
                "version": self.VERSION,
                "release": self.RELEASE,
                "extra": {
                    'typeinfo': {
                        'operator-manifests': {
                            'archive': self.FILENAME
                        },
                    },
                },
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
                    "path": self.FILEPATH_ARCHIVE_IN_LOGS,
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
        """(Deprecated) Test if proper exception is raised when build miss the
        archive file"""
        self._mock_getBuild(mocked_koji, rdata=self.META_ARCHIVE_IN_LOGS)
        logs = [
            {
                'name': 'something_else',
                "path": "path/to/something_else.log"
            },
        ]
        self._mock_getBuildLogs(mocked_koji, rdata=logs)

        with pytest.raises(KojiManifestsArchiveNotFound):
            mocked_koji.download_manifest_archive('test', None)

    def test_download_manifest_archive_download_error_logs(self, mocked_koji):
        """(Deprecated) Test if proper exception is raised when download fails"""
        self._mock_getBuild(mocked_koji, rdata=self.META_ARCHIVE_IN_LOGS)
        self._mock_getBuildLogs(mocked_koji)

        with requests_mock.Mocker() as m:
            m.get(
                mocked_koji._kojiroot_url + self.FILEPATH_ARCHIVE_IN_LOGS,
                status_code=requests.codes.not_found)
            with pytest.raises(KojiError):
                with tempfile.NamedTemporaryFile() as target_f:
                    mocked_koji.download_manifest_archive('test', target_f)

    def test_download_manifest_archive_download_error(self, mocked_koji):
        """Test if proper exception is raised when download fails"""
        self._mock_getBuild(mocked_koji)

        with requests_mock.Mocker() as m:
            m.get(
                mocked_koji._kojiroot_url + self.ARCHIVE_KOJI_PATH,
                status_code=requests.codes.not_found)
            with pytest.raises(KojiError):
                with tempfile.NamedTemporaryFile() as target_f:
                    mocked_koji.download_manifest_archive('test', target_f)

    def test_download_manifest_archive_logs(self, mocked_koji):
        """(Deprecated) Positive test, archive stored in logs everything
        should work"""
        self._mock_getBuild(mocked_koji, rdata=self.META_ARCHIVE_IN_LOGS)
        self._mock_getBuildLogs(mocked_koji)

        data = b"I'm a zip archive!"

        with requests_mock.Mocker() as m:
            m.get(
                mocked_koji._kojiroot_url + self.FILEPATH_ARCHIVE_IN_LOGS,
                content=data)
            with tempfile.NamedTemporaryFile() as target_f:
                mocked_koji.download_manifest_archive('test', target_f)
                target_f.seek(0)
                assert target_f.read() == data

    def test_download_manifest_archive(self, mocked_koji):
        """Positive test, archive stored in dedicated build type"""
        self._mock_getBuild(mocked_koji)

        data = b"I'm a zip archive!"

        with requests_mock.Mocker() as m:
            m.get(
                mocked_koji._kojiroot_url + self.ARCHIVE_KOJI_PATH,
                content=data)
            with tempfile.NamedTemporaryFile() as target_f:
                mocked_koji.download_manifest_archive('test', target_f)
                target_f.seek(0)
                assert target_f.read() == data

    def test_get_api_version(self, mocked_koji):
        """Test get_api_version method"""

        version = 1
        mocked_koji.session.should_receive('getAPIVersion').and_return(version)

        assert mocked_koji.get_api_version() == version

    def test_get_api_version_error(self, mocked_koji):
        """Test if get_api_version method raises proper exception"""
        msg = "something wrong happened"
        (mocked_koji.session
         .should_receive('getAPIVersion')
         .and_raise(Exception(msg))
         )

        with pytest.raises(KojiError) as exc_info:
            mocked_koji.get_api_version()

        assert msg in str(exc_info.value)
