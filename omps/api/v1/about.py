#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from flask import jsonify

import pkg_resources
from omps import __version__ as version
from . import API


@API.route("/about", methods=('GET',))
def about():
    courier_version = pkg_resources.get_distribution('operator-courier').version
    return jsonify(version=version, operatorcourier=courier_version)
