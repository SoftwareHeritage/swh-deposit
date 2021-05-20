# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status

from ..models import DEPOSIT_STATUS_DETAIL
from .common import APIBase, get_deposit_by_id
from .converters import convert_status_detail


class StateAPI(APIBase):
    """Deposit status.

    What's known as 'State-IRI' in the sword specification.

    HTTP verbs supported: GET

    """

    def get(  # type: ignore
        self, req, collection_name: str, deposit_id: int
    ) -> HttpResponse:
        deposit = get_deposit_by_id(deposit_id, collection_name)

        self.checks(req, collection_name, deposit)

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
            "origin_url",
        )
        for k in keys:
            context[k] = getattr(deposit, k, None)

        return render(
            req,
            "deposit/state.xml",
            context=context,
            content_type="application/xml",
            status=status.HTTP_200_OK,
        )
