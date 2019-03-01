#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#
import logging

from flask import jsonify
import requests

from . import API
from omps.quay import QUAY_ORG_MANAGER

logger = logging.getLogger(__name__)


@API.route("/<organization>/<repo>", defaults={'version': None},
           methods=('DELETE',))
@API.route("/<organization>/<repo>/<version>", methods=('DELETE',))
def delete_package_release(organization, repo, version=None):
    """
    Delete particular version of released package from quay.io

    :param organization: quay.io organization
    :param repo: target repository
    :param version: version of operator manifest
    :return: HTTP response
    """
    quay_org = QUAY_ORG_MANAGER.organization_login(organization)

    # quay.io may contain OMPS incompatible release version format string
    # but we want to be able to delete everything there, thus using _raw
    # method
    if version is None:
        versions = quay_org.get_releases_raw(repo)
    else:
        versions = [version]

    for ver in versions:
        quay_org.delete_release(repo, ver)

    data = {
        'organization': organization,
        'repo': repo,
        'deleted': versions,
    }

    resp = jsonify(data)
    resp.status_code = requests.codes.ok
    return resp
