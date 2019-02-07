#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

""" Defines custom exceptions and error handling functions """

from flask import jsonify
from werkzeug.exceptions import HTTPException


def json_error(status, error, message):
    response = jsonify(
        {'status': status,
         'error': error,
         'message': message})
    response.status_code = status
    return response


def init_errors_handling(app):
    """Initialize error handling of the app"""

    @app.errorhandler(HTTPException)
    def standard_http_errors(e):
        """Flask error handler for standard HTTP exceptions"""
        return json_error(e.code, e.__class__.__name__, e.description)

    @app.errorhandler(ValueError)
    def validationerror_error(e):
        """Flask error handler for ValueError exceptions"""
        app.logger.exception('Bad Request: %s', e)
        return json_error(400, 'Bad Request', str(e))

    @app.errorhandler(Exception)
    def internal_server_error(e):
        """Flask error handler for RuntimeError exceptions"""
        app.logger.exception('Internal server error: %s', e)
        return json_error(500, 'Internal Server Error', str(e))
