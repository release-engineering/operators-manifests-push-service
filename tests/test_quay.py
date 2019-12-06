#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import logging

import flexmock
import requests
import requests_mock
import pytest
from operatorcourier.errors import (
    OpCourierQuayErrorResponse,
    OpCourierBadBundle,
    OpCourierError,
    OpCourierQuayError,
    OpCourierQuayCommunicationError,
    OpCourierValueError,
    OpCourierBadYaml
)

from omps.errors import (
    QuayCourierError,
    QuayPackageError,
    QuayPackageNotFound,
    QuayAuthorizationError,
    PackageValidationError
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

    @pytest.mark.usefixtures('mocked_op_courier_push')
    def test_push_operator_manifest(self):
        """Test for pushing operator manifest"""

        qo = QuayOrganization(self.org, self.cnr_token)
        qo.push_operator_manifest(self.repo, self.version, self.source_dir)

    @pytest.mark.parametrize('courier_exception', [
        OpCourierError('a'),
        OpCourierQuayError('b'),
        OpCourierQuayCommunicationError('c'),
        OpCourierValueError('d')
    ])
    def test_generic_courier_error(self, courier_exception,
                                   caplog, op_courier_push_raising):
        """Test that all the courier exceptions meant to be handled
        in a generic way are in fact handled that way"""
        expected_dict = {
            'status': 500,
            'error': 'QuayCourierError',
            'message': f'Failed to push manifest: {courier_exception}',
            'quay_response': {}
        }

        self._test_courier_exception(courier_exception,
                                     QuayCourierError,
                                     expected_dict,
                                     caplog,
                                     op_courier_push_raising)

    @pytest.mark.parametrize('courier_exception', [
        OpCourierBadYaml('Bad yaml.')
    ])
    def test_courier_invalid_files_error(self, courier_exception,
                                         caplog, op_courier_push_raising):
        """Test that the proper exception is raised when courier reports
        an error while building bundle (invalid yaml/artifact)"""
        expected_dict = {
            'status': 400,
            'error': 'PackageValidationError',
            'message': f'Failed to push manifest: {courier_exception}',
            'validation_info': {}
        }

        self._test_courier_exception(courier_exception,
                                     PackageValidationError,
                                     expected_dict,
                                     caplog,
                                     op_courier_push_raising)

    def test_courier_invalid_bundle_error(self, caplog,
                                          op_courier_push_raising):
        """Test that the proper exception is raised when courier reports
        a validation error after building bundle"""
        validation_info = {'errors': ['this one', 'this one too']}
        error = OpCourierBadBundle('Bad bundle.', validation_info)
        expected_dict = {
            'status': 400,
            'error': 'PackageValidationError',
            'message': f'Failed to push manifest: {error}',
            'validation_info': validation_info
        }

        self._test_courier_exception(error,
                                     PackageValidationError,
                                     expected_dict,
                                     caplog,
                                     op_courier_push_raising)

    def test_courier_quay_authorization_error(self, caplog,
                                              op_courier_push_raising):
        """Test that the proper exception is raised when courier reports
        a Quay authorization error"""
        error_response = {'error': 'something with authorization'}
        error = OpCourierQuayErrorResponse('Quay error.', 403, error_response)
        expected_dict = {
            'status': 403,
            'error': 'QuayAuthorizationError',
            'message': f'Failed to push manifest: {error}',
            'quay_response': error_response
        }

        self._test_courier_exception(error,
                                     QuayAuthorizationError,
                                     expected_dict,
                                     caplog,
                                     op_courier_push_raising)

    def _test_courier_exception(self, courier_exception,
                                expected_omps_exception, expected_dict,
                                caplog, op_courier_push_raising):
        qo = QuayOrganization(self.org, self.cnr_token)

        with op_courier_push_raising(courier_exception):
            with pytest.raises(expected_omps_exception) as exc_info, \
                    caplog.at_level(logging.ERROR):
                qo.push_operator_manifest(self.repo,
                                          self.version,
                                          self.source_dir)

        e = exc_info.value
        assert e.to_dict() == expected_dict
        assert any('Operator courier call failed' in message
                   for message in caplog.messages)

    @pytest.mark.usefixtures('mocked_op_courier_push')
    def test_push_operator_manifest_publish_repo(self):
        """Organizations marked as public will try to publish new
        repositories"""
        qo = QuayOrganization(self.org, self.cnr_token,
                              oauth_token='random', public=True)
        (flexmock(qo)
         .should_receive('publish_repo')
         .and_return(None)
         .once())
        qo.push_operator_manifest(self.repo, self.version, self.source_dir)

    @pytest.mark.usefixtures('mocked_op_courier_push')
    def test_push_operator_manifest_publish_repo_no_public(self):
        """Make repos won't be published for non-public organizations"""
        qo = QuayOrganization(self.org, self.cnr_token,
                              oauth_token='random', public=False)
        (flexmock(qo)
         .should_receive('publish_repo')
         .and_return(None)
         .never())
        qo.push_operator_manifest(self.repo, self.version, self.source_dir)

    @pytest.mark.usefixtures('mocked_op_courier_push')
    def test_push_operator_manifest_publish_repo_no_oauth(self, caplog):
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
                f'/cnr/api/v1/packages?namespace={org}',
                json=[
                    {
                        'name': 'org/something_else',
                        'releases': ["2.0.0"],
                    },
                    {
                        'name': f'{org}/{repo}',
                        'releases': ["1.2.0", "1.1.0", "1.0.0"]
                    },
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
                f'/cnr/api/v1/packages?namespace={org}',
                json=[
                    {
                        'name': 'org/something_else',
                        'releases': ["2.0.0"],
                    }
                ]
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
                f'/cnr/api/v1/packages?namespace={org}',
                json=[
                    {
                        'name': f'{org}/{repo}',
                        'releases': ["1.0.0-invalid"]
                    },
                ]
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
                f'/cnr/api/v1/packages?namespace={org}',
                json=[
                    {
                        'name': 'org/something_else',
                        'releases': ["2.0.0"],
                    },
                    {
                        'name': f'{org}/{repo}',
                        'releases': ["1.2.0", "1.0.1-random", "1.0.0"]
                    },
                ]
            )

            qo = QuayOrganization(org, "token")
            releases = qo.get_releases_raw(repo)
            assert sorted(releases) == ["1.0.0", "1.0.1-random", "1.2.0"]

    @pytest.mark.parametrize('error_code, expected_exc_type', [
        (403, QuayAuthorizationError),
        (500, QuayPackageError)
    ])
    def test_get_releases_raw_errors(self, error_code, expected_exc_type):
        """Test that the proper exceptions are raised for various kinds
        of HTTP errors"""
        org = "test_org"
        repo = "test_repo"

        qo = QuayOrganization(org, TOKEN)

        with requests_mock.Mocker() as m:
            m.get(f'/cnr/api/v1/packages?namespace={org}',
                  status_code=error_code)

            with pytest.raises(expected_exc_type):
                qo.get_releases_raw(repo)

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

    @pytest.mark.parametrize('enabled', [True, False])
    def test_registry_replacing_enabled(self, enabled):
        """Test if property returns correct value"""
        if enabled:
            replace_conf = [{'old': 'reg_old', 'new': 'reg_new'}]
        else:
            replace_conf = None

        org = 'testorg'

        qo = QuayOrganization(org, TOKEN, replace_registry_conf=replace_conf)

        assert qo.registry_replacing_enabled == enabled

    @pytest.mark.parametrize('text,expected', [
        (
            'Registry reg_old will be replaced',
            'Registry reg_new will be replaced'
        ),
        (
            'Registry nope will not be replaced',
            'Registry nope will not be replaced',
        ),
    ])
    def test_replace_registries(self, text, expected):
        """Test if registries are replaced properly"""
        replace_conf = [{'old': 'reg_old', 'new': 'reg_new'}]
        org = 'testorg'
        qo = QuayOrganization(org, TOKEN, replace_registry_conf=replace_conf)
        assert qo.replace_registries(text) == expected

    def test_replace_registries_unconfigured(self):
        """Test if replace operation returns unchanged text"""
        org = 'testorg'
        qo = QuayOrganization(org, TOKEN)
        text = 'text'

        res = qo.replace_registries(text)
        assert res == text
        assert id(res) == id(text)

    @pytest.mark.parametrize('text,expected', [
        (
            'Registry reg_old will be replaced using a regexp: reg_old',
            'Registry reg_old will be replaced using a regexp: reg_new',
        )
    ])
    def test_regexp_replace_registries(self, text, expected):
        """Test if registries are replaced properly with regexp"""
        replace_conf = [{'old': 'reg_old$', 'new': 'reg_new', 'regexp': True}]
        org = 'testorg'
        qo = QuayOrganization(org, TOKEN, replace_registry_conf=replace_conf)
        assert qo.replace_registries(text) == expected


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
                },
                'private_org_replacing_registries': {
                    'replace_registry': [
                        {'new': 'reg1', 'old': 'reg2'},
                    ]
                }
            }

        conf = Config(ConfClass)
        om = OrgManager()
        om.initialize(conf)

        priv_org = om.get_org('private_org', 'cnr_token')
        assert isinstance(priv_org, QuayOrganization)
        assert not priv_org.public
        assert priv_org.oauth_access
        assert not priv_org.registry_replacing_enabled

        public_org = om.get_org('public_org', 'cnr_token')
        assert isinstance(public_org, QuayOrganization)
        assert public_org.public
        assert public_org.oauth_access
        assert not public_org.registry_replacing_enabled

        public_org_no_token = om.get_org('public_org_no_token', 'cnr_token')
        assert isinstance(public_org_no_token, QuayOrganization)
        assert public_org_no_token.public
        assert not public_org_no_token.oauth_access
        assert not public_org_no_token.registry_replacing_enabled

        priv_org_replacing_registries = om.get_org(
            'private_org_replacing_registries', 'cnr_token')
        assert isinstance(priv_org_replacing_registries, QuayOrganization)
        assert not priv_org_replacing_registries.public
        assert not priv_org_replacing_registries.oauth_access
        assert priv_org_replacing_registries.registry_replacing_enabled

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


@pytest.mark.usefixtures('mocked_quay_version')
def test_get_cnr_api_version():
    """Tests of quay.get_cnr_api_version function"""
    assert get_cnr_api_version(0) == "0.0.1-test"
