#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import logging

from flask import jsonify, current_app
import requests
from requests.exceptions import RequestException

from . import API
from omps.errors import KojiError
from omps.quay import get_cnr_api_version
from omps.koji_util import KOJI

logger = logging.getLogger(__name__)


@API.route("/health/ping", methods=('GET', ))
def ping():
    """Provides status report
     * 200 if everything is ok
     * 503 if service is not working as expected
    :return: HTTP Response
    """
    def _ok():
        return {
            "ok": True,
            "details": "It works!",
        }

    def _err(exc):
        return {
            "ok": False,
            "details": str(exc)
        }

    everything_ok = True

    # quay.io status
    try:
        # try to retrieve API version to check if quay.io is alive
        get_cnr_api_version(current_app.config['REQUEST_TIMEOUT'])
    except RequestException as e:
        logger.error('Quay version check: %s', e)
        quay_result = _err(e)
        everything_ok = False
    else:
        quay_result = _ok()

    # koji status
    try:
        # try to retrieve API version to check if koji is alive
        KOJI.get_api_version()
    except KojiError as e:
        logger.error('Koji version check: %s', e)
        koji_result = _err(e)
        everything_ok = False
    else:
        koji_result = _ok()

    status_code = (
        requests.codes.ok if everything_ok
        else requests.codes.unavailable
    )

    data = {
        "ok": everything_ok,
        "status": status_code,
        "services": {
            "koji": koji_result,
            "quay": quay_result
        }
    }

    resp = jsonify(data)
    resp.status_code = status_code
    return resp
