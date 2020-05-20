# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from rest_framework.parsers import JSONParser

from swh.model.identifiers import DIRECTORY, persistent_identifier, REVISION, SNAPSHOT

from . import SWHPrivateAPIView
from ..common import SWHPutDepositAPI
from ...errors import make_error_dict, BAD_REQUEST
from ...models import Deposit, DEPOSIT_STATUS_DETAIL
from ...models import DEPOSIT_STATUS_LOAD_SUCCESS


MANDATORY_KEYS = ["origin_url", "revision_id", "directory_id", "snapshot_id"]


class SWHUpdateStatusDeposit(SWHPrivateAPIView, SWHPutDepositAPI):
    """Deposit request class to update the deposit's status.

    HTTP verbs supported: PUT

    """

    parser_classes = (JSONParser,)

    def additional_checks(self, request, headers, collection_name, deposit_id=None):
        """Enrich existing checks to the default ones.

        New checks:
        - Ensure the status is provided
        - Ensure it exists
        - no missing information on load success update

        """
        data = request.data
        status = data.get("status")
        if not status:
            msg = "The status key is mandatory with possible values %s" % list(
                DEPOSIT_STATUS_DETAIL.keys()
            )
            return make_error_dict(BAD_REQUEST, msg)

        if status not in DEPOSIT_STATUS_DETAIL:
            msg = "Possible status in %s" % list(DEPOSIT_STATUS_DETAIL.keys())
            return make_error_dict(BAD_REQUEST, msg)

        if status == DEPOSIT_STATUS_LOAD_SUCCESS:
            missing_keys = []
            for key in MANDATORY_KEYS:
                value = data.get(key)
                if value is None:
                    missing_keys.append(key)

            if missing_keys:
                msg = (
                    f"Updating deposit status to {status}"
                    f" requires information {','.join(missing_keys)}"
                )
                return make_error_dict(BAD_REQUEST, msg)

        return {}

    def process_put(self, request, headers, collection_name, deposit_id):
        """Update the deposit with status and SWHIDs

        Returns:
            204 No content
            400 Bad request if checks fail

        """
        data = request.data

        deposit = Deposit.objects.get(pk=deposit_id)

        status = data["status"]
        deposit.status = status
        if status == DEPOSIT_STATUS_LOAD_SUCCESS:
            origin_url = data["origin_url"]
            directory_id = data["directory_id"]
            revision_id = data["revision_id"]
            dir_id = persistent_identifier(DIRECTORY, directory_id)
            snp_id = persistent_identifier(SNAPSHOT, data["snapshot_id"])
            rev_id = persistent_identifier(REVISION, revision_id)

            deposit.swh_id = dir_id
            # new id with contextual information
            deposit.swh_id_context = persistent_identifier(
                DIRECTORY,
                directory_id,
                metadata={
                    "origin": origin_url,
                    "visit": snp_id,
                    "anchor": rev_id,
                    "path": "/",
                },
            )
        else:  # rejected
            deposit.status = status

        deposit.save()

        return {}
