#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import logging

from jsonschema import validate
import requests

from omps.errors import (
    GreenwaveError,
    GreenwaveUnsatisfiedError
)

logger = logging.getLogger(__name__)


class GreenwaveHelper:
    """Greenwave helper"""

    SCHEMA_CONFIG = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Configuration for Greenwave queries",
        "type": "object",
        "properties": {
            "url": {
                "description": "URL of Greenwave instance",
                "type": "string",
            },
            "context": {
                "description": "Greenwave decsion_context",
                "type": "string",
            },
            "product_version": {
                "description": "Greenwave product_version",
                "type": "string",
            },
        },
        "required": ["url", "context", "product_version"]
    }

    @classmethod
    def validate_conf(cls, greenwave_conf):
        """Validate if config meets the schema expectations

        :param dict greenwave_conf: organizations config
        :raises jsonschema.ValidationError: when config doesn't meet criteria
        """
        validate(greenwave_conf, cls.SCHEMA_CONFIG)

    def __init__(self):
        self._url = None
        self._context = None
        self._product_version = None
        self._timeout = None

    def initialize(self, conf):
        if conf.greenwave is None:
            logger.warning("Greenwave is not configured!")
            return

        self.validate_conf(conf.greenwave)
        self._timeout = conf.request_timeout
        self._url = conf.greenwave["url"]
        self._context = conf.greenwave["context"]
        self._product_version = conf.greenwave["product_version"]
        if not self._url.endswith('/'):
            self._url += "/"

    @property
    def enabled(self):
        return self._url is not None

    def check_build(self, nvr):
        """Check if build passed greenwave checks

        :param str nvr: Build nvr to be checked
        """
        endpoint = "api/v1.0/decision"

        logger.info("'check_build' for %s", nvr)
        if not self.enabled:
            raise RuntimeError("Greenwave is not configured")

        payload = dict(
            decision_context=self._context,
            product_version=self._product_version,
            subject_identifier=nvr,
            subject_type='koji_build',
        )
        try:
            response = requests.post(
                f"{self._url}{endpoint}", json=payload, timeout=self._timeout)
        except requests.exceptions.RequestException as e:
            logger.exception("Greenwave request failed")
            raise GreenwaveError(f"Request failed: {e}", {})
        else:
            try:
                data = response.json()
            except ValueError:
                data = {}

            logger.debug("Greenwave details for %s: %s", nvr, data)
            if response.status_code != requests.codes.ok:
                raise GreenwaveError(
                    f"Greenwave unexpected response code: "
                    f"{response.status_code}", data)

            try:
                satisfied = data["policies_satisfied"]
            except KeyError:
                raise GreenwaveError(
                    f"Missing key 'policies_satisfied' in answer for nvr"
                    f" {nvr}", data)

            if not satisfied:
                raise GreenwaveUnsatisfiedError(
                    f"Policies for nvr {nvr} were not satisfied", data)

            logger.info("check_build for %s: passed", nvr)


GREENWAVE = GreenwaveHelper()
