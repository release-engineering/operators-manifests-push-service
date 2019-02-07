#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import logging

from flask import Flask

from .errors import init_errors_handling
from .push import BLUEPRINT as PUSH_BP
from .settings import init_config


logger = logging.getLogger(__name__)


def create_app():
    """Create flask app"""
    app = Flask('omps')

    _load_config(app)
    init_errors_handling(app)
    _register_blueprints(app)

    return app


def _load_config(app):
    init_config(app)


def _register_blueprints(app):
    app.register_blueprint(PUSH_BP, url_prefix='/push')


app = create_app()
