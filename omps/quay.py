#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

"""Module related to quay operations"""
import logging

import jsonschema
import requests

from .errors import (
    QuayLoginError,
    OMPSOrganizationNotFound,
)

logger = logging.getLogger(__name__)


class QuayOrganizationManager:
    """Class responsible for handling configured organizations"""

    SCHEMA_ORGANIZATIONS = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Configuration for accessing Quay.io organizations",
        "type": ["object"],
        "patternProperties": {
            "^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}": {
                "description": "Organization name",
                "type": "object",
                "properties": {
                    "username": {
                        "description": "quay.io username",
                        "type": "string",
                    },
                    "password": {
                        "description": "quay.io password",
                        "type": "string",
                    },
                },
                "required": ['username', 'password'],
            },
        },
        "uniqueItems": True,
        "additionalProperties": False,
    }

    @classmethod
    def validate_config(cls, organizations):
        """Validate quay organizations configuration

        :param organizations: dictionary with configuration
        :raises jsonschema.ValidationError: when configuration doesn't meet
            expectations
        """
        jsonschema.validate(organizations, cls.SCHEMA_ORGANIZATIONS)

    def __init__(self):
        self._organizations = {}
        self._quay_url = "https://quay.io"

    def init_from_config(self, config):
        """Initialize object from config"""
        self.validate_config(config.quay_organizations)
        self._organizations = config.quay_organizations
        if not self._organizations:
            logger.error('No organizations configured')

    def _login(self, username, password):
        endpoint = '/cnr/api/v1/users/login'
        data = {
            "user": {
                "username": username,
                "password": password,
            },
        }
        url = self._quay_url + endpoint
        r = requests.post(url, json=data)

        if r.status_code != requests.codes.ok:
            details = 'unknown details'
            try:
                details = r.json()['error']
            except Exception:
                pass
            msg = 'Failed to login: {} ({})'.format(r.status_code, details)
            logger.error(msg)
            raise QuayLoginError(msg)

        content = r.json()
        if 'token' not in content:
            raise QuayLoginError("Answer from quay doesn't contain token")
        return content['token']

    def organization_login(self, organization):
        """Login to organization and return QuayOrganization object

        :param organization: organization name
        :return: QuayOrganization object
        """
        org_config = self._organizations.get(organization)
        if org_config is None:
            raise OMPSOrganizationNotFound(
                "Organization '{}' not found in configuration".format(
                    organization
                )
            )
        token = self._login(org_config['username'], org_config['password'])
        return QuayOrganization(organization, token)


class QuayOrganization:
    """Class for operations on organization"""

    def __init__(self, organization, token):
        """
        :param organization: organization name
        :param token: organization login token
        """
        self._organization = organization
        self._token = token


QUAY_ORG_MANAGER = QuayOrganizationManager()
