#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from collections import namedtuple

import pytest


EntrypointMeta = namedtuple('EntrypointMeta', 'url_path,org,repo,version')


@pytest.fixture(params=[
    True,  # endpoint with version
    False,  # endpoint without version
])
def endpoint_push_zipfile(request, release_version):
    """Returns URL for zipfile endpoints"""
    organization = 'testorg'
    repo = 'repo-Y'
    version = release_version if request.param else None

    url_path = '/v1/{}/{}/zipfile'.format(organization, repo)
    if version:
        url_path = '{}/{}'.format(url_path, version)

    yield EntrypointMeta(
        url_path=url_path, org=organization,
        repo=repo, version=version
    )


@pytest.fixture(params=[
    True,  # endpoint with version
    False,  # endpoint without version
])
def endpoint_packages(request, release_version):
    """Returns URL for packages endpoints"""
    organization = 'testorg'
    repo = 'repo-Y'

    url_path = '/v1/{}/{}'.format(organization, repo)
    if request.param:
        url_path = '{}/{}'.format(url_path, release_version)

    yield EntrypointMeta(
        url_path=url_path, org=organization,
        repo=repo, version=release_version
    )
