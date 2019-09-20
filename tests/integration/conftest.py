#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import pytest
from .utils import OMPS, QuayAppRegistry, Koji, test_env


@pytest.fixture(scope='session')
def quay():
    """Quay App Registry used for testing.

    Args:
        test_env: Dictionary with test environment configuration.

    Yields: An instance of QuayAppRegistry.
    Raises: None.
    """
    app_registry = QuayAppRegistry(test_env['quay_app_registry_api'],
                                   test_env['quay_api'],
                                   test_env['quay_oauth_token'])
    app_registry.login_to_cnr(test_env['quay_user'], test_env['quay_password'])

    yield app_registry


@pytest.fixture(scope='session')
def omps(quay):
    """OMPS used for testing.

    Args:
        test_env: Dictionary with test environment configuration.
        quay: QuayAppRegistry object, for the Quay instance used by OMPS.

    Returns: An instance of OMPS.
    Raises: None.
    """
    return OMPS(test_env['omps_url'], quay.token)


@pytest.fixture(scope='session')
def koji():
    """Koji instance configured in OMPS.

    Args:
        test_env: Dictionary with test environment configuration.

    Returns: An instance of Koji.
    Raises: None.
    """
    return Koji(test_env['kojihub'], test_env['kojiroot'])


@pytest.fixture
def private_quay():
    quay = None

    if test_env.get('private_org'):
        quay = QuayAppRegistry(test_env['quay_app_registry_api'],
                               test_env['quay_api'],
                               test_env['quay_oauth_token'])
        quay.login_to_cnr(test_env['private_org']['user'],
                          test_env['private_org']['password'])

    yield quay

    if quay:
        quay.delete(test_env['private_org']['namespace'],
                    test_env['private_org']['package'])


@pytest.fixture
def private_omps(private_quay):
    if private_quay:
        return OMPS(test_env['omps_url'], private_quay.token)
