#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import os
import pytest
from .utils import OMPS, QuayAppRegistry
from .constants import TEST_PACKAGE


@pytest.fixture(scope='session')
def quay():
    """Quay App Registry used for testing.

    Args: None.
    Yields: An instance of QuayAppRegistry.
    Raises: None.
    """
    app_registry = QuayAppRegistry(os.getenv('OMPS_INT_TEST_QUAY_URL'))
    username = os.getenv('OMPS_INT_TEST_QUAY_USER')
    password = os.getenv('OMPS_INT_TEST_QUAY_PASSWD')
    app_registry.login(username, password)

    yield app_registry

    organization = os.getenv('OMPS_INT_TEST_OMPS_ORG')
    app_registry.clean_up(organization, TEST_PACKAGE)


@pytest.fixture(scope='session')
def omps(quay):
    """OMPS used for testing.

    Args:
        quay: QuayAppRegistry object, for the Quay instance used by OMPS.

    Returns: An instance of OMPS.
    Raises: None.
    """
    api_url = os.getenv('OMPS_INT_TEST_OMPS_URL')

    return OMPS(api_url, quay.token)
