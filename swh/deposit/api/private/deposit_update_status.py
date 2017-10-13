# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from rest_framework.parsers import JSONParser

from ..common import SWHPutDepositAPI, SWHPrivateAPIView
from ...errors import make_error_dict, BAD_REQUEST
from ...models import Deposit, DEPOSIT_STATUS_DETAIL, format_swh_id


class SWHUpdateStatusDeposit(SWHPutDepositAPI, SWHPrivateAPIView):
    """Deposit request class to update the deposit's status.

    HTTP verbs supported: PUT

    """
    parser_classes = (JSONParser, )

    def additional_checks(self, req, collection_name, deposit_id=None):
        """Enrich existing checks to the default ones.

        New checks:
        - Ensure the status is provided
        - Ensure it exists

        """
        data = req.data
        status = data.get('status')
        if not status:
            msg = 'The status key is mandatory with possible values %s' % list(
                DEPOSIT_STATUS_DETAIL.keys())
            return make_error_dict(BAD_REQUEST, msg)

        if status not in DEPOSIT_STATUS_DETAIL:
            msg = 'Possible status in %s' % list(DEPOSIT_STATUS_DETAIL.keys())
            return make_error_dict(BAD_REQUEST, msg)

        if status == 'success':
            swh_id = data.get('revision_id')
            if not swh_id:
                msg = 'Updating status to %s requires a revision_id key' % (
                    status, )
                return make_error_dict(BAD_REQUEST, msg)

        return {}

    def restrict_access(self, req, deposit=None):
        """Remove restriction modification to 'partial' deposit.
           Update is possible regardless of the existing status.

        """
        return None

    def process_put(self, req, headers, collection_name, deposit_id):
        """Update the deposit's status

        Returns:
            204 No content

        """
        deposit = Deposit.objects.get(pk=deposit_id)
        deposit.status = req.data['status']  # checks already done before
        swh_id = req.data.get('revision_id')
        if swh_id:
            deposit.swh_id = format_swh_id(collection_name, swh_id)
        deposit.save()

        return {}
