#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

"""Configures logging"""

import logging


def init_logging(conf):
    """Initialize logging module"""
    logging.basicConfig(level=conf.log_level, format=conf.log_format)
