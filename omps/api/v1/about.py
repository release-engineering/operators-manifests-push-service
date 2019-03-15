#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from flask import jsonify

from omps import __version__ as version
from . import API


@API.route("/about", methods=('GET',))
def about():
    return jsonify(version=version)
