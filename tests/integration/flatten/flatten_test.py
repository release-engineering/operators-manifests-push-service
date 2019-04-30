#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import shutil
import requests
from distutils import dir_util
from tests.integration.utils import test_env, bundles_equal
from operatorcourier import api as courier


def test_flatten_with_nvr(omps, quay, koji, tmp_path_factory):
    """
    When the manifest data of an operator image has a nested structure,
    and the manifest data is pushed to Quay using the NVR endpoint,
    then pushing the data is successful.
    """
    version = '1.0.0'
    nvr = test_env['koji_builds']['nested_manifest']
    quay.delete(test_env['test_namespace'], test_env['test_package'])

    response = omps.fetch_nvr(organization=test_env['test_namespace'],
                              repo=test_env['test_package'], nvr=nvr)

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
        'nvr': nvr,
        'organization': test_env['test_namespace'],
        'repo': test_env['test_package'],
        'version': version,
    }
    assert quay.get_release(test_env['test_namespace'],
                            test_env['test_package'], '1.0.0',
                            authorization=None)

    quay_bundle = quay.get_bundle(test_env['test_namespace'],
                                  test_env['test_package'], '1.0.0',
                                  authorization=None)

    koji_data = tmp_path_factory.mktemp('koji_data')
    flattened = tmp_path_factory.mktemp('flattened')
    koji.download_manifest(nvr, koji_data)
    courier.flatten(koji_data.as_posix(), flattened.as_posix())
    koji_bundle = courier.build_and_verify(source_dir=flattened.as_posix())

    # Note: this only confirms that OMPS used the right data from Koji,
    #       but tells nothing about the correctness of that data.
    assert bundles_equal(quay_bundle, koji_bundle)


def test_flatten_with_zip(omps, quay, tmp_path):
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


def test_flatten_fails(omps, quay, tmp_path_factory):
    """
    When the manifest data in a zip file has a nested structure,
    and operator courier fails to flatten the manifest
        (due to multiple package files),
    then pushing the data to Quay fails.
    """
    quay.delete(test_env['test_namespace'], test_env['test_package'])

    nested_dir = tmp_path_factory.mktemp('invalid_nested')
    dir_util.copy_tree('tests/integration/artifacts/nested/',
                       nested_dir.as_posix())
    shutil.copyfile(nested_dir / 'int-test.package.yaml',
                    nested_dir / 'other.package.yaml')
    archive_dir = tmp_path_factory.mktemp('archive')
    archive = shutil.make_archive(archive_dir / 'archive', 'zip', nested_dir)

    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'], archive=archive)

    assert response.status_code == requests.codes.server_error
    # TODO(csomh): Check the message in response.json() once Operator Courier
    #     released this change:
    #     https://github.com/operator-framework/operator-courier/pull/92
    assert not quay.get_releases(test_env['test_namespace'],
                                 test_env['test_package'])
