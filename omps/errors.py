#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

""" Defines custom exceptions and error handling functions """

from flask import jsonify
from werkzeug.exceptions import HTTPException
from operatorcourier.errors import (
    OpCourierBadYaml,
    OpCourierBadBundle,
    OpCourierQuayErrorResponse
)


class OMPSError(Exception):
    """Base OMPSError"""
    code = 500

    def to_dict(self):
        """Turn the exception into a dict for use as an error response"""
        return {
            'status': self.code,
            'error': self.__class__.__name__,
            'message': str(self)
        }


class OMPSUploadedFileError(OMPSError):
    """Uploaded file doesn't meet expectations"""
    code = 400


class OMPSExpectedFileError(OMPSError):
    """No file was uploaded, but a file was expected"""
    code = 400


class QuayCourierError(OMPSError):
    """Operator-courier library failures"""
    code = 500

    def __init__(self, msg, quay_response=None):
        """
        :param msg: the message this exception should have
        :param quay_response: Quay error response json, if available
        """
        super().__init__(msg)
        self.quay_response = quay_response or {}

    def to_dict(self):
        data = super().to_dict()
        data['quay_response'] = self.quay_response
        return data


class PackageValidationError(OMPSError):
    """Package failed validation"""
    code = 400

    def __init__(self, msg, validation_info=None):
        """
        :param msg: the message this exception should have
        :param validation_info: errors and warnings found during validation,
                                if available
        """
        super().__init__(msg)
        self.validation_info = validation_info or {}

    def to_dict(self):
        data = super().to_dict()
        data['validation_info'] = self.validation_info
        return data


class QuayAuthorizationError(OMPSError):
    """Unauthorized access to Quay"""
    code = 403

    def __init__(self, msg, quay_response):
        """
        :param msg: the message this exception should have
        :param quay_response: Quay error response json
        """
        super().__init__(msg)
        self.quay_response = quay_response

    def to_dict(self):
        data = super().to_dict()
        data['quay_response'] = self.quay_response
        return data


class QuayPackageError(OMPSError):
    """Error during getting package information from quay"""
    code = 500


class QuayPackageNotFound(OMPSError):
    """Requested package doesn't exist"""
    code = 404


class OMPSInvalidVersionFormat(OMPSError):
    """Quay package version does not follow the required format.
    The format should be 'x.y.z', where x, y, z are positive integers or 0"""
    code = 400


class OMPSAuthorizationHeaderRequired(OMPSError):
    """Request doesn't contain 'Authorization' header"""
    code = 403


class KojiNVRBuildNotFound(OMPSError):
    """Requested build not found in koji"""
    code = 404


class KojiNotAnOperatorImage(OMPSError):
    """Requested build is not an operator image"""
    code = 400


class KojiManifestsArchiveNotFound(OMPSError):
    """Manifest archive not found in koji"""
    code = 500


class KojiError(OMPSError):
    """Failed to retrieve data from koji"""
    code = 500


class GreenwaveError(OMPSError):
    """Failed to retrieve data from Greenwave"""
    code = 500

    def __init__(self, msg, greenwave_response):
        """
        :param msg: the message this exception should have
        :param greenwave_response: response from greenwave
        """
        super().__init__(msg)
        self.greenwave_response = greenwave_response

    def to_dict(self):
        data = super().to_dict()
        data['greenwave_response'] = self.greenwave_response
        return data


class GreenwaveUnsatisfiedError(OMPSError):
    """Didn't meet policy expectations"""
    code = 400

    def __init__(self, msg, greenwave_response):
        """
        :param msg: the message this exception should have
        :param greenwave_response: response from greenwave
        """
        super().__init__(msg)
        self.greenwave_response = greenwave_response

    def to_dict(self):
        data = super().to_dict()
        data['greenwave_response'] = self.greenwave_response
        return data


def raise_for_courier_exception(e, new_msg=None):
    """React to operator-courier errors by raising the proper OMPS error

    :param e: the operator-courier error
    :param new_msg: message for the OMPS error (if None, the original error
                    message will be used)
    """
    msg = new_msg if new_msg is not None else str(e)

    if isinstance(e, OpCourierBadBundle):
        raise PackageValidationError(msg, e.validation_info)
    elif isinstance(e, OpCourierBadYaml):
        raise PackageValidationError(msg)
    elif isinstance(e, OpCourierQuayErrorResponse):
        if e.code == 403:
            raise QuayAuthorizationError(msg, e.error_response)
        else:
            raise QuayCourierError(msg, e.error_response)
    else:
        raise QuayCourierError(msg)


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
        err_dict = e.to_dict()
        app.logger.error(
            'OMPS error: %s: %r',
            err_dict['error'], err_dict
        )
        response = jsonify(err_dict)
        response.status_code = e.code
        return response

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
