#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from . import API
from omps.api.v1.health import ping as ping_v1


@API.route("/health/ping", methods=('GET', ))
def ping():
    # V2 has the same implementation as V1
    return ping_v1()
