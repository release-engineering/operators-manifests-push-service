#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import os
import shutil
import zipfile

import pytest

from omps.app import app


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
    path =  os.path.join(tmpdir, "data")
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
