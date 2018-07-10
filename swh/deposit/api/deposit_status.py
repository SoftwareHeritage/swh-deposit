# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.shortcuts import render
from rest_framework import status

from .common import SWHBaseDeposit
from ..errors import NOT_FOUND, make_error_response
from ..errors import make_error_response_from_dict
from ..models import DEPOSIT_STATUS_DETAIL, Deposit


def convert_status_detail(status_detail):
    """Given a status_detail dict, transforms it into a human readable
       string.

       Dict has the following form (all first level keys are optional):
       {
           'url': {
               'summary': <summary-string>,
               'fields': <impacted-fields-list>
           },
           'metadata': [{
               'summary': <summary-string>,
               'fields': <impacted-fields-list>,
           }],
           'archive': {
               'summary': <summary-string>,
               'fields': [],
           }


        }

    Args:
        status_detail (dict):

    Returns:
        Status detail as inlined string.

    """
    if not status_detail:
        return None

    msg = []
    if 'metadata' in status_detail:
        for data in status_detail['metadata']:
            fields = ', '.join(data['fields'])
            msg.append('- %s (%s)\n' % (data['summary'], fields))

    for key in ['url', 'archive']:
        if key in status_detail:
            _detail = status_detail[key]
            fields = _detail.get('fields')
            suffix_msg = ''
            if fields:
                suffix_msg = ' (%s)' % ', '.join(fields)
            msg.append('- %s%s\n' % (_detail['summary'], suffix_msg))

    if not msg:
        return None
    return ''.join(msg)


class SWHDepositStatus(SWHBaseDeposit):
    """Deposit status.

    What's known as 'State IRI' in the sword specification.

    HTTP verbs supported: GET

    """
    def get(self, req, collection_name, deposit_id, format=None):
        checks = self.checks(req, collection_name, deposit_id)
        if 'error' in checks:
            return make_error_response_from_dict(req, checks['error'])

        try:
            deposit = Deposit.objects.get(pk=deposit_id)
            if deposit.collection.name != collection_name:
                raise Deposit.DoesNotExist
        except Deposit.DoesNotExist:
            return make_error_response(
                req, NOT_FOUND,
                'deposit %s does not belong to collection %s' % (
                    deposit_id, collection_name))

        status_detail = convert_status_detail(deposit.status_detail)
        if not status_detail:
            status_detail = DEPOSIT_STATUS_DETAIL[deposit.status]

        context = {
            'deposit_id': deposit.id,
            'status': deposit.status,
            'status_detail': status_detail,
            'swh_id': None,
        }

        if deposit.swh_id:
            context['swh_id'] = deposit.swh_id

        return render(req, 'deposit/status.xml',
                      context=context,
                      content_type='application/xml',
                      status=status.HTTP_200_OK)
