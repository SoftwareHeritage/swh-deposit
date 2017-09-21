# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.shortcuts import render
from rest_framework import status

from ..config import SWHDefaultConfig
from ..errors import NOT_FOUND, make_error, make_error_response
from ..models import DEPOSIT_STATUS_DETAIL, Deposit

from .common import SWHAPIView


class SWHDepositStatus(SWHDefaultConfig, SWHAPIView):
    """Deposit status.

    What's known as 'State IRI' in the sword specification.

    HTTP verbs supported: GET

    """
    def get(self, req, client_name, deposit_id, format=None):
        try:
            deposit = Deposit.objects.get(pk=deposit_id)
            # FIXME: Find why Deposit.objects.get(pk=deposit_id,
            # client=User(username=client_name)) does not work
            if deposit.client.username != client_name:
                raise Deposit.DoesNotExist
        except Deposit.DoesNotExist:
            err = make_error(
                NOT_FOUND,
                'deposit %s for client %s does not exist' % (
                    deposit_id, client_name))
            return make_error_response(req, err['error'])

        context = {
            'deposit_id': deposit.id,
            'status': deposit.status,
            'status_detail': DEPOSIT_STATUS_DETAIL[deposit.status],
        }

        return render(req, 'deposit/status.xml',
                      context=context,
                      content_type='application/xml',
                      status=status.HTTP_200_OK)
