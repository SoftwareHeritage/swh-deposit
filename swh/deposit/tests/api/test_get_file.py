# Copyright (C) 2020-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Tests 'GET File-IRI'."""

import datetime

from django.urls import reverse_lazy as reverse
from rest_framework import status

from swh.deposit.config import CONT_FILE_IRI
from swh.deposit.models import DEPOSIT_STATUS_DETAIL
from swh.deposit.parsers import parse_xml
from swh.deposit.utils import NAMESPACES


def test_api_deposit_content_nominal(
    authenticated_client, complete_deposit, partial_deposit_only_metadata
):
    """Retrieve information on deposit should return 200 response"""
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    for deposit in [complete_deposit, partial_deposit_only_metadata]:
        url = reverse(CONT_FILE_IRI, args=[deposit.collection.name, deposit.id])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        actual_deposit = parse_xml(response.content)
        assert actual_deposit.findtext("swh:deposit_id", namespaces=NAMESPACES) == str(
            deposit.id
        )
        assert (
            actual_deposit.findtext("swh:deposit_status", namespaces=NAMESPACES)
            == deposit.status
        )
        assert (
            actual_deposit.findtext("swh:deposit_status_detail", namespaces=NAMESPACES)
            == DEPOSIT_STATUS_DETAIL[deposit.status]
        )
        assert (
            now - datetime.timedelta(hours=1)
            <= datetime.datetime.fromisoformat(
                actual_deposit.findtext("swh:deposit_date", namespaces=NAMESPACES)
            )
            <= now
        )


def test_api_deposit_content_unknown(
    authenticated_client, complete_deposit, deposit_collection
):
    """Retrieve information on unknown deposit or collection should return 404"""
    unknown_deposit_id = 999
    unknown_collection = "unknown"
    for collection, deposit_id in [
        (deposit_collection.name, unknown_deposit_id),
        (unknown_collection, complete_deposit.id),
        (complete_deposit.collection.name, complete_deposit.id + 10),
    ]:
        url = reverse(CONT_FILE_IRI, args=[collection, deposit_id])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
