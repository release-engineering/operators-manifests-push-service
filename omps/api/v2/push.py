#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from . import API
from omps.api.v1.push import (
    push_zipfile as push_zipfile_v1,
    push_koji_nvr as push_koji_nvr_v1,
)

@API.route("/<organization>/<repo>/zipfile", defaults={"version": None},
           methods=('POST',))
@API.route("/<organization>/<repo>/zipfile/<version>", methods=('POST',))
def push_zipfile(organization, repo, version=None):
    # V2 has the same implementation as V1
    return push_zipfile_v1(organization, repo, version)


@API.route("/<organization>/<repo>/koji/<nvr>", defaults={"version": None},
           methods=('POST',))
@API.route("/<organization>/<repo>/koji/<nvr>/<version>", methods=('POST',))
def push_koji_nvr(organization, repo, nvr, version):
    # V2 has the same implementation as V1
    return push_koji_nvr_v1(organization, repo, nvr, version)
