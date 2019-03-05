#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import pytest
import requests


def test_delete_released_package(
        client, valid_manifests_archive, endpoint_packages,
        mocked_packages_delete_quay_io, auth_header):
    """Test REST API for deleting released operators manifest packages"""

    rv = client.delete(
        endpoint_packages.url_path,
        headers=auth_header,
    )

    assert rv.status_code == requests.codes.ok, rv.get_json()
    expected = {
        'organization': endpoint_packages.org,
        'repo': endpoint_packages.repo,
        'deleted': ["0.0.1"],
    }
    assert rv.get_json() == expected


@pytest.mark.parametrize('endpoint', [
    '/v1/organization-X/repo-Y',
    '/v1/organization-X/repo-Y/1.0.1',
])
@pytest.mark.parametrize('method', [
    'GET', 'PATCH' 'PUT', 'HEAD', 'POST', 'TRACE',
])
def test_method_not_allowed(client, endpoint, method):
    """Specified endpoints currently support only DELETE method, test if other
    HTTP methods returns proper error code

    Method OPTIONS is excluded from testing due its special meaning
    """
    rv = client.open(endpoint, method=method)
    assert rv.status_code == requests.codes.method_not_allowed


@pytest.mark.parametrize('endpoint', [
    '/',
    '/v1',
    '/v1/organization-X/',
    '/v1/organization-X/repo-Y/version-Z/extra-something',
])
def test_404_for_mistyped_entrypoints(client, endpoint):
    """Test if HTTP 404 is returned for unexpected endpoints"""
    rv = client.post(endpoint)
    assert rv.status_code == requests.codes.not_found
    rv_json = rv.get_json()
    assert rv_json['error'] == 'NotFound'
    assert rv_json['status'] == requests.codes.not_found
