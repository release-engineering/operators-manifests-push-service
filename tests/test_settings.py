#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

"""Tests for omps.settings module"""

from flask import Flask
import pytest

from omps import constants
from omps.settings import Config, DefaultConfig


@pytest.mark.parametrize('key,expected', (
    ("LOG_LEVEL", "INFO"),
    (
        "LOG_FORMAT",
        '%(asctime)s - [%(process)d] %(name)s - %(levelname)s - %(message)s'
    ),
    (
        "ZIPFILE_MAX_UNCOMPRESSED_SIZE",
        constants.DEFAULT_ZIPFILE_MAX_UNCOMPRESSED_SIZE
    ),
    (
        "DEFAULT_RELEASE_VERSION",
        constants.DEFAULT_RELEASE_VERSION,
    ),
    (
        "KOJIHUB_URL",
        "https://koji.fedoraproject.org/kojihub"
    ),
    (
        "KOJIROOT_URL",
        "https://kojipkgs.fedoraproject.org/"
    ),
    ("ORGANIZATIONS", {}),
))
def test_defaults(key, expected):
    """Test if defaults are properly propagated to app config"""

    class ConfClass:
        SECRET_KEY = "secret"

    app = Flask('test_app')
    app.config.from_object(ConfClass)
    conf = Config(ConfClass)
    conf.set_app_defaults(app)

    assert app.config[key] == expected, "failed for key '{}'".format(key)


def test_log_level_debug():
    """Test of setting DEBUG log level"""

    class ConfClass(DefaultConfig):
        LOG_LEVEL = 'DEBUG'

    conf = Config(ConfClass)
    assert conf.log_level == 'DEBUG'


@pytest.mark.parametrize('value', (
    'INVALID',
    10,
    True,
))
def test_log_level_invalid(value):
    """Test of setting invalid log level"""

    class ConfClass(DefaultConfig):
        LOG_LEVEL = value

    with pytest.raises(ValueError):
        Config(ConfClass)


def test_log_format():
    """Test of setting log format"""
    expected = 'Test'

    class ConfClass(DefaultConfig):
        LOG_FORMAT = expected

    conf = Config(ConfClass)
    assert conf.log_format == expected


def test_zipfile_max_uncompressed_size():
    """Test of setting zipfile_max_uncompressed_size"""
    expected = 10

    class ConfClass(DefaultConfig):
        ZIPFILE_MAX_UNCOMPRESSED_SIZE = expected

    conf = Config(ConfClass)
    assert conf.zipfile_max_uncompressed_size == expected


def test_zipfile_max_uncompressed_size_invalid():
    """Test of setting invalid zipfile_max_uncompressed_size"""

    class ConfClass(DefaultConfig):
        ZIPFILE_MAX_UNCOMPRESSED_SIZE = -10

    with pytest.raises(ValueError):
        Config(ConfClass)


def test_organizations():
    """Test of organization settings"""
    expected = {
        'myorg': {
            'public': False,
            'oauth_token': 'token',
        }
    }

    class ConfClass(DefaultConfig):
        ORGANIZATIONS = expected

    conf = Config(ConfClass)
    assert conf.organizations == expected


@pytest.mark.parametrize('conf', [
    {
        'organization': None
    }, {
        'organization_not_allowed/characters': {}
    }, {
        'organization': []
    }, {
        'organization': {
            'public': 'No'
        }
    }, {
        'organization': {
            'oauth_token': 10
        }
    }

])
def test_organizations_invalid(conf):
    """Test if invalid config is properly reported"""

    class ConfClass(DefaultConfig):
        ORGANIZATIONS = conf

    with pytest.raises(ValueError):
        Config(ConfClass)
