# Copyright (C) 2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict, Optional

from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

from django.db.utils import OperationalError


def custom_exception_handler(exc: APIException, context: Dict) -> Optional[Response]:
    """Custom deposit exception handler to ensure consistent xml output

    """
    # drf's default exception handler first, to get the standard error response
    response = exception_handler(exc, context)

    if isinstance(exc, OperationalError):
        status = "Database backend maintenance"
        detail = "Service temporarily unavailable, try again later."
        data = f"""<?xml version="1.0" encoding="utf-8"?>
<api>
  <status>{status}</status>
  <detail>{detail}</detail>
</api>
"""
        return Response(data, status=503, content_type="application/xml")

    return response
