#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from . import API
from omps.api.v1.packages import (
    delete_package_release as delete_package_release_v1
)


@API.route("/<organization>/<repo>", defaults={'version': None},
           methods=('DELETE',))
@API.route("/<organization>/<repo>/<version>", methods=('DELETE',))
def delete_package_release(organization, repo, version=None):
    # V2 has the same implementation as V1
    return delete_package_release_v1(organization, repo, version)
