#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

""" Defines shared functions for API """

import logging
import os

from omps.errors import OMPSAuthorizationHeaderRequired


logger = logging.getLogger(__name__)


def extract_auth_token(req):
    """Extracts auth token from request header

    :param req: Flask request
    :rtype: str
    :return: Auth token
    """
    auth_header = req.headers.get('Authorization', None)
    if auth_header is None:
        raise OMPSAuthorizationHeaderRequired(
            "Request contains no 'Authorization' header")

    return auth_header


def replace_registries(quay_org, dir_path):
    """Replace registries URLs in manifests files"""
    if not quay_org.registry_replacing_enabled:
        return

    logger.info("Replacing registries URLs for organization: %s",
                quay_org.organization)

    for filename in _yield_yaml_files(dir_path):
        with open(filename, 'r') as f:
            text = f.read()

        text = quay_org.replace_registries(text)
        with open(filename, 'w') as f:
            f.write(text)
            f.flush()


def _yield_yaml_files(dir_path):
    """Helper function to iterate only through yaml files"""
    for root, _, files in os.walk(dir_path):
        for fname in files:
            fname_lower = fname.lower()
            if fname_lower.endswith('.yml') or fname_lower.endswith('.yaml'):
                yield os.path.join(root, fname)
