#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import re
import os
import shutil
import zipfile

from flexmock import flexmock
import operatorcourier.api
import pytest
import requests
import requests_mock

from omps.app import app
from omps.koji_util import KOJI, KojiUtil
from omps.settings import Config, TestConfig


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
def valid_manifests_archive(datadir, tmpdir):
    """Construct valid operator manifest data zip archive"""

    path = os.path.join(tmpdir, 'test_archive.zip')

    with zipfile.ZipFile(path, 'w') as zip_archive:
        # for now we are happy just with empty file in that archive
        zip_archive.write(
            os.path.join(datadir, 'empty.yml'),
            arcname='empty.yml')

    return path


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
        with open(valid_manifests_archive, 'rb') as zf:
            target_fd.write(zf.read())
            target_fd.flush()

    orig = KOJI.download_manifest_archive
    try:
        KOJI.download_manifest_archive = fake_download
        yield
    finally:
        KOJI.download_manifest_archive = orig


@pytest.fixture
def mocked_koji():
    """Return mocked KojiUtil with session"""
    conf = Config(TestConfig)
    ku = KojiUtil()
    ku.initialize(conf)
    ku._session = flexmock()
    return ku
