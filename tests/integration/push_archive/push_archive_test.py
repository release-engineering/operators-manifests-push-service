#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import shutil
import pytest
import requests
import yaml
from distutils import dir_util
from tests.integration.utils import test_env


def test_initial_upload(omps, quay, tmp_path):
    """
    When uploading an archive to a repository which is empty,
    and no version is specified during the upload
    then a new release is created with version 1.0.0
    """

    # Make sure there test_env['test_package'] operator is empty.
    releases = [r['release'] for r in
                quay.get_releases(test_env['test_namespace'], test_env['test_package'])]
    quay.delete_releases('/'.join([test_env['test_namespace'],
                                   test_env['test_package']]), releases)

    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/artifacts/valid/')
    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'], archive=archive).json()

    assert response['organization'] == test_env['test_namespace']
    assert response['repo'] == test_env['test_package']
    assert response['version'] == '1.0.0'

    releases = quay.get_releases(test_env['test_namespace'],
                                 test_env['test_package'],
                                 authorization=None)
    assert releases
    assert len(releases) == 1
    assert releases[0]['release'] == '1.0.0'


def test_nested_manifest(omps, quay, tmp_path):
    """
    When the manifest data in a zip file has a nested structure,
    and the manifest data is pushed to Quay using the ZIP-file endpoint,
    then pushing the data is successful.
    """
    version = '1.0.0'
    quay.delete(test_env['test_namespace'], test_env['test_package'])
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/artifacts/nested/')

    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'], archive=archive)

    assert response.status_code == requests.codes.ok
    assert response.json() == {
        'extracted_files': [
            '0.6.1/int-testcluster.crd.yaml',
            '0.6.1/int-testoperator.clusterserviceversion.yaml',
            '0.9.0/int-testbackup.crd.yaml',
            '0.9.0/int-testcluster.crd.yaml',
            '0.9.0/int-testoperator.v0.9.0.clusterserviceversion.yaml',
            '0.9.0/int-testrestore.crd.yaml',
            '0.9.2/int-testbackup.crd.yaml',
            '0.9.2/int-testoperator.v0.9.2.clusterserviceversion.yaml',
            'int-test.package.yaml'
        ],
        'organization': test_env['test_namespace'],
        'repo': test_env['test_package'],
        'version': version,
    }
    assert quay.get_release(test_env['test_namespace'],
                            test_env['test_package'],
                            version,
                            authorization=None)


def test_upload_with_version(omps, quay, tmp_path):
    """
    When specifying the version for an upload,
    then the release is created with the version specified.
    """
    version = '4.3.2'

    # Make sure the version to be uploaded does not exist.
    if quay.get_release(test_env['test_namespace'], test_env['test_package'], version):
        quay.delete_releases('/'.join([test_env['test_namespace'],
                                       test_env['test_package']]), [version])

    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/artifacts/valid/')
    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'],
                           version=version, archive=archive).json()

    assert response['organization'] == test_env['test_namespace']
    assert response['repo'] == test_env['test_package']
    assert response['version'] == version

    assert quay.get_release(test_env['test_namespace'],
                            test_env['test_package'],
                            version,
                            authorization=None)


def test_increment_version(omps, quay, tmp_path):
    """
    When no version is specified, and there already are some releases in
        the package,
    then the major bit of the semantically highest version is incremented,
        and used as the version of the new release.
    """
    expected_releases = set(['1.0.0', '4.3.2'])
    next_release = '5.0.0'

    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/artifacts/valid/')

    # Make sure that only the expected releases are present
    package_releases = set(release['release'] for release in
                           quay.get_releases(test_env['test_namespace'],
                                             test_env['test_package']))
    for release in expected_releases - package_releases:
        omps.upload(organization=test_env['test_namespace'],
                    repo=test_env['test_package'], version=release, archive=archive)

    quay.delete_releases('/'.join([test_env['test_namespace'], test_env['test_package']]),
                         package_releases - expected_releases)

    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'], archive=archive).json()

    assert response['organization'] == test_env['test_namespace']
    assert response['repo'] == test_env['test_package']
    assert response['version'] == next_release

    assert quay.get_release(test_env['test_namespace'],
                            test_env['test_package'],
                            next_release,
                            authorization=None)


def test_version_exists(omps, quay, tmp_path):
    """
    When the version already exists in the package,
    then creating the new release fails.
    """
    release_used = '5.0.0'

    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/artifacts/valid/')

    if not quay.get_release(test_env['test_namespace'],
                            test_env['test_package'], release_used):
        omps.upload(organization=test_env['test_namespace'],
                    repo=test_env['test_package'], version=release_used, archive=archive)

    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'],
                           version=release_used, archive=archive)

    assert response.status_code == requests.codes.server_error
    assert response.json()['error'] == 'QuayCourierError'
    assert 'Failed to push' in response.json()['message']


