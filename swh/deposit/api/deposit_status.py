# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status

from ..errors import NOT_FOUND, make_error_response, make_error_response_from_dict
from ..models import DEPOSIT_STATUS_DETAIL, Deposit
from .common import APIBase
from .converters import convert_status_detail


class APIStatus(APIBase):
    """Deposit status.

    What's known as 'State IRI' in the sword specification.

    HTTP verbs supported: GET

    """

    def get(self, req, collection_name: str, deposit_id: int) -> HttpResponse:
        checks = self.checks(req, collection_name, deposit_id)
        if "error" in checks:
            return make_error_response_from_dict(req, checks["error"])

        try:
            deposit = Deposit.objects.get(pk=deposit_id)
            if deposit.collection.name != collection_name:
                raise Deposit.DoesNotExist
        except Deposit.DoesNotExist:
            return make_error_response(
                req,
                NOT_FOUND,
                "deposit %s does not belong to collection %s"
                % (deposit_id, collection_name),
            )

        status_detail = convert_status_detail(deposit.status_detail)
        if not status_detail:
            status_detail = DEPOSIT_STATUS_DETAIL[deposit.status]

        context = {
            "deposit_id": deposit.id,
            "status_detail": status_detail,
        }
        keys = (
            "status",
            "swhid",
            "swhid_context",
            "external_id",
        )
        for k in keys:
            context[k] = getattr(deposit, k, None)

        return render(
            req,
            "deposit/status.xml",
            context=context,
            content_type="application/xml",
            status=status.HTTP_200_OK,
        )
