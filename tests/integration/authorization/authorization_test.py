#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#


import shutil
import pytest
import requests
from tests.integration.utils import OMPS, test_env


@pytest.fixture(scope='module')
def no_auth_omps():
    return OMPS(test_env['omps_url'])


def test_upload_without_authorization(no_auth_omps, tmp_path):
    """
    Upload fails, when no 'Authorization' header is provided.
    """
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/push_archive/artifacts/')
    response = no_auth_omps.upload(organization=test_env['test_namespace'],
                                   repo=test_env['test_package'], archive=archive)

    assert response.status_code == requests.codes.forbidden
    assert response.json()['error'] == 'OMPSAuthorizationHeaderRequired'


def test_delete_without_authorization(no_auth_omps, omps, quay, tmp_path):
    """
    Deleting a version fails, when no 'Authorization' header is provided.
    """
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/push_archive/artifacts/')
    response = omps.upload(organization=test_env['test_namespace'],
                           repo=test_env['test_package'], archive=archive)
    response.raise_for_status()

    assert quay.get_release(test_env['test_namespace'],
                            test_env['test_package'], '1.0.0')

    response = no_auth_omps.delete(test_env['test_namespace'],
                                   test_env['test_package'], '1.0.0')

    assert response.status_code == requests.codes.forbidden
    assert response.json()['error'] == 'OMPSAuthorizationHeaderRequired'
