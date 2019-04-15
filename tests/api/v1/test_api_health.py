#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import requests
import requests_mock

from omps.errors import KojiError, GreenwaveError


PING_ENDPOINT = '/v1/health/ping'


def test_health_ping(client, mocked_koji_get_api_version, mocked_quay_version):
    """Test reporting of ok status"""
    rv = client.get(PING_ENDPOINT)

    expected = {
        "ok": True,
        "status": requests.codes.ok,
        "services": {
            "koji": {
                "ok": True,
                "details": "It works!"
            },
            "quay": {
                "ok": True,
                "details": "It works!"
            },
            "greenwave": None,
        }
    }

    assert rv.status_code == requests.codes.ok
    assert rv.get_json() == expected


def test_health_ping_with_greenwave(
    client, mocked_koji_get_api_version, mocked_quay_version,
    mocked_greenwave_get_version
):
    """Test reporting of ok status"""
    rv = client.get(PING_ENDPOINT)

    expected = {
        "ok": True,
        "status": requests.codes.ok,
        "services": {
            "koji": {
                "ok": True,
                "details": "It works!"
            },
            "quay": {
                "ok": True,
                "details": "It works!"
            },
            "greenwave": {
                "ok": True,
                "details": "It works!"
            },
        }
    }

    assert rv.status_code == requests.codes.ok
    assert rv.get_json() == expected


def test_health_ping_broken_quay(client, mocked_koji_get_api_version):
    """Test if broken quay is reported properly"""
    with requests_mock.Mocker() as m:
        m.get(
            'https://quay.io/cnr/version',
            status_code=requests.codes.server_error
        )
        rv = client.get(PING_ENDPOINT)

    expected = {
        "ok": False,
        "status": requests.codes.unavailable,
        "services": {
            "koji": {
                "ok": True,
                "details": "It works!"
            },
            "quay": {
                "ok": False,
                "details": (
                    "500 Server Error: None for url: "
                    "https://quay.io/cnr/version"
                )
            },
            "greenwave": None,
        }
    }
    assert rv.status_code == requests.codes.unavailable
    assert rv.get_json() == expected


def test_health_ping_broken_koji(
    client, mocked_quay_version, mocked_koji_get_api_version
):
    """Test if broken koji is reported properly"""
    e_msg = "something happened"
    mocked_koji_get_api_version.side_effect = KojiError(e_msg)

    rv = client.get(PING_ENDPOINT)

    expected = {
        "ok": False,
        "status": requests.codes.unavailable,
        "services": {
            "koji": {
                "ok": False,
                "details": e_msg
            },
            "quay": {
                "ok": True,
                "details": "It works!"
            },
            "greenwave": None,
        }
    }
    assert rv.status_code == requests.codes.unavailable
    assert rv.get_json() == expected


def test_health_ping_broken_greenwave(
    client, mocked_quay_version, mocked_koji_get_api_version,
    mocked_greenwave_get_version
):
    """Test if broken koji is reported properly"""
    e_msg = "something happened"
    mocked_greenwave_get_version.side_effect = GreenwaveError(e_msg, {})

    rv = client.get(PING_ENDPOINT)

    expected = {
        "ok": False,
        "status": requests.codes.unavailable,
        "services": {
            "koji": {
                "ok": True,
                "details": "It works!"
            },
            "quay": {
                "ok": True,
                "details": "It works!"
            },
            "greenwave": {
                "ok": False,
                "details": e_msg
            },
        }
    }
    assert rv.status_code == requests.codes.unavailable
    assert rv.get_json() == expected
