#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import pytest
import yaml
from .utils import OMPS, QuayAppRegistry, Koji


@pytest.fixture(scope='session')
def test_env():
    """Test environment configuration.
    """
    with open('test.env.yaml') as f:
        env = yaml.safe_load(f)
    return env


@pytest.fixture(scope='session')
def quay(test_env):
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
def omps(test_env, quay):
    """OMPS used for testing.

    Args:
        test_env: Dictionary with test environment configuration.
        quay: QuayAppRegistry object, for the Quay instance used by OMPS.

    Returns: An instance of OMPS.
    Raises: None.
    """
    return OMPS(test_env['omps_url'], quay.token)


@pytest.fixture(scope='session')
def koji(test_env):
    """Koji instance configured in OMPS.

    Args:
        test_env: Dictionary with test environment configuration.

    Returns: An instance of Koji.
    Raises: None.
    """
    return Koji(test_env['kojihub'], test_env['kojiroot'])
