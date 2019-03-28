#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from functools import partial

from flask import request

from . import API
from omps.api.v1.push import (
    extract_zip_file_from_koji,
    extract_zip_file_from_request,
    _zip_flow,
)


@API.route("/<organization>/zipfile", defaults={"version": None},
           methods=('POST',))
@API.route("/<organization>/zipfile/<version>", methods=('POST',))
def push_zipfile(organization, version=None):
    # V2 has the same implementation as V1
    return _zip_flow(
        organization=organization,
        repo=None,
        version=version,
        extract_manifest_func=partial(extract_zip_file_from_request, request)
    )


@API.route("/<organization>/koji/<nvr>", defaults={"version": None},
           methods=('POST',))
@API.route("/<organization>/koji/<nvr>/<version>", methods=('POST',))
def push_koji_nvr(organization, nvr, version):
    # V2 has the same implementation as V1
    return _zip_flow(
        organization=organization,
        repo=None,
        version=version,
        extract_manifest_func=partial(extract_zip_file_from_koji, nvr),
        extras_data={'nvr': nvr}
    )
