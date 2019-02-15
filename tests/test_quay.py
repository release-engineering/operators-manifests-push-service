#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import pytest

from omps.errors import OMPSOrganizationNotFound, QuayLoginError
from omps.quay import QuayOrganizationManager, QuayOrganization
from omps.settings import TestConfig, Config


class TestQuayOrganizationManager:
    """Tests for QuayOrganizationManager class"""

    def test_organization_login(self, mocked_quay_login):
        """Test successful org login"""
        qom = QuayOrganizationManager()
        conf = Config(TestConfig)
        qom.init_from_config(conf)

        org = qom.organization_login('testorg')
        assert isinstance(org, QuayOrganization)

    def test_organization_login_org_not_found(self, mocked_quay_login):
        """Test login to not configured org"""
        qom = QuayOrganizationManager()
        conf = Config(TestConfig)
        qom.init_from_config(conf)
        with pytest.raises(OMPSOrganizationNotFound):
            qom.organization_login('org_not_configured')

    def test_organization_login_failed(self, mocked_failed_quay_login):
        """Test login with invalid credentials"""
        qom = QuayOrganizationManager()
        # credentials are valid here, failure is mocked
        conf = Config(TestConfig)
        qom.init_from_config(conf)
        with pytest.raises(QuayLoginError):
            qom.organization_login('testorg')
