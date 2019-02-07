#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import pytest


def test_push_zipfile(client):
    """Test REST API for pushing operators form zipfile"""
    rv = client.post('/push/organization-X/repo-Y/zipfile')
    assert rv.status_code == 200
    expected = {
        'organization': 'organization-X',
        'repo': 'repo-Y',
        'msg': 'Not Implemented. Testing only'
    }
    assert rv.get_json() == expected


def test_push_koji_nvr(client):
    """Test REST API for pushing operators form koji by NVR"""
    rv = client.post('/push/organization-X/repo-Y/koji/nvr-Z')
    assert rv.status_code == 200
    expected = {
        'organization': 'organization-X',
        'repo': 'repo-Y',
        'nvr': 'nvr-Z',
        'msg': 'Not Implemented. Testing only'
    }
    assert rv.get_json() == expected


@pytest.mark.parametrize('endpoint', [
    '/push/organization-X/repo-Y/zipfile',
    '/push/organization-X/repo-Y/koji/nvr-Z',
])
@pytest.mark.parametrize('method', [
    'GET', 'PATCH' 'PUT', 'HEAD', 'DELETE', 'TRACE',
])
def test_method_not_allowed(client, endpoint, method):
    """Specified endpoints currently support only POST method, test if other
    HTTP methods returns proper error code

    Method OPTIONS is excluded from testing due its special meaning
    """
    rv = client.open(endpoint, method=method)
    assert rv.status_code == 405


@pytest.mark.parametrize('endpoint', [
    '/',
    '/push',
    '/push/organization-X/repo-Y/koji/',
    '/push/organization-X/repo-Y/zipfile/extra-something',
])
def test_404_for_mistyped_entrypoints(client, endpoint):
    """Test if HTTP 404 is returned for unexpected endpoints"""
    rv = client.post(endpoint)
    assert rv.status_code == 404
    rv_json = rv.get_json()
    assert rv_json['error'] == 'NotFound'
    assert rv_json['status'] == 404
