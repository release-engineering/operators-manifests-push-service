#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from collections import namedtuple

import pytest


EntrypointMeta = namedtuple('EntrypointMeta', 'url_path,org,repo,version,nvr')


@pytest.fixture(params=[
    True,  # endpoint with version
    False,  # endpoint without version
])
def endpoint_push_zipfile(request, release_version):
    """Returns URL for zipfile endpoints"""
    organization = 'testorg'
    repo = 'repo-Y'
    version = release_version if request.param else None

    url_path = f'/v1/{organization}/{repo}/zipfile'
    if version:
        url_path = f'{url_path}/{version}'

    yield EntrypointMeta(
        url_path=url_path, org=organization,
        repo=repo, version=version, nvr=None,
    )


@pytest.fixture(params=[
    True,  # endpoint with version
    False,  # endpoint without version
])
def endpoint_push_koji(request, release_version):
    """Returns URL for koji endpoints"""
    organization = 'testorg'
    repo = 'repo-Y'
    nvr = 'build-1.0.1-2'
    version = release_version if request.param else None

    url_path = f'/v1/{organization}/{repo}/koji/{nvr}'
    if version:
        url_path = f'{url_path}/{version}'

    yield EntrypointMeta(
        url_path=url_path, org=organization,
        repo=repo, version=version, nvr=nvr,
    )


@pytest.fixture(params=[
    True,  # endpoint with version
    False,  # endpoint without version
])
def endpoint_packages(request, release_version):
    """Returns URL for packages endpoints"""
    organization = 'testorg'
    repo = 'repo-Y'

    url_path = f'/v1/{organization}/{repo}'
    if request.param:
        url_path = f'{url_path}/{release_version}'

    yield EntrypointMeta(
        url_path=url_path, org=organization,
        repo=repo, version=release_version, nvr=None,
    )


@pytest.fixture()
def auth_header():
    return {'Authorization': 'random_token'}
