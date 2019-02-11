#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

"""Tests for omps.settings module"""

import pytest

from omps.settings import Config, DefaultConfig


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
