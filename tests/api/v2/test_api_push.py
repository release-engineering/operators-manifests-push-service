#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from io import BytesIO
from textwrap import dedent
from unittest import mock
import os.path

import flexmock
import requests
import pytest

from omps import constants
from omps.quay import QuayOrganization


def test_push_zipfile(
        client, valid_manifests_archive, endpoint_push_zipfile,
        mocked_quay_io, mocked_op_courier_push, auth_header):
    """Test REST API for pushing operators form zipfile"""
    with open(valid_manifests_archive.path, 'rb') as f:
        data = {
            'file': (f, f.name),
        }
        rv = client.post(
            endpoint_push_zipfile.url_path,
            headers=auth_header,
            data=data,
            content_type='multipart/form-data',
        )

    assert rv.status_code == 200, rv.get_json()
    expected = {
        'organization': endpoint_push_zipfile.org,
        'repo': valid_manifests_archive.pkg_name,
        'version': endpoint_push_zipfile.version or constants.DEFAULT_RELEASE_VERSION,
        'extracted_files': valid_manifests_archive.files,
    }
    assert rv.get_json() == expected


@pytest.mark.parametrize(('suffix_func', 'expected_pkg_name_func'), (
    (lambda _: '-suffix', lambda x: x + '-suffix'),
    (lambda x: x, lambda x: x),
    (lambda x: '', lambda x: x),
))
@mock.patch('omps.api.v1.push.ORG_MANAGER')
def test_push_zipfile_with_package_name_suffix(
        mocked_org_manager, client, valid_manifests_archive,
        endpoint_push_zipfile, mocked_quay_io, mocked_op_courier_push,
        auth_header, suffix_func, expected_pkg_name_func):
    """Test REST API for pushing operators form zipfile with package_name_suffix"""
    original_pkg_name = valid_manifests_archive.pkg_name
    expected_pkg_name = expected_pkg_name_func(original_pkg_name)

    mocked_org_manager.get_org.return_value = QuayOrganization(
        endpoint_push_zipfile.org, 'cnr_token',
        package_name_suffix=suffix_func(original_pkg_name))

    def verify_modified_package_name(repo, version, source_dir):
        # The modified YAML file should retain comments and defined order. The
        # only modification should be the package name.
        if valid_manifests_archive.pkg_name == 'marketplace':
            pkg_manifest = (
                'deploy/chart/catalog_resources/rh-operators/'
                'marketplace.v0.0.1.clusterserviceversion.yaml')
            expected_packages_yaml = dedent("""\
                #! package-manifest: {pkg_manifest}
                packageName: {pkg_name}
                channels:
                - name: alpha
                  currentCSV: marketplace-operator.v0.0.1
                """)
            packages_yaml_path = os.path.join(source_dir, 'packages.yaml')
        elif valid_manifests_archive.pkg_name == 'etcd':
            pkg_manifest = (
                './deploy/chart/catalog_resources/rh-operators/'
                'etcdoperator.v0.9.2.clusterserviceversion.yaml')
            expected_packages_yaml = dedent("""\
                #! package-manifest: {pkg_manifest}
                packageName: {pkg_name}
                channels:
                - name: alpha
                  currentCSV: etcdoperator.v0.9.2
                """)
            packages_yaml_path = os.path.join(source_dir, 'etcd.package.yaml')
        else:
            raise ValueError(
                'Unsupported manifests archive, {}'.format(valid_manifests_archive))
        expected_packages_yaml = expected_packages_yaml.format(
            pkg_manifest=pkg_manifest,
            pkg_name=expected_pkg_name)
        with open(packages_yaml_path) as f:
            assert f.read() == expected_packages_yaml

    flexmock(QuayOrganization)\
        .should_receive('push_operator_manifest')\
        .replace_with(verify_modified_package_name)\
        .once()

    with open(valid_manifests_archive.path, 'rb') as f:
        rv = client.post(
            endpoint_push_zipfile.url_path,
            headers=auth_header,
            data={'file': (f, f.name)},
            content_type='multipart/form-data',
        )

    assert rv.status_code == 200, rv.get_json()
    # In V2, package_name_suffix also modifies the repository
    assert rv.get_json()['repo'] == expected_pkg_name


@pytest.mark.parametrize('filename', (
    'test.json',  # test invalid extension
    'test.zip',  # test invalid content
))
def test_push_zipfile_invalid_file(
        client, filename, endpoint_push_zipfile,
        mocked_quay_io, auth_header):
    """Test if proper error is returned when no zip file is being attached"""
    data = {
        'file': (BytesIO(b'randombytes'), filename),
    }
    rv = client.post(
        endpoint_push_zipfile.url_path,
        data=data,
        headers=auth_header,
        content_type='multipart/form-data',
    )

    assert rv.status_code == 400, rv.get_json()
    rv_json = rv.get_json()
    assert rv_json['status'] == 400
    assert rv_json['error'] == 'OMPSUploadedFileError'


