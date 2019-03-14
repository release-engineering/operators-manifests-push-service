#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import shutil
import requests
import pytest
from operatorcourier import api as courier
from tests.integration.utils import test_env


def test_invalid_zip(omps):
    """
    When fetching an NVR from Koji,
    and the archive attached to the build has an invalid bundle,
    then fetching the NVR fails.
    """
    nvr = test_env['koji_builds']['invalid_zip']
    response = omps.fetch_nvr(organization=test_env['test_namespace'],
                              repo=test_env['test_package'], nvr=nvr)

    assert response.status_code == requests.codes.internal_server_error
    assert response.json()['error'] == 'QuayCourierError'
    assert 'bundle is invalid' in response.json()['message']


def test_not_an_operator(omps):
    """
    When fetching an NVR from Koji,
    and the container image referenced by the NVR is not an operator,
    then fetching the NVR fails.
    """
    nvr = test_env['koji_builds']['not_an_operator']
    response = omps.fetch_nvr(organization=test_env['test_namespace'],
                              repo=test_env['test_package'], nvr=nvr)

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
    response = omps.fetch_nvr(organization=test_env['test_namespace'],
                              repo=test_env['test_package'], nvr=nvr)

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
    nvr = test_env['koji_builds']['valid_zip']
    quay.delete(test_env['test_namespace'], test_env['test_package'])

    response = omps.fetch_nvr(organization=test_env['test_namespace'],
                              repo=test_env['test_package'], nvr=nvr)

    assert response.status_code == requests.codes.ok
    assert response.json() == {
        'extracted_files': [
            'crd.yaml',
            'csv.yaml',
            'packages.yaml'
        ],
        'nvr': test_env['koji_builds']['valid_zip'],
        'organization': test_env['test_namespace'],
        'repo': test_env['test_package'],
        'version': '1.0.0',
    }
    assert quay.get_release(test_env['test_namespace'],
                            test_env['test_package'], '1.0.0',
                            authorization=None)

    quay_bundle = quay.get_bundle(test_env['test_namespace'],
                                  test_env['test_package'], '1.0.0',
                                  authorization=None)
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
    nvr = test_env['koji_builds']['valid_zip']
    version = '6.5.4'
    response = omps.fetch_nvr(organization=test_env['test_namespace'],
                              repo=test_env['test_package'],
                              nvr=nvr, version=version)

    assert response.status_code == requests.codes.ok
    assert response.json() == {
        'extracted_files': [
            'crd.yaml',
            'csv.yaml',
            'packages.yaml'
        ],
        'nvr': nvr,
        'organization': test_env['test_namespace'],
        'repo': test_env['test_package'],
        'version': version,
    }
    assert quay.get_release(test_env['test_namespace'],
                            test_env['test_package'], version,
                            authorization=None)


def test_version_exists(omps, quay, tmp_path):
    """
    When fetching an NVR from Koji,
    and the request specifies a version,
    and a release with the same version already exists,
    then fetching the NVR fails.
    """
    nvr = test_env['koji_builds']['valid_zip']
    version = '8.0.1'

    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/push_archive/artifacts/')

    if not quay.get_release(test_env['test_namespace'],
                            test_env['test_package'], version):
        omps.upload(organization=test_env['test_namespace'],
                    repo=test_env['test_package'], version=version, archive=archive)

    response = omps.fetch_nvr(organization=test_env['test_namespace'],
                              repo=test_env['test_package'], nvr=nvr, version=version)

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
    nvr = test_env['koji_builds']['valid_zip']
    version = '7.6.1'
    next_version = '8.0.0'

    quay.delete(test_env['test_namespace'], test_env['test_package'])
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/push_archive/artifacts/')
    omps.upload(organization=test_env['test_namespace'],
                repo=test_env['test_package'], version=version, archive=archive)

    response = omps.fetch_nvr(organization=test_env['test_namespace'],
                              repo=test_env['test_package'], nvr=nvr)

    assert response.status_code == requests.codes.ok
    assert response.json() == {
        'extracted_files': [
            'crd.yaml',
            'csv.yaml',
            'packages.yaml'
        ],
        'nvr': nvr,
        'organization': test_env['test_namespace'],
        'repo': test_env['test_package'],
        'version': next_version,
    }
    assert quay.get_release(test_env['test_namespace'],
                            test_env['test_package'], next_version,
                            authorization=None)


@pytest.mark.skipif(not test_env.get('private_org'),
                    reason='No private organization configured.')
def test_private_organization(private_omps, private_quay):
    """
    """
    namespace = test_env['private_org']['namespace']
    package = test_env['private_org']['package']
    nvr = test_env['koji_builds']['valid_zip']
    version = '1.0.0'
    private_quay.delete(namespace, package)

    response = private_omps.fetch_nvr(organization=namespace,
                                      repo=package, nvr=nvr)

    assert response.json() == {
        'extracted_files': [
            'crd.yaml',
            'csv.yaml',
            'packages.yaml'
        ],
        'nvr': nvr,
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
