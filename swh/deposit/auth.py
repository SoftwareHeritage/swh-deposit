# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from rest_framework import status

from .errors import UNAUTHORIZED, make_error_response


def convert_response(request, content):
    """Convert response from drf's basic authentication mechanism to a
       swh-deposit one.

        Args:
           request (Request): Use to build the response
           content (bytes): The drf's answer

        Returns:

            Response with the same status error as before, only the
            body is now an swh-deposit compliant one.

    """
    from json import loads

    content = loads(content.decode("utf-8"))
    detail = content.get("detail")
    if detail:
        verbose_description = "API is protected by basic authentication"
    else:
        detail = "API is protected by basic authentication"
        verbose_description = None

    response = make_error_response(
        request, UNAUTHORIZED, summary=detail, verbose_description=verbose_description
    )
    response["WWW-Authenticate"] = 'Basic realm=""'

    return response


class WrapBasicAuthenticationResponseMiddleware:
    """Middleware to capture potential authentication error and convert
       them to standard deposit response.

       This is to be installed in django's settings.py module.

    """

    def __init__(self, get_response):
        super().__init__()
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code is status.HTTP_401_UNAUTHORIZED:
            content_type = response._headers.get("content-type")
            if content_type == ("Content-Type", "application/json"):
                return convert_response(request, response.content)

        return response
