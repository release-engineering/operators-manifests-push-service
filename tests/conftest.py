#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from collections import namedtuple
import re
import os
import shutil
from unittest.mock import Mock
import zipfile

from flexmock import flexmock
import operatorcourier.api
import pytest
import requests
import requests_mock

from omps.app import app
from omps.koji_util import KOJI, KojiUtil
from omps.settings import Config, TestConfig


ArchiveMeta = namedtuple('ArchiveMeta', ['path', 'files', 'pkg_name', 'valid'])
ManifestDirMeta = namedtuple('ManifestDirMeta', ['path', 'pkg_name', 'valid'])


@pytest.fixture()
def release_version():
    return "0.0.1"


@pytest.fixture
def client():
    client = app.test_client()

    yield client


@pytest.fixture
def datadir(tmpdir):
    """
    Fixture copies content of data directory to tmp dir to allow immutable work
    with test data

    :return: tmpdir data path
    """
    path = os.path.join(tmpdir, "data")
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    shutil.copytree(data_dir, path)
    return path


@pytest.fixture
def valid_manifest_dir(datadir):
    """Return metadata and path to manifest"""
    path = os.path.join(datadir, "marketplace_op_flat")
    return ManifestDirMeta(
        path=path,
        pkg_name='marketplace',
        valid=True
    )


@pytest.fixture
def valid_manifests_archive(datadir, tmpdir, valid_manifest_dir):
    """Construct valid operator manifest data zip archive"""
    path = os.path.join(tmpdir, 'test_archive.zip')

    files = os.listdir(valid_manifest_dir.path)

    with zipfile.ZipFile(path, 'w') as zip_archive:
        for name in files:
            zip_archive.write(
                os.path.join(valid_manifest_dir.path, name),
                arcname=name)

    return ArchiveMeta(
        path=path,
        files=sorted(files),
        pkg_name=valid_manifest_dir.pkg_name,
        valid=valid_manifest_dir.valid)


@pytest.fixture
def encrypted_zip_archive(datadir):
    """Path to the encrypted zip archive created in advance"""
    return os.path.join(datadir, 'encrypted.zip')


@pytest.fixture
def mocked_quay_io():
    """Mocking quay.io answers"""
    with requests_mock.Mocker() as m:
        m.get(
            re.compile(r'/cnr/api/v1/packages/.*'),
            status_code=404,
        )
        yield m


@pytest.fixture
def mocked_packages_delete_quay_io(release_version):
    """Mocking quay.io answers for retrieving and deleting packages"""
    with requests_mock.Mocker() as m:
        m.get(
            re.compile(r'/cnr/api/v1/packages/.*'),
            json=[
                {"release": release_version},
            ],
        )
        m.delete(
            re.compile(r'/cnr/api/v1/packages/.*'),
            status_code=requests.codes.ok,
        )
        yield m


@pytest.fixture
def mocked_op_courier_push():
    """Do not execute operator-courier push operation"""
    orig = operatorcourier.api.build_verify_and_push
    try:
        operatorcourier.api.build_verify_and_push = flexmock()
        yield
    finally:
        operatorcourier.api.build_verify_and_push = orig


@pytest.fixture
def mocked_koji_archive_download(valid_manifests_archive):
    """Mock KojiUtil.koji_download_manifest_archive to return valid archive"""
    def fake_download(nvr, target_fd):
        with open(valid_manifests_archive.path, 'rb') as zf:
            target_fd.write(zf.read())
            target_fd.flush()

    orig = KOJI.download_manifest_archive
    try:
        KOJI.download_manifest_archive = fake_download
        yield valid_manifests_archive
    finally:
        KOJI.download_manifest_archive = orig


@pytest.fixture
def mocked_koji_get_api_version():
    """Mock global KOJI.get_api_version to return valid version"""
    def fake_version():
        return 1

    orig = KOJI.get_api_version
    try:
        m = Mock(return_value=1)
        KOJI.get_api_version = m
        yield m
    finally:
        KOJI.get_api_version = orig


@pytest.fixture
def mocked_koji():
    """Return mocked KojiUtil with session"""
    conf = Config(TestConfig)
    ku = KojiUtil()
    ku.initialize(conf)
    ku._session = flexmock()
    return ku


@pytest.fixture
def mocked_quay_version():
    """Return mocked quay api version"""
    with requests_mock.Mocker() as m:
        m.get("/cnr/version", json={"cnr-api": "0.0.1-test"})
        yield m
