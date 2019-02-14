#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from collections import namedtuple
import os
import shutil
import zipfile

import pytest

from omps.app import app


EntrypointMeta = namedtuple('EntrypointMeta', 'url_path,org,repo,version')


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


@pytest.fixture(params=[
    True,  # endpoint with version
    False,  # endpoint without version
])
def endpoint_push_zipfile(request):
    """Returns URL for zipfile endpoints"""
    organization = 'organization-X'
    repo = 'repo-Y'
    version = '0.0.1' if request.param else None

    url_path = '/push/{}/{}/zipfile'.format(organization, repo)
    if version:
        url_path = '{}/{}'.format(url_path, version)

    yield EntrypointMeta(
        url_path=url_path, org=organization,
        repo=repo, version=version
    )
