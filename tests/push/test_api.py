#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from io import BytesIO

import pytest


def test_push_zipfile(client, valid_manifests_archive):
    """Test REST API for pushing operators form zipfile"""
    with open(valid_manifests_archive, 'rb') as f:
        data = {
            'file': (f, f.name),
        }
        rv = client.post(
            '/push/organization-X/repo-Y/zipfile',
            data=data,
            content_type='multipart/form-data',
        )

    assert rv.status_code == 200, rv.get_json()
    expected = {
        'organization': 'organization-X',
        'repo': 'repo-Y',
        'msg': 'Not Implemented. Testing only',
        'extracted_files': ['empty.yml'],
    }
    assert rv.get_json() == expected


@pytest.mark.parametrize('filename', (
    'test.json',  # test invalid extension
    'test.zip',  # test invalid content
))
def test_push_zipfile_invalid_file(client, filename):
    """Test if proper error is returned when no zip file is being attached"""
    data = {
        'file': (BytesIO(b'randombytes'), filename),
    }
    rv = client.post(
        '/push/organization-X/repo-Y/zipfile',
        data=data,
        content_type='multipart/form-data',
    )

    assert rv.status_code == 400, rv.get_json()
    rv_json = rv.get_json()
    assert rv_json['status'] == 400
    assert rv_json['error'] == 'OMPSUploadedFileError'


def test_push_zipfile_no_file(client):
    """Test if proper error is returned when no file is being attached"""
    rv = client.post('/push/organization-X/repo-Y/zipfile')
    assert rv.status_code == 400, rv.get_json()
    rv_json = rv.get_json()
    assert rv_json['status'] == 400
    assert rv_json['error'] == 'OMPSExpectedFileError'


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