@pytest.mark.parametrize("version", [
    ('1.0.0.1'),
    ('1.0.0-2'),
    ('1.0.02'),
    ('1.a.2'),
    ('1.1'),
])
def test_incorrect_version(omps, tmp_path, version):
    """
    When the version specified does not meet OMPS requirements,
    then the push fails.
    """
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/artifacts/valid/')
    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'],
                           version=version, archive=archive)

    assert response.status_code == requests.codes.bad_request
    assert response.json()['error'] == 'OMPSInvalidVersionFormat'
    assert version in response.json()['message']


def test_filetype_not_supported(omps, tmpdir):
    """
    If the file uploaded is not a ZIP file,
    then the push fails.
    """
    archive = tmpdir.join('not-a-zip.zip').ensure()
    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'], archive=archive)

    assert response.status_code == requests.codes.bad_request
    assert response.json()['error'] == 'OMPSUploadedFileError'
    assert 'not a zip file' in response.json()['message']


def test_file_extension_not_zip(omps, tmpdir):
    """
    If the extension of the file is not '.zip',
    then the push fails.
    """
    archive = tmpdir.join('archive.tar.gz').ensure()
    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'], archive=archive)

    assert response.status_code == requests.codes.bad_request
    assert response.json()['error'] == 'OMPSUploadedFileError'
    assert 'file extension' in response.json()['message']


def test_no_file_field(omps, tmp_path):
    """
    The ZIP file uploaded must be assigned to the 'file' field.
    """
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/artifacts/valid/')
    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'],
                           archive=archive, field='archive')

    assert response.status_code == requests.codes.bad_request
    assert response.json()['error'] == 'OMPSExpectedFileError'
    assert 'No field "file"' in response.json()['message']


def test_organization_unaccessible_in_quay(omps, tmp_path):
    """
    Push fails, if the organization is not configured in OMPS.
    """
    organization = 'martian-green-operators'
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/artifacts/valid/')
    response = omps.upload(organization=organization,
                           repo=test_env['test_package'], archive=archive)

    assert response.status_code == requests.codes.forbidden
    assert response.json()['error'] == 'QuayAuthorizationError'
    assert 'Cannot retrieve information about package' in response.json()['message']


def test_upload_password_protected_zip(omps):
    """
    Push fails, if the ZIP-file is password-protected.
    """
    archive = 'tests/integration/artifacts/encrypted.zip'
    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'], archive=archive)

    assert response.status_code == requests.codes.bad_request
    assert response.json()['error'] == 'OMPSUploadedFileError'
    assert 'is encrypted' in response.json()['message']


def test_upload_invalid_artifact(omps, tmp_path):
    """
    Push fails, if the artifact does not pass quay-courier validation.
    """
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/artifacts/invalid/')
    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'], archive=archive)

    assert response.status_code == requests.codes.bad_request
    assert response.json()['error'] == 'PackageValidationError'
    assert 'bundle is invalid' in response.json()['message']


@pytest.mark.skipif(not test_env.get('private_org'),
                    reason='No private organization configured.')
def test_private_organization(private_omps, private_quay, tmp_path_factory):
    """
    When packages are pushed to an organization, which is not configured
        to hold public packages,
    Then a newly created package is private.
    """
    namespace = test_env['private_org']['namespace']
    package = test_env['private_org']['package']
    version = '1.0.0'
    private_quay.delete(namespace, package)

    # Make sure artifact's packageName matches package name used for the push.
    artifacts_dir = tmp_path_factory.mktemp('artifacts')
    dir_util.copy_tree('tests/integration/artifacts/valid/',
                       artifacts_dir.as_posix())

    with open(artifacts_dir / 'packages.yaml', 'r') as fd:
        packages_yaml = yaml.safe_load(fd)

    with open(artifacts_dir / 'packages.yaml', 'w') as fd:
        packages_yaml['packageName'] = 'int-test-private'
        yaml.dump(packages_yaml, fd)

    archive_dir = tmp_path_factory.mktemp('archive')
    archive = shutil.make_archive(archive_dir / 'archive', 'zip', artifacts_dir)

    response = private_omps.upload(organization=namespace,
                                   repo=package, archive=archive)

    assert response.json() == {
        'extracted_files': [
            'crd.yaml',
            'csv.yaml',
            'packages.yaml'
        ],
        'organization': namespace,
        'repo': package,
        'version': version,
    }
    assert response.status_code == requests.codes.ok

    assert private_quay.get_release(namespace, package, version)

    with pytest.raises(requests.HTTPError) as err:
        private_quay.get_release(namespace, package, version,
                                 authorization=None)
        assert '403' in str(err.value)
