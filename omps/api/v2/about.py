#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from . import API
from omps.api.v1.about import about as about_v1


@API.route("/about", methods=('GET',))
def about():
    # V2 has the same implementation as V1
    return about_v1()
