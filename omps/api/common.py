#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

""" Defines shared functions for API """

from omps.errors import OMPSAuthorizationHeaderRequired


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
