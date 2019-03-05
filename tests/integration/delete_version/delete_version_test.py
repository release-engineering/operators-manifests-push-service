#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import shutil
import requests
import pytest


def test_delete_version(omps, quay_app_registry, tmp_path):
    """
    When a version is requested to be deleted,
    and a release matching that version exists for the package,
    the matching release is deleted.
    """
    version = '10.9.8'
    if not quay_app_registry.get_release(omps.organization, 'int-test', version):
        archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                      'tests/integration/push_archive/artifacts/')
        response = omps.upload(repo='int-test', version=version, archive=archive)
        response.raise_for_status()

    response = omps.delete(omps.organization, 'int-test', version)

    assert response.status_code == requests.codes.ok
    assert response.json() == {
        'deleted': [version],
        'organization': omps.organization,
        'repo': 'int-test',
    }
    assert not quay_app_registry.get_release(omps.organization, 'int-test', version)


def test_version_does_not_exist(omps, quay_app_registry, tmp_path):
    """
    If the version requested to be deleted, is not present in the package,
    a 'QuayPackageNotFound' error is returned.
    """
    # Ensure there is at least one more release besides the one to be deleted.
    version = '8.0.1'
    if not quay_app_registry.get_release(omps.organization, 'int-test', version):
        archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                      'tests/integration/push_archive/artifacts/')
        response = omps.upload(repo='int-test', version=version, archive=archive)
        response.raise_for_status()

    # Ensure the release to be deleted is not in the package.
    version = '10.9.8'
    if quay_app_registry.get_release(omps.organization, 'int-test', version):
        quay_app_registry.delete_releases(omps.organization + '/int-test', [version])

    response = omps.delete(omps.organization, 'int-test', version)

    assert response.status_code == requests.codes.not_found
    assert response.json()['error'] == 'QuayPackageNotFound'
    assert "doesn't exist" in response.json()['message']


def test_delete_all_versions(omps, quay_app_registry, tmp_path):
    """
    When there is no version specified for the delete operation,
    all the releases of the package are deleted.
    """
    # Ensure there are at least 2 releases.
    if len(quay_app_registry.get_releases(omps.organization, 'int-test')) < 2:
        archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                      'tests/integration/push_archive/artifacts/')
        for version in ['8.0.0', '8.0.1']:
            response = omps.upload(repo='int-test', version=version, archive=archive)

    versions = [r['release'] for r in
                quay_app_registry.get_releases(omps.organization, 'int-test')]
    assert len(versions) > 1

    response = omps.delete(omps.organization, 'int-test')

    assert response.status_code == requests.codes.ok
    assert response.json() == {
        'deleted': versions,
        'organization': omps.organization,
        'repo': 'int-test',
    }


def test_organization_not_configured(omps):
    """
    Delete fails, if the organization is not configured with OMPS.
    """
    response = omps.delete('no-such-organization', 'int-test', '10.0.1')

    assert response.status_code == requests.codes.not_found
    assert response.json()['error'] == 'OMPSOrganizationNotFound'
    assert 'not found in configuration' in response.json()['message']


def test_package_does_not_exist(omps, quay_app_registry):
    """
    Delete fails, if the package does not exist in Quay.
    """
    # Ensure package does not exist.
    package = 'no-such-package'
    name = '/'.join([omps.organization, package])
    existing = [p['name'] for p in quay_app_registry.get_packages(omps.organization)]
    if name in existing:
        releases = [r['release'] for r in
                    quay_app_registry.get_releases(omps.organization, 'no-such-package')]
        quay_app_registry.delete_releases(name, releases)

    response = omps.delete(omps.organization, package)

    assert response.status_code == requests.codes.not_found
    assert response.json()['error'] == 'QuayPackageNotFound'
    assert 'not found' in response.json()['message']


@pytest.mark.parametrize("delete_version,next_version", [
    pytest.param('6.0.2', '5.0.0', id='highest version'),
    pytest.param('4.0.1', '7.0.0', id='previous version'),
])
def test_increment_version_after_delete(omps, quay_app_registry, tmp_path,
                                        delete_version, next_version):
    """
    Auto-incrementing the version works as expected,
        after the highest version is deleted.
    Auto-incrementing the version works as expected,
        after some previous version is deleted.
    """
    # Ensure only certain releases do exist.
    releases = set(r['release'] for r in
                   quay_app_registry.get_releases(omps.organization, 'int-test'))
    versions = set(['3.0.0', '4.0.1', '6.0.2'])
    to_delete = releases - versions
    to_upload = versions - releases
    quay_app_registry.delete_releases(omps.organization + '/int-test', to_delete)
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/push_archive/artifacts/')
    for version in to_upload:
        response = omps.upload(repo='int-test', version=version, archive=archive)
        response.raise_for_status()

    # Delete a release.
    response = omps.delete(omps.organization, 'int-test', delete_version)
    response.raise_for_status()

    # Push a new one, without specifying the version.
    response = omps.upload(repo='int-test', archive=archive)

    assert response.status_code == requests.codes.ok
    assert response.json()['version'] == next_version
    assert quay_app_registry.get_release(omps.organization, 'int-test', next_version)
