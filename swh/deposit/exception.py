# Copyright (C) 2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict, Optional

from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler
from django.http import HttpResponse

from django.db.utils import OperationalError


def custom_exception_handler(
    exc: APIException, context: Dict
) -> Optional[HttpResponse]:
    """Custom deposit exception handler to ensure consistent xml output

    """
    # drf's default exception handler first, to get the standard error response
    response = exception_handler(exc, context)

    if isinstance(exc, OperationalError):
        status = "Database backend maintenance"
        detail = "Service temporarily unavailable, try again later."
        data = f"""<?xml version="1.0" encoding="utf-8"?>
<sword:error xmlns="http://www.w3.org/2005/Atom"
       xmlns:sword="http://purl.org/net/sword/">
    <summary>{status}</summary>
    <sword:verboseDescription>{detail}</sword:verboseDescription>
</sword:error>
""".encode(
            "utf-8"
        )
        return HttpResponse(data, status=503, content_type="application/xml")

    return response
