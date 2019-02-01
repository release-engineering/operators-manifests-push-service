#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from flask import Blueprint, jsonify

BLUEPRINT = Blueprint('push', __name__)


@BLUEPRINT.route("/<organization>/<repo>/zipfile", methods=('POST',))
def push_zipfile(organization, repo):
    """
    Push operator manifest to registry from uploaded zipfile

    :param organization: quay.io organization
    :param repo: target repository
    """
    data = {
        'organization': organization,
        'repo': repo,
        'msg': 'Not Implemented. Testing only'
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp


@BLUEPRINT.route("/<organization>/<repo>/koji/<nvr>", methods=('POST',))
def push_koji_nvr(organization, repo, nvr):
    """
    Get operator manifest from koji by specified NVR and upload operator
    manifest to registry
    :param organization: quay.io organization
    :param repo: target repository
    :param nvr: image NVR from koji
    """
    data = {
        'organization': organization,
        'repo': repo,
        'nvr': nvr,
        'msg': 'Not Implemented. Testing only'
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
