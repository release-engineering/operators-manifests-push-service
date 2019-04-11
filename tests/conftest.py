#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from collections import namedtuple
from distutils import dir_util
import re
import os
import shutil
import tempfile
from unittest.mock import Mock
import zipfile

from flexmock import flexmock
import operatorcourier.api
import pytest
import requests
import requests_mock

from omps.app import app
from omps.greenwave import GREENWAVE
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


@pytest.fixture(params=[
    ('marketplace_op_flat', 'marketplace'),
    ('etcd_op_nested', 'etcd'),
])
def valid_manifest_dir(request, datadir):
    """Return metadata and path to manifest"""
    manifest_dir_name, pkg_name = request.param
    path = os.path.join(datadir, manifest_dir_name)
    return ManifestDirMeta(
        path=path,
        pkg_name=pkg_name,
        valid=True
    )


@pytest.fixture
def valid_manifest_flatten_dir(valid_manifest_dir):
    """Most operator-courier operations require flatten dir structure"""
    with tempfile.TemporaryDirectory() as tmpdir:
        operatorcourier.api.flatten(valid_manifest_dir.path, tmpdir)
        if not os.listdir(tmpdir):
            # if dest dir is empty, it means that flatten did noop and source dir
            # has already flat structure
            dir_util.copy_tree(valid_manifest_dir.path, tmpdir)

        yield ManifestDirMeta(
            path=tmpdir,
            pkg_name=valid_manifest_dir.pkg_name,
            valid=True
        )


@pytest.fixture
def valid_manifests_archive(datadir, tmpdir, valid_manifest_dir):
    """Construct valid operator manifest data zip archive"""
    path = os.path.join(tmpdir, 'test_archive.zip')

    start = valid_manifest_dir.path
    res_files = []

    with zipfile.ZipFile(path, 'w') as zip_archive:
        for root, dirs, files in os.walk(start):
            for name in files:
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, start)
                zip_archive.write(full_path, arcname=rel_path)
                res_files.append(rel_path)

    return ArchiveMeta(
        path=path,
        files=sorted(res_files),
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
def op_courier_push_raising():
    """Use as a context manager to make courier raise a specific exception
    from build_verify_and_push()

    e.g.:
        with op_courier_push_raising(OpCourierBadBundle(*exc_args)):
            quay_org.push_operator_manifest(*push_args)
    """
    class CourierPushCM:
        def __init__(self, exception):
            self.e = exception
            self.original_api = operatorcourier.api
            self.mocked_api = flexmock(self.original_api)

        def __enter__(self):
            (self.mocked_api
                .should_receive('build_verify_and_push')
                .and_raise(self.e))
            operatorcourier.api = self.mocked_api

        def __exit__(self, *args):
            operatorcourier.api = self.original_api

    return CourierPushCM


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


@pytest.fixture
def mocked_greenwave():
    """Mock global GREENWAVE.check_build to pass without connecting to
    Greenwave"""

    orig = GREENWAVE.check_build
    orig_url = GREENWAVE._url
    try:
        m = Mock(return_value=None)
        GREENWAVE.check_build = m
        # we have to specify URL to fake GREENWAVE.enabled property
        GREENWAVE._url = "https://test-greenwave.example.com"
        yield m
    finally:
        GREENWAVE.check_build = orig
        GREENWAVE._url = orig_url
