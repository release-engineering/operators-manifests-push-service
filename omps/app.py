#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import logging

from flask import Flask

from .api.v1 import API as API_V1
from .errors import init_errors_handling
from .logger import init_logging
from .settings import init_config


logger = logging.getLogger(__name__)


def create_app():
    """Create flask app"""
    app = Flask('omps')

    _load_config(app)
    _init_errors_handling(app)
    _register_blueprints(app)

    return app


def _load_config(app):
    conf = init_config(app)
    init_logging(conf)
    logger.debug('Config loaded. Logging initialized')


def _init_errors_handling(app):
    logger.debug('Initializing errors handling')
    init_errors_handling(app)


def _register_blueprints(app):
    logger.debug('Registering blueprints')
    app.register_blueprint(API_V1, url_prefix='/v1')


app = create_app()
