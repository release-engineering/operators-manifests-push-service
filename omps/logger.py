#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

"""Configures logging"""

import logging
import time


def init_logging(conf):
    """Initialize logging module"""
    logging.Formatter.converter = time.gmtime  # we want to have logs in UTC
    logging.basicConfig(
        level=conf.log_level,
        format=conf.log_format,
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
