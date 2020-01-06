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

    app_registry.delete(test_env['test_namespace'], test_env['test_package'])


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
def suffix_quay():
    quay = None
    config = test_env.get("alter_package_name")

    if config:
        quay = QuayAppRegistry(test_env["quay_app_registry_api"],
                               test_env["quay_api"],
                               test_env["quay_oauth_token"])
        quay.login_to_cnr(config["user"],
                          config["password"])

    yield quay

    if quay:
        quay.delete(config["namespace"],
                    config["package"] + config["suffix"])


@pytest.fixture
def private_omps(private_quay):
    if private_quay:
        return OMPS(test_env['omps_url'], private_quay.token)


@pytest.fixture
def suffix_omps(suffix_quay):
    if suffix_quay:
        return OMPS(test_env["omps_url"], suffix_quay.token)
