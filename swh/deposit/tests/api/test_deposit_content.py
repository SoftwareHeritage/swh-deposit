# Copyright (C) 2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.urls import reverse
from rest_framework import status

from swh.deposit.config import CONT_FILE_IRI
from swh.deposit.models import DEPOSIT_STATUS_DETAIL
from swh.deposit.parsers import parse_xml


def test_api_deposit_content_nominal(
    client, complete_deposit, partial_deposit_only_metadata
):
    """Retrieve information on deposit should return 200 response

    """

    for deposit in [complete_deposit, partial_deposit_only_metadata]:
        expected_deposit = {
            "deposit_id": str(deposit.id),
            "deposit_status": deposit.status,
            "deposit_status_detail": DEPOSIT_STATUS_DETAIL[deposit.status],
        }

        url = reverse(CONT_FILE_IRI, args=[deposit.collection.name, deposit.id])
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        actual_deposit = dict(parse_xml(response.content))
        expected_deposit["sword:request"] = actual_deposit["sword:request"]
        assert actual_deposit == expected_deposit


def test_api_deposit_content_unknown(client, complete_deposit, deposit_collection):
    """Retrieve information on unknown deposit or collection should return 404

    """
    unknown_deposit_id = 999
    unknown_collection = "unknown"
    for collection, deposit_id in [
        (deposit_collection.name, unknown_deposit_id),
        (unknown_collection, complete_deposit.id),
        (complete_deposit.collection.name, complete_deposit.id + 10),
    ]:
        url = reverse(CONT_FILE_IRI, args=[collection, deposit_id])
        response = client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
