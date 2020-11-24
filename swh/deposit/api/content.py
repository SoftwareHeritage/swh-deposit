# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status

from ..models import DEPOSIT_STATUS_DETAIL, DepositRequest
from .common import APIBase, get_deposit_by_id


class ContentAPI(APIBase):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'Cont-IRI' and 'File-IRI' in the sword specification.

    HTTP verbs supported: GET

    """

    def get(self, req, collection_name: str, deposit_id: int) -> HttpResponse:
        deposit = get_deposit_by_id(deposit_id, collection_name)

        self.checks(req, collection_name, deposit)

        requests = DepositRequest.objects.filter(deposit=deposit)
        context = {
            "deposit_id": deposit.id,
            "status": deposit.status,
            "status_detail": DEPOSIT_STATUS_DETAIL[deposit.status],
            "requests": requests,
        }

        return render(
            req,
            "deposit/content.xml",
            context=context,
            content_type="application/xml",
            status=status.HTTP_200_OK,
        )
