#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

""" Defines custom exceptions and error handling functions """

from flask import jsonify
from werkzeug.exceptions import HTTPException


class OMPSError(Exception):
    """Base OMPSError"""
    code = 500


class OMPSUploadedFileError(OMPSError):
    """Uploaded file doesn't meet expectations"""
    code = 400


class OMPSExpectedFileError(OMPSError):
    """No file was uploaded, but a file was expected"""
    code = 400


class OMPSOrganizationNotFound(OMPSError):
    """Requested organization cannot be accessed"""
    code = 404


class QuayLoginError(OMPSError):
    """Login to quay.io failed"""
    code = 500


class QuayCourierError(OMPSError):
    """Operator-courier library failures"""
    code = 500


def json_error(status, error, message):
    response = jsonify(
        {'status': status,
         'error': error,
         'message': message})
    response.status_code = status
    return response


def init_errors_handling(app):
    """Initialize error handling of the app"""

    @app.errorhandler(OMPSError)
    def omps_errors(e):
        """Handle OMPS application errors"""
        return json_error(e.code, e.__class__.__name__, str(e))

    @app.errorhandler(HTTPException)
    def standard_http_errors(e):
        """Flask error handler for standard HTTP exceptions"""
        return json_error(e.code, e.__class__.__name__, e.description)

    @app.errorhandler(ValueError)
    def validationerror_error(e):
        """Flask error handler for ValueError exceptions"""
        app.logger.exception('Bad Request: %s', e)
        return json_error(400, 'BadRequest', str(e))

    @app.errorhandler(Exception)
    def internal_server_error(e):
        """Flask error handler for RuntimeError exceptions"""
        app.logger.exception('Internal server error: %s', e)
        return json_error(500, 'InternalServerError', str(e))
