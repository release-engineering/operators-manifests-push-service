#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import pytest
import requests
import requests_mock

from omps.errors import (
    GreenwaveError,
    GreenwaveUnsatisfiedError,
)
from omps.greenwave import GreenwaveHelper
from omps.settings import Config


class TestGreenwaveHelper:
    """Tests for GreenwaveHelper class"""

    g_url = "https://greenwave.example.com"
    g_context = 'omps_push'
    g_product_version = 'cvp'
    test_nvr = 'test-1.0.1-58'

    def _get_instance(self):

        class ConfClass:
            GREENWAVE = {
                "url": self.g_url,
                "context": self.g_context,
                "product_version": self.g_product_version
            }

        conf = Config(ConfClass)
        gh = GreenwaveHelper()
        gh.initialize(conf)
        return gh

    def test_enabled(self):
        """Test if property "enabled" reports correctly configured instance"""
        gh = self._get_instance()
        assert gh.enabled

    def test_enabled_false(self):
        """Test if property "enabled" reports correctly not configured
        instance"""
        gh = GreenwaveHelper()
        assert not gh.enabled

    def _check_greenwave_request(self, req):
        """test if query contains expected fields"""
        req_data = req.json()
        expected = {
            "decision_context": self.g_context,
            "product_version": self.g_product_version,
            "subject_identifier": self.test_nvr,
            "subject_type": "koji_build"
        }
        assert req_data == expected
        return True

    def test_check_build(self):
        """Test getting information about passing checks from Greenwave"""
        gh = self._get_instance()
        with requests_mock.Mocker() as m:
            m.post(
                f"{self.g_url}/api/v1.0/decision",
                json={
                    "policies_satisfied": True,
                    "summary": "ok"
                },
            )
            gh.check_build(self.test_nvr)
            self._check_greenwave_request(m.last_request)

    def test_check_build_unconfigured(self):
        """Test if proper exception is raised when Greenwave is not
        configured"""
        gh = GreenwaveHelper()
        with pytest.raises(RuntimeError):
            gh.check_build(self.test_nvr)

    def test_check_build_policy_failed(self):
        """Test if proper exception is raise when policy check at Greenwave
        failed"""
        gh = self._get_instance()
        with requests_mock.Mocker() as m:
            m.post(
                f"{self.g_url}/api/v1.0/decision",
                json={
                    "policies_satisfied": False,
                    "summary": "Policies failed ..."
                },
            )
            with pytest.raises(GreenwaveUnsatisfiedError):
                gh.check_build(self.test_nvr)

    def test_check_build_policy_missing_key(self):
        """Test if proper exception is raise when Greenwave answer doesn't
        contain `policies_satisfied` key"""
        gh = self._get_instance()
        with requests_mock.Mocker() as m:
            m.post(
                f"{self.g_url}/api/v1.0/decision",
                json={
                    # "policies_satisfied": True  # missing for test purpose
                    "summary": "Policies failed ..."
                },
            )
            with pytest.raises(GreenwaveError):
                gh.check_build(self.test_nvr)

    def test_check_build_http_error(self):
        """Test if proper exception is raise when an HTTPError is returned"""
        gh = self._get_instance()
        with requests_mock.Mocker() as m:
            m.post(
                f"{self.g_url}/api/v1.0/decision",
                status_code=requests.codes.server_error
            )
            with pytest.raises(GreenwaveError):
                gh.check_build(self.test_nvr)

    def test_check_build_connection_error(self):
        """Test if proper exception is raise when an connection error is
        returned"""
        def _raise_request_err(*args, **kwargs):
            raise requests.exceptions.RequestException("Test exception")

        gh = self._get_instance()
        with requests_mock.Mocker() as m:
            m.post(
                f"{self.g_url}/api/v1.0/decision",
                content=_raise_request_err
            )
            with pytest.raises(GreenwaveError):
                gh.check_build(self.test_nvr)

    def test_get_version(self):
        """Test of getting greenwave version"""
        gh = self._get_instance()
        version = "1.2.3"
        with requests_mock.Mocker() as m:
            m.get(
                f"{self.g_url}/api/v1.0/about",
                json={
                    "version": version
                },
            )
            assert gh.get_version() == version

    def test_get_version_unconfigured(self):
        """Test if proper exception is raised when Greenwave is not
        configured"""
        gh = GreenwaveHelper()
        with pytest.raises(RuntimeError):
            gh.get_version()

    def test_get_version_missing_key(self):
        """Test if proper exception si raised when response doesn't contain
        version key"""
        gh = self._get_instance()
        with requests_mock.Mocker() as m:
            m.get(
                f"{self.g_url}/api/v1.0/about",
                json={},
            )
            with pytest.raises(GreenwaveError):
                gh.get_version()

    def test_get_version_error_response(self):
        """Test if proper exception is raised when error response is received
        """
        gh = self._get_instance()
        with requests_mock.Mocker() as m:
            m.get(
                f"{self.g_url}/api/v1.0/about",
                status_code=requests.codes.server_error
            )
            with pytest.raises(GreenwaveError):
                gh.get_version()
