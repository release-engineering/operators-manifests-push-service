#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import shutil


def test_initial_upload(omps, quay_app_registry, tmp_path):
    """
    When uploading an archive to a repository which does not exist or it's empty,
    And no version is specified during the upload
    Then a new release is created with version 1.0.0
    """

    # Make sure there is no 'int-test' operator in the namespace,
    # or it is empty.
    assert not quay_app_registry.get_releases(omps.organization, 'int-test')

    archive = shutil.make_archive(tmp_path / 'archive', 'zip',
                                  'tests/integration/push_archive/artifacts/')
    response = omps.upload('int-test', archive)

    assert response['organization'] == omps.organization
    assert response['repo'] == 'int-test'
    assert response['version'] == '1.0.0'

    releases = quay_app_registry.get_releases(omps.organization, 'int-test')
    assert releases
    assert len(releases) == 1
    assert releases[0]['release'] == '1.0.0'
