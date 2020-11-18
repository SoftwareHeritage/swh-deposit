# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of providing the standard sword errors

"""

from typing import Any, Dict

from django.shortcuts import render
from rest_framework import status

FORBIDDEN = "forbidden"
UNAUTHORIZED = "unauthorized"
NOT_FOUND = "unknown"
BAD_REQUEST = "bad-request"
ERROR_CONTENT = "error-content"
CHECKSUM_MISMATCH = "checksum-mismatch"
MEDIATION_NOT_ALLOWED = "mediation-not-allowed"
METHOD_NOT_ALLOWED = "method-not-allowed"
MAX_UPLOAD_SIZE_EXCEEDED = "max_upload_size_exceeded"
PARSING_ERROR = "parsing-error"


class ParserError(ValueError):
    """Specific parsing error detected when parsing the xml metadata input

    """

    pass


ERRORS = {
    FORBIDDEN: {
        "status": status.HTTP_403_FORBIDDEN,
        "iri": "http://purl.org/net/sword/error/ErrorForbidden",
        "tag": "sword:ErrorForbidden",
    },
    UNAUTHORIZED: {
        "status": status.HTTP_401_UNAUTHORIZED,
        "iri": "http://purl.org/net/sword/error/ErrorUnauthorized",
        "tag": "sword:ErrorUnauthorized",
    },
    NOT_FOUND: {
        "status": status.HTTP_404_NOT_FOUND,
        "iri": "http://purl.org/net/sword/error/ErrorNotFound",
        "tag": "sword:ErrorNotFound",
    },
    ERROR_CONTENT: {
        "status": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        "iri": "http://purl.org/net/sword/error/ErrorContent",
        "tag": "sword:ErrorContent",
    },
    CHECKSUM_MISMATCH: {
        "status": status.HTTP_412_PRECONDITION_FAILED,
        "iri": "http://purl.org/net/sword/error/ErrorChecksumMismatch",
        "tag": "sword:ErrorChecksumMismatch",
    },
    BAD_REQUEST: {
        "status": status.HTTP_400_BAD_REQUEST,
        "iri": "http://purl.org/net/sword/error/ErrorBadRequest",
        "tag": "sword:ErrorBadRequest",
    },
    PARSING_ERROR: {
        "status": status.HTTP_400_BAD_REQUEST,
        "iri": "http://purl.org/net/sword/error/ErrorBadRequest",
        "tag": "sword:ErrorBadRequest",
    },
    MEDIATION_NOT_ALLOWED: {
        "status": status.HTTP_412_PRECONDITION_FAILED,
        "iri": "http://purl.org/net/sword/error/MediationNotAllowed",
        "tag": "sword:MediationNotAllowed",
    },
    METHOD_NOT_ALLOWED: {
        "status": status.HTTP_405_METHOD_NOT_ALLOWED,
        "iri": "http://purl.org/net/sword/error/MethodNotAllowed",
        "tag": "sword:MethodNotAllowed",
    },
    MAX_UPLOAD_SIZE_EXCEEDED: {
        "status": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        "iri": "http://purl.org/net/sword/error/MaxUploadSizeExceeded",
        "tag": "sword:MaxUploadSizeExceeded",
    },
}


def make_error_dict(key, summary=None, verbose_description=None):
    """Utility function to factorize error message dictionary.

    Args:
        key (str): Error status key referenced in swh.deposit.errors module
        summary (str/None): Error message clarifying the status
        verbose_description (str/None): A more verbose
          description or work around a potential problem.

    Returns:
        Dictionary with key 'error' detailing the 'status' and
        associated 'message'

    """
    return {
        "error": {
            "key": key,
            "summary": summary,
            "verboseDescription": verbose_description,
        },
    }


def make_error_response_from_dict(req, error):
    """Utility function to return an http response with error detail.

    Args:
        req (Request): original request
        error (dict): Error described as dict, typically generated
        from the make_error_dict function.

    Returns:
        HttpResponse with detailed error.

    """
    error_information = ERRORS[error["key"]]
    context = error
    context.update(error_information)
    return render(
        req,
        "deposit/error.xml",
        context=error,
        content_type="application/xml",
        status=error_information["status"],
    )


def make_error_response(req, key, summary=None, verbose_description=None):
    """Utility function to create an http response with detailed error.

    Args:
        req (Request): original request
        key (str): Error status key referenced in swh.deposit.errors module
        summary (str): Error message clarifying the status
        verbose_description (str / None): A more verbose
          description or work around a potential problem.

    Returns:
        Dictionary with key 'error' detailing the 'status' and
        associated 'message'

    """
    error = make_error_dict(key, summary, verbose_description)
    return make_error_response_from_dict(req, error["error"])


def make_missing_slug_error() -> Dict[str, Any]:
    """Returns a missing slug header error dict

    """
    return make_error_dict(
        BAD_REQUEST,
        "Missing SLUG header",
        verbose_description=(
            "Provide in the SLUG header one identifier, for example the "
            "url pointing to the resource you are depositing."
        ),
    )


class BadRequestError(ValueError):
    """Represents a bad input from the deposit client

    """

    def __init__(self, summary, verbose_description):
        self.key = BAD_REQUEST
        self.summary = summary
        self.verbose_description = verbose_description

    def to_dict(self):
        return make_error_dict(self.key, self.summary, self.verbose_description)
