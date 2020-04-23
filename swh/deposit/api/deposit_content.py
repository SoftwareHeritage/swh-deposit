# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.shortcuts import render
from rest_framework import status

from .common import SWHBaseDeposit
from ..errors import NOT_FOUND, make_error_response
from ..errors import make_error_response_from_dict
from ..models import DEPOSIT_STATUS_DETAIL, Deposit, DepositRequest


class SWHDepositContent(SWHBaseDeposit):
    def get(self, req, collection_name, deposit_id, format=None):
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
