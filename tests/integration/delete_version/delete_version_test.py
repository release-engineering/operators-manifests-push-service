#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import shutil
import requests
import pytest
from tests.integration.constants import TEST_NAMESPACE, TEST_PACKAGE


def test_delete_version(omps, quay, tmp_path):
    """
    When a version is requested to be deleted,
    and a release matching that version exists for the package,
    the matching release is deleted.
    """
    version = '10.9.8'
    if not quay.get_release(TEST_NAMESPACE, TEST_PACKAGE, version):
        archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                      'tests/integration/push_archive/artifacts/')
        response = omps.upload(organization=TEST_NAMESPACE,
                               repo=TEST_PACKAGE, version=version, archive=archive)
        response.raise_for_status()

    response = omps.delete(TEST_NAMESPACE, TEST_PACKAGE, version)

    assert response.status_code == requests.codes.ok
    assert response.json() == {
        'deleted': [version],
        'organization': TEST_NAMESPACE,
        'repo': TEST_PACKAGE,
    }
    assert not quay.get_release(TEST_NAMESPACE, TEST_PACKAGE, version)


def test_version_does_not_exist(omps, quay, tmp_path):
    """
    If the version requested to be deleted, is not present in the package,
    a 'QuayPackageNotFound' error is returned.
    """
    # Ensure there is at least one more release besides the one to be deleted.
    version = '8.0.1'
    if not quay.get_release(TEST_NAMESPACE, TEST_PACKAGE, version):
        archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                      'tests/integration/push_archive/artifacts/')
        response = omps.upload(organization=TEST_NAMESPACE,
                               repo=TEST_PACKAGE, version=version, archive=archive)
        response.raise_for_status()

    # Ensure the release to be deleted is not in the package.
    version = '10.9.8'
    if quay.get_release(TEST_NAMESPACE, TEST_PACKAGE, version):
        quay.delete_releases('/'.join([TEST_NAMESPACE, TEST_PACKAGE]), [version])

    response = omps.delete(TEST_NAMESPACE, TEST_PACKAGE, version)

    assert response.status_code == requests.codes.not_found
    assert response.json()['error'] == 'QuayPackageNotFound'
    assert "doesn't exist" in response.json()['message']


def test_delete_all_versions(omps, quay, tmp_path):
    """
    When there is no version specified for the delete operation,
    all the releases of the package are deleted.
    """
    # Ensure there are at least 2 releases.
    if len(quay.get_releases(TEST_NAMESPACE, TEST_PACKAGE)) < 2:
        archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                      'tests/integration/push_archive/artifacts/')
        for version in ['8.0.0', '8.0.1']:
            response = omps.upload(organization=TEST_NAMESPACE,
                                   repo=TEST_PACKAGE, version=version, archive=archive)

    versions = [r['release'] for r in
                quay.get_releases(TEST_NAMESPACE, TEST_PACKAGE)]
    assert len(versions) > 1

    response = omps.delete(TEST_NAMESPACE, TEST_PACKAGE)

    assert response.status_code == requests.codes.ok
    assert response.json() == {
        'deleted': versions,
        'organization': TEST_NAMESPACE,
        'repo': TEST_PACKAGE,
    }


def test_organization_unaccessible_in_quay(omps):
    """
    Delete fails, if the organization is not configured with OMPS.
    """
    response = omps.delete('no-such-organization', TEST_PACKAGE, '10.0.1')

    assert response.status_code == requests.codes.internal_server_error
    assert response.json()['error'] == 'QuayPackageError'
    assert 'Unauthorized access' in response.json()['message']


def test_package_does_not_exist(omps, quay):
    """
    Delete fails, if the package does not exist in Quay.
    """
    # Ensure package does not exist.
    package = 'no-such-package'
    name = '/'.join([TEST_NAMESPACE, package])
    existing = [p['name'] for p in quay.get_packages(TEST_NAMESPACE)]
    if name in existing:
        releases = [r['release'] for r in
                    quay.get_releases(TEST_NAMESPACE, 'no-such-package')]
        quay.delete_releases(name, releases)

    response = omps.delete(TEST_NAMESPACE, package)

    assert response.status_code == requests.codes.not_found
    assert response.json()['error'] == 'QuayPackageNotFound'
    assert 'not found' in response.json()['message']


@pytest.mark.parametrize("delete_version,next_version", [
    pytest.param('6.0.2', '5.0.0', id='highest version'),
    pytest.param('4.0.1', '7.0.0', id='previous version'),
])
def test_increment_version_after_delete(omps, quay, tmp_path,
                                        delete_version, next_version):
    """
    Auto-incrementing the version works as expected,
        after the highest version is deleted.
    Auto-incrementing the version works as expected,
        after some previous version is deleted.
    """
    # Ensure only certain releases do exist.
    releases = set(r['release'] for r in
                   quay.get_releases(TEST_NAMESPACE, TEST_PACKAGE))
    versions = set(['3.0.0', '4.0.1', '6.0.2'])
    to_delete = releases - versions
    to_upload = versions - releases
    quay.delete_releases('/'.join([TEST_NAMESPACE, TEST_PACKAGE]), to_delete)
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/push_archive/artifacts/')
    for version in to_upload:
        response = omps.upload(organization=TEST_NAMESPACE,
                               repo=TEST_PACKAGE, version=version, archive=archive)
        response.raise_for_status()

    # Delete a release.
    response = omps.delete(TEST_NAMESPACE, TEST_PACKAGE, delete_version)
    response.raise_for_status()

    # Push a new one, without specifying the version.
    response = omps.upload(organization=TEST_NAMESPACE,
                           repo=TEST_PACKAGE, archive=archive)

    assert response.status_code == requests.codes.ok
    assert response.json()['version'] == next_version
    assert quay.get_release(TEST_NAMESPACE, TEST_PACKAGE, next_version)