def test_push_zipfile_no_file(
        client, endpoint_push_zipfile, mocked_quay_io, auth_header):
    """Test if proper error is returned when no file is being attached"""
    rv = client.post(endpoint_push_zipfile.url_path, headers=auth_header)
    assert rv.status_code == 400, rv.get_json()
    rv_json = rv.get_json()
    assert rv_json['status'] == 400
    assert rv_json['error'] == 'OMPSExpectedFileError'


def test_push_zipfile_unauthorized(client, endpoint_push_zipfile):
    """Test if api properly refuses unauthorized requests"""
    rv = client.post(endpoint_push_zipfile.url_path)
    assert rv.status_code == requests.codes.forbidden, rv.get_json()
    rv_json = rv.get_json()
    assert rv_json['status'] == requests.codes.forbidden
    assert rv_json['error'] == 'OMPSAuthorizationHeaderRequired'


@pytest.mark.usefixtures("mocked_quay_io")
def test_push_zipfile_encrypted(
        client, encrypted_zip_archive,
        endpoint_push_zipfile, auth_header):
    """Test if proper error is returned when the attached zip file
    is encrypted
    """
    with open(encrypted_zip_archive, 'rb') as f:
        data = {
            'file': (f, f.name),
        }
        rv = client.post(
            endpoint_push_zipfile.url_path,
            headers=auth_header,
            data=data,
            content_type='multipart/form-data',
        )

    assert rv.status_code == 400, rv.get_json()
    rv_json = rv.get_json()
    assert rv_json['status'] == 400
    assert rv_json['error'] == 'OMPSUploadedFileError'
    assert 'is encrypted' in rv_json['message']


def test_push_koji_nvr(
        client, endpoint_push_koji, mocked_quay_io, mocked_op_courier_push,
        auth_header, mocked_koji_archive_download, mocked_greenwave):
    """Test REST API for pushing operators from koji by NVR"""
    archive = mocked_koji_archive_download
    rv = client.post(
        endpoint_push_koji.url_path,
        headers=auth_header
    )
    assert rv.status_code == 200, rv.get_json()
    expected = {
        'organization': endpoint_push_koji.org,
        'repo': archive.pkg_name,
        'version': endpoint_push_koji.version or constants.DEFAULT_RELEASE_VERSION,
        'nvr': endpoint_push_koji.nvr,
        'extracted_files': archive.files,
    }
    assert rv.get_json() == expected
    mocked_greenwave.assert_called_once_with(endpoint_push_koji.nvr)


def test_push_invalid_manifests(
        client, endpoint_push_koji, mocked_quay_io, mocked_op_courier_push,
        auth_header, mocked_bad_koji_archive_download, mocked_greenwave):
    """Test REST API for failing to push operators with bad manifests """
    rv = client.post(
        endpoint_push_koji.url_path,
        headers=auth_header
    )
    assert rv.status_code == requests.codes.bad_request, rv.get_json()
    rv_json = rv.get_json()
    assert rv_json['error'] == 'PackageValidationError'
    assert rv_json['message'] in (
        'Could not find packageName in manifests.',
        'Failed to process yaml file /not_yaml.yaml',
    )


def test_push_koji_unauthorized(client, endpoint_push_koji):
    """Test if api properly refuses unauthorized requests"""
    rv = client.post(endpoint_push_koji.url_path)
    assert rv.status_code == requests.codes.forbidden, rv.get_json()
    rv_json = rv.get_json()
    assert rv_json['status'] == requests.codes.forbidden
    assert rv_json['error'] == 'OMPSAuthorizationHeaderRequired'


@pytest.mark.parametrize('endpoint, exclude', [
    ('/v2/organization-X/zipfile', {'DELETE', }),
    ('/v2/organization-X/zipfile/1.0.1', {'DELETE', }),
    ('/v2/organization-X/koji/nvr-Z', {'DELETE', }),
    ('/v2/organization-X/koji/nvr-Z/1.0.1', set()),
])
@pytest.mark.parametrize('method', [
    'GET', 'PATCH' 'PUT', 'HEAD', 'DELETE', 'TRACE',
])
def test_method_not_allowed(client, endpoint, exclude, method):
    """Specified endpoints currently support only POST method, test if other
    HTTP methods returns proper error code

    Method OPTIONS is excluded from testing due its special meaning
    """
    if method in exclude:
        # exclude testing of some combinations
        return

    rv = client.open(endpoint, method=method)
    assert rv.status_code == 405


@pytest.mark.parametrize('endpoint', [
    '/',
    '/v2'
    '/v2/organization-X/repo-Y/koji/',
    '/v2/organization-X/repo-Y/koji/nvr-Z/version/extra-something',
    '/v2/organization-X/repo-Y/zipfile/version-Z/extra-something',
])
def test_404_for_mistyped_entrypoints(client, endpoint):
    """Test if HTTP 404 is returned for unexpected endpoints"""
    rv = client.post(endpoint)
    assert rv.status_code == 404
    rv_json = rv.get_json()
    assert rv_json['error'] == 'NotFound'
    assert rv_json['status'] == 404
