# Copyright (C) 2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.deposit.exception import custom_exception_handler

from rest_framework.exceptions import APIException
from rest_framework.response import Response

from django.db.utils import OperationalError


def test_custom_exception_handler_operational_error(mocker):
    """Operation error are translated to service unavailable

    """
    fake_exception = OperationalError("Fake internal error", 503)

    response = custom_exception_handler(fake_exception, {})

    assert response is not None
    assert response.status_code == 503

    status = "Database backend maintenance"
    detail = "Service temporarily unavailable, try again later."
    assert (
        response.content.decode("utf-8")
        == f"""<?xml version="1.0" encoding="utf-8"?>
<sword:error xmlns="http://www.w3.org/2005/Atom"
       xmlns:sword="http://purl.org/net/sword/">
    <summary>{status}</summary>
    <sword:verboseDescription>{detail}</sword:verboseDescription>
</sword:error>
"""
    )


def test_custom_exception_handler_default_behavior_maintained(mocker):
    """Other internal errors are transmitted as is

    """
    fake_exception = APIException("Fake internal error", 500)
    fake_response = Response(
        exception=fake_exception, status=fake_exception.status_code
    )
    mock_exception_handler = mocker.patch("swh.deposit.exception.exception_handler")
    mock_exception_handler.return_value = fake_response

    response = custom_exception_handler(fake_exception, {})

    assert response is not None
    assert response == fake_response
