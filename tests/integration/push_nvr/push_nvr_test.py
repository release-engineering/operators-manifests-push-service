#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import shutil
import requests
from operatorcourier import api as courier
from tests.integration.constants import (
    TEST_NAMESPACE,
    TEST_PACKAGE,
    TEST_VALID_NVR,
    TEST_INVALID_NVR,
    TEST_NOT_AN_OPERATOR)


def test_invalid_zip(omps):
    """
    When fetching an NVR from Koji,
    and the archive attached to the build has an invalid bundle,
    then fetching the NVR fails.
    """
    nvr = TEST_INVALID_NVR
    response = omps.fetch_nvr(organization=TEST_NAMESPACE,
                              repo=TEST_PACKAGE, nvr=nvr)

    assert response.status_code == requests.codes.internal_server_error
    assert response.json()['error'] == 'QuayCourierError'
    assert 'bundle is invalid' in response.json()['message']


def test_not_an_operator(omps):
    """
    When fetching an NVR from Koji,
    and the container image referenced by the NVR is not an operator,
    then fetching the NVR fails.
    """
    nvr = TEST_NOT_AN_OPERATOR
    response = omps.fetch_nvr(organization=TEST_NAMESPACE,
                              repo=TEST_PACKAGE, nvr=nvr)

    assert response.status_code == requests.codes.bad_request
    assert response.json()['error'] == 'KojiNotAnOperatorImage'
    assert 'Not an operator image' in response.json()['message']


def test_nvr_not_found(omps):
    """
    When fetching an NVR from Koji,
    and no build exists for that NVR in Koji,
    then fetching the NVR fails.
    """
    nvr = 'no-such-operator-container-image-1.0.0-111'
    response = omps.fetch_nvr(organization=TEST_NAMESPACE,
                              repo=TEST_PACKAGE, nvr=nvr)

    assert response.status_code == requests.codes.not_found
    assert response.json()['error'] == 'KojiNVRBuildNotFound'
    assert 'NVR not found' in response.json()['message']


def test_valid_zip_default_version(omps, quay, koji, tmp_path):
    """
    When fetching an NVR from Koji,
    and it's going to be the first release in the package,
    and there is no version specified,
    then the release gets the default version number,
    and the bundle uploaded to Quay is the same as the one generated
        from the Koji archive.
    """
    nvr = TEST_VALID_NVR
    quay.clean_up_package(TEST_NAMESPACE, TEST_PACKAGE)

    response = omps.fetch_nvr(organization=TEST_NAMESPACE,
                              repo=TEST_PACKAGE, nvr=nvr)

    assert response.status_code == requests.codes.ok
    assert response.json() == {
        'extracted_files': [
            'crd.yaml',
            'csv.yaml',
            'packages.yaml'
        ],
        'nvr': TEST_VALID_NVR,
        'organization': TEST_NAMESPACE,
        'repo': TEST_PACKAGE,
        'version': '1.0.0',
    }
    assert quay.get_release(TEST_NAMESPACE, TEST_PACKAGE, '1.0.0')

    quay_bundle = quay.get_bundle(TEST_NAMESPACE, TEST_PACKAGE, '1.0.0')
    koji.download_manifest(nvr, tmp_path)
    koji_bundle = courier.build_and_verify(source_dir=tmp_path.as_posix())

    # Note: this only confirms that OMPS used the right data from Koji,
    #       but tells nothing about the correctness of that data.
    assert quay_bundle == koji_bundle


def test_valid_zip_defined_version(omps, quay):
    """
    When fetching an NVR from Koji,
    and there is a version specified,
    then the release gets the version number specified.
    """
    nvr = TEST_VALID_NVR
    version = '6.5.4'
    response = omps.fetch_nvr(organization=TEST_NAMESPACE,
                              repo=TEST_PACKAGE, nvr=nvr, version=version)

    assert response.status_code == requests.codes.ok
    assert response.json() == {
        'extracted_files': [
            'crd.yaml',
            'csv.yaml',
            'packages.yaml'
        ],
        'nvr': nvr,
        'organization': TEST_NAMESPACE,
        'repo': TEST_PACKAGE,
        'version': version,
    }
    assert quay.get_release(TEST_NAMESPACE, TEST_PACKAGE, version)


def test_version_exists(omps, quay, tmp_path):
    """
    When fetching an NVR from Koji,
    and the request specifies a version,
    and a release with the same version already exists,
    then fetching the NVR fails.
    """
    nvr = TEST_VALID_NVR
    version = '8.0.1'

    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/push_archive/artifacts/')

    if not quay.get_release(TEST_NAMESPACE, TEST_PACKAGE, version):
        omps.upload(organization=TEST_NAMESPACE,
                    repo=TEST_PACKAGE, version=version, archive=archive)

    response = omps.fetch_nvr(organization=TEST_NAMESPACE,
                              repo=TEST_PACKAGE, nvr=nvr, version=version)

    assert response.status_code == requests.codes.server_error
    assert response.json()['error'] == 'QuayCourierError'
    assert 'Failed to push' in response.json()['message']


def test_increment_version(omps, quay, tmp_path):
    """
    When fetching an NVR from Koji,
    and the request specifies no version for the release to be created,
    and there are already some releases for the package,
    then the major bit of the semantically highest version is incremented,
        and used as the version of the new release.
    """
    nvr = TEST_VALID_NVR
    version = '7.6.1'
    next_version = '8.0.0'

    quay.clean_up_package(TEST_NAMESPACE, TEST_PACKAGE)
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/push_archive/artifacts/')
    omps.upload(organization=TEST_NAMESPACE,
                repo=TEST_PACKAGE, version=version, archive=archive)

    response = omps.fetch_nvr(organization=TEST_NAMESPACE,
                              repo=TEST_PACKAGE, nvr=nvr)

    assert response.status_code == requests.codes.ok
    assert response.json() == {
        'extracted_files': [
            'crd.yaml',
            'csv.yaml',
            'packages.yaml'
        ],
        'nvr': nvr,
        'organization': TEST_NAMESPACE,
        'repo': TEST_PACKAGE,
        'version': next_version,
    }
    assert quay.get_release(TEST_NAMESPACE, TEST_PACKAGE, next_version)
