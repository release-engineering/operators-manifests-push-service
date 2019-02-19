#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import requests_mock
import pytest

from omps.errors import (
    OMPSOrganizationNotFound,
    QuayPackageNotFound,
    QuayLoginError
)
from omps.quay import QuayOrganizationManager, QuayOrganization, ReleaseVersion
from omps.settings import TestConfig, Config


class TestReleaseVersion:
    """Tests for ReleaseVersion class"""

    def test_from_str(self):
        """Test of creating ReleaseVersion object from string"""
        version = ReleaseVersion.from_str("1.2.3")
        assert isinstance(version, ReleaseVersion)
        assert version.version_tuple == (1, 2, 3)

    @pytest.mark.parametrize('value', [
        "1",
        "1.2",
        "1.2.3.4",
        "nope",
        "1-5.1.0",
        "-1.2.3",
        "a.b.c",
    ])
    def test_from_str_invalid(self, value):
        """Test if error is properly raised for invalid input"""
        with pytest.raises(ValueError):
            ReleaseVersion.from_str(value)

    def test_to_str(self):
        """Test textual representation"""
        version = ReleaseVersion(1, 2, 3)
        assert str(version) == "1.2.3"

    @pytest.mark.parametrize('from_version, expected', [
        ("1.2.3", "2.0.0"),
        ("1.0.0", "2.0.0"),
    ])
    def test_increment(self, from_version, expected):
        """Test if incrementation of version works as expected"""
        version = ReleaseVersion.from_str(from_version)
        version.increment()
        assert str(version) == expected

    def test_ordering(self):
        """Test if ordering works as expected"""
        min_version = ReleaseVersion.from_str("1.0.0")
        mid_version = ReleaseVersion.from_str("1.2.3")
        max_version = ReleaseVersion.from_str("2.0.0")

        versions = (max_version, min_version, mid_version)

        assert min_version == min_version
        assert min_version != max_version
        assert min_version != mid_version
        assert min_version < mid_version < max_version
        assert max_version > mid_version > min_version
        assert min_version == min(versions)
        assert max_version == max(versions)

    @pytest.mark.parametrize('value', ["2.0.0", (2, 0, 0), 2])
    def test_ordering_other_types(self, value):
        """Test if a proper exception is raised when comparing to unsupported
        types"""
        version = ReleaseVersion.from_str("1.0.0")
        with pytest.raises(TypeError):
            assert version < value


class TestQuayOrganizationManager:
    """Tests for QuayOrganizationManager class"""

    def test_organization_login(self, mocked_quay_io):
        """Test successful org login"""
        qom = QuayOrganizationManager()
        conf = Config(TestConfig)
        qom.init_from_config(conf)

        org = qom.organization_login('testorg')
        assert isinstance(org, QuayOrganization)

    def test_organization_login_org_not_found(self, mocked_quay_io):
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


class TestQuayOrganization:
    """Tests for QuayOrganization class"""

    def test_push_operator_manifest(self, mocked_op_courier_push):
        """Test for pushing operator manifest"""
        org = "org"
        token = "token"
        repo = "repo"
        version = "0.0.1"
        source_dir = "/not/important/dir"

        qo = QuayOrganization(org, token)
        qo.push_operator_manifest(repo, version, source_dir)

    def test_get_latest_release_version(self):
        """Test getting the latest release version"""
        org = "test_org"
        repo = "test_repo"

        with requests_mock.Mocker() as m:
            m.get(
                '/cnr/api/v1/packages/{}/{}'.format(org, repo),
                json=[
                    {'release': "1.0.0"},
                    {'release': "1.2.0"},
                    {'release': "1.0.1"},
                ]
            )

            qo = QuayOrganization(org, "token")
            latest = qo.get_latest_release_version(repo)
            assert str(latest) == "1.2.0"

    def test_get_latest_release_version_not_found(self):
        """Test if proper exception is raised when no package is not found"""
        org = "test_org"
        repo = "test_repo"

        with requests_mock.Mocker() as m:
            m.get(
                '/cnr/api/v1/packages/{}/{}'.format(org, repo),
                status_code=404,
            )

            qo = QuayOrganization(org, "token")
            with pytest.raises(QuayPackageNotFound):
                qo.get_latest_release_version(repo)
