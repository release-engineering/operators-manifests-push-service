#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import logging

import flexmock
import requests
import requests_mock
import pytest

from omps.errors import (
    QuayPackageError,
    QuayPackageNotFound,
)
from omps.quay import (
    get_cnr_api_version,
    QuayOrganization,
    OrgManager,
    ReleaseVersion,
)
from omps.settings import Config


TOKEN = "basic randomtoken"


class TestReleaseVersion:
    """Tests for ReleaseVersion class"""

    @pytest.mark.parametrize('version,expected', [
        ("1.2.3", (1, 2, 3)),
        ("1.0.0", (1, 0, 0)),
        ("0.0.0", (0, 0, 0)),
    ])
    def test_from_str(self, version, expected):
        """Test of creating ReleaseVersion object from string"""
        v = ReleaseVersion.from_str(version)
        assert isinstance(v, ReleaseVersion)
        assert v.version_tuple == expected

    @pytest.mark.parametrize('value', [
        "1",
        "1.2",
        "1.2.3.4",
        "nope",
        "1-5.1.0",
        "-1.2.3",
        "a.b.c",
        "1.01.0",
        "+1.0.0",
        "0x1.0.0",
        "1.1.1a0",
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


class TestQuayOrganization:
    """Tests for QuayOrganization class"""

    org = "org"
    cnr_token = "cnr_token"
    repo = "repo"
    version = "0.0.1"
    source_dir = "/not/important/dir"

    def test_push_operator_manifest(self, mocked_op_courier_push):
        """Test for pushing operator manifest"""

        qo = QuayOrganization(self.org, self.cnr_token)
        qo.push_operator_manifest(self.repo, self.version, self.source_dir)

    def test_push_operator_manifest_publish_repo(self, mocked_op_courier_push):
        """Organizations marked as public will try to publish new
        repositories"""
        qo = QuayOrganization(self.org, self.cnr_token,
                              oauth_token='random', public=True)
        (flexmock(qo)
         .should_receive('publish_repo')
         .and_return(None)
         .once())
        qo.push_operator_manifest(self.repo, self.version, self.source_dir)

    def test_push_operator_manifest_publish_repo_no_public(
            self, mocked_op_courier_push):
        """Make repos won't be published for non-public organizations"""
        qo = QuayOrganization(self.org, self.cnr_token,
                              oauth_token='random', public=False)
        (flexmock(qo)
         .should_receive('publish_repo')
         .and_return(None)
         .never())
        qo.push_operator_manifest(self.repo, self.version, self.source_dir)

    def test_push_operator_manifest_publish_repo_no_oauth(
            self, mocked_op_courier_push, caplog):
        """Make sure that proper warning msg is logged"""
        qo = QuayOrganization(self.org, self.cnr_token,
                              public=True)
        (flexmock(qo)
         .should_receive('publish_repo')
         .and_return(None)
         .never())
        caplog.clear()
        with caplog.at_level(logging.ERROR):
            qo.push_operator_manifest(self.repo, self.version, self.source_dir)
        messages = (rec.message for rec in caplog.records)
        assert any('Oauth access is not configured' in m for m in messages)

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

    def test_get_latest_release_version_invalid_version_only(self):
        """Test if proper exception is raised when packages only with invalid
        version are available

        Invalid versions should be ignored, thus QuayPackageNotFound
        should be raised as may assume that OMPS haven't managed that packages
        previously
        """
        org = "test_org"
        repo = "test_repo"

        with requests_mock.Mocker() as m:
            m.get(
                '/cnr/api/v1/packages/{}/{}'.format(org, repo),
                json=[
                    {'release': "1.0.0-invalid"},
                ],
            )

            qo = QuayOrganization(org, "token")
            with pytest.raises(QuayPackageNotFound):
                qo.get_latest_release_version(repo)

    def test_get_releases_raw(self):
        """Test if all release are returned from quay.io, including format that
        is OMPS invalid"""
        org = "test_org"
        repo = "test_repo"

        with requests_mock.Mocker() as m:
            m.get(
                '/cnr/api/v1/packages/{}/{}'.format(org, repo),
                json=[
                    {'release': "1.0.0"},
                    {'release': "1.2.0"},
                    {'release': "1.0.1-random"},
                ]
            )

            qo = QuayOrganization(org, "token")
            releases = qo.get_releases_raw(repo)
            assert sorted(releases) == ["1.0.0", "1.0.1-random", "1.2.0"]

    def test_get_releases(self):
        """Test if only proper releases are used and returned"""
        org = "test_org"
        repo = "test_repo"

        qo = QuayOrganization(org, TOKEN)
        (flexmock(qo)
         .should_receive('get_releases_raw')
         .and_return(["1.0.0", "1.0.1-random", "1.2.0"])
         )

        expected = [ReleaseVersion.from_str(v) for v in ["1.0.0", "1.2.0"]]

        assert qo.get_releases(repo) == expected

    def test_delete_release(self):
        """Test of deleting releases"""
        org = "test_org"
        repo = "test_repo"
        version = '1.2.3'

        qo = QuayOrganization(org, TOKEN)

        with requests_mock.Mocker() as m:
            m.delete(
                '/cnr/api/v1/packages/{}/{}/{}/helm'.format(
                    org, repo, version),
            )
            qo.delete_release(repo, version)

    @pytest.mark.parametrize('code,exc_class', [
        (requests.codes.not_found, QuayPackageNotFound),
        (requests.codes.method_not_allowed, QuayPackageError),
        (requests.codes.internal_server_error, QuayPackageError),
    ])
    def test_delete_release_quay_error(self, code, exc_class):
        """Test of error handling from quay errors"""
        org = "test_org"
        repo = "test_repo"
        version = '1.2.3'

        qo = QuayOrganization(org, TOKEN)

        with requests_mock.Mocker() as m:
            m.delete(
                '/cnr/api/v1/packages/{}/{}/{}/helm'.format(
                    org, repo, version),
                status_code=code
            )
            with pytest.raises(exc_class):
                qo.delete_release(repo, version)

    def test_publish_repo(self):
        """Test publishing repository"""
        org = 'testorg'
        repo = 'testrepo'

        qo = QuayOrganization(org, TOKEN, oauth_token='randomtoken')

        with requests_mock.Mocker() as m:
            m.post(
                '/api/v1/repository/{org}/{repo}/changevisibility'.format(
                    org=org, repo=repo),
                status_code=requests.codes.ok,
            )
            qo.publish_repo(repo)

    def test_publish_repo_error(self):
        """Test if publishing repository raises proper exception"""
        org = 'testorg'
        repo = 'testrepo'

        qo = QuayOrganization(org, TOKEN, oauth_token='randomtoken')

        with requests_mock.Mocker() as m:
            m.post(
                '/api/v1/repository/{org}/{repo}/changevisibility'.format(
                    org=org, repo=repo),
                status_code=requests.codes.server_error,
            )
            with pytest.raises(QuayPackageError):
                qo.publish_repo(repo)


class TestOrgManager:
    """Tets for OrgManager class"""

    def test_getting_configured_org(self):
        """Test of getting organization instance when org is configured"""

        class ConfClass:
            ORGANIZATIONS = {
                'private_org': {
                    # 'public': False, # Default
                    'oauth_token': 'something',
                },
                'public_org': {
                    'public': True,
                    'oauth_token': 'something_else',
                },
                'public_org_no_token': {
                    'public': True
                }
            }

        conf = Config(ConfClass)
        om = OrgManager()
        om.initialize(conf)

        priv_org = om.get_org('private_org', 'cnr_token')
        assert isinstance(priv_org, QuayOrganization)
        assert not priv_org.public
        assert priv_org.oauth_access

        public_org = om.get_org('public_org', 'cnr_token')
        assert isinstance(public_org, QuayOrganization)
        assert public_org.public
        assert public_org.oauth_access

        public_org_no_token = om.get_org('public_org_no_token', 'cnr_token')
        assert isinstance(public_org_no_token, QuayOrganization)
        assert public_org_no_token.public
        assert not public_org_no_token.oauth_access

    def test_getting_unconfigured_org(self):
        """Test of getting organization instance whne org is not configured in
        settings"""
        class ConfClass:
            ORGANIZATIONS = {}

        conf = Config(ConfClass)
        om = OrgManager()
        om.initialize(conf)

        unconfigured_org = om.get_org('unconfigured_org', 'cnr_token')
        assert isinstance(unconfigured_org, QuayOrganization)
        assert not unconfigured_org.public
        assert not unconfigured_org.oauth_access


def test_get_cnr_api_version(mocked_quay_version):
    """Tests of quay.get_cnr_api_version function"""
    assert get_cnr_api_version() == "0.0.1-test"
