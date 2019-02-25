#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import logging

from flask import Flask

from .errors import init_errors_handling
from .logger import init_logging
from .packages import BLUEPRINT as PACKAGES_BP
from .push import BLUEPRINT as PUSH_BP
from .settings import init_config
from .quay import QUAY_ORG_MANAGER


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
    QUAY_ORG_MANAGER.init_from_config(conf)


def _init_errors_handling(app):
    logger.debug('Initializing errors handling')
    init_errors_handling(app)


def _register_blueprints(app):
    logger.debug('Registering blueprints')
    app.register_blueprint(PUSH_BP, url_prefix='/push')
    app.register_blueprint(PACKAGES_BP, url_prefix='/packages')


app = create_app()
