#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from flask import Blueprint

API = Blueprint('v1', __name__)

from . import packages, push, about, health  # noqa, register routes
