#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import os
import shutil
import pytest
import requests
from tests.integration.utils import OMPS


@pytest.fixture(scope='module')
def no_auth_omps():
    api_url = os.getenv('OMPS_INT_TEST_OMPS_URL')
    organization = os.getenv('OMPS_INT_TEST_OMPS_ORG')

    return OMPS(api_url, organization)


def test_upload_without_authorization(no_auth_omps, tmp_path):
    """
    Upload fails, when no 'Authorization' header is provided.
    """
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/push_archive/artifacts/')
    response = no_auth_omps.upload(repo='int-test', archive=archive)

    assert response.status_code == requests.codes.forbidden
    assert response.json()['error'] == 'OMPSAuthorizationHeaderRequired'


def test_delete_without_authorization(no_auth_omps, omps, quay, tmp_path):
    """
    Deleting a version fails, when no 'Authorization' header is provided.
    """
    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/push_archive/artifacts/')
    response = omps.upload(repo='int-test', archive=archive).raise_for_status()
    assert quay.get_release(omps.organization, 'int-test', '1.0.0')

    response = no_auth_omps.delete(no_auth_omps.organization, 'int-test', '1.0.0')

    assert response.status_code == requests.codes.forbidden
    assert response.json()['error'] == 'OMPSAuthorizationHeaderRequired'
