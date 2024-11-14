# Copyright (C) 2024 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from swh.deposit.config import (
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_LOAD_SUCCESS,
    PRIVATE_GET_RELEASES,
)
from swh.deposit.models import Deposit, DepositClient


def test_releases(anonymous_client, deposit_collection):
    client = DepositClient.objects.create(
        username="releases", collections=[deposit_collection.id]
    )

    deposit_v0 = Deposit.objects.create(
        origin_url="http://releases.localhost",
        complete_date=timezone.now(),
        status=DEPOSIT_STATUS_DEPOSITED,
        client=client,
        collection_id=deposit_collection.id,
        software_version="v0",
    )
    Deposit.objects.create(
        origin_url="http://releases.localhost",
        complete_date=timezone.now(),
        status=DEPOSIT_STATUS_LOAD_SUCCESS,
        client=client,
        collection_id=deposit_collection.id,
        software_version="v1",
    )
    deposit_v1_overwrite = Deposit.objects.create(
        origin_url="http://releases.localhost",
        complete_date=timezone.now(),
        status=DEPOSIT_STATUS_LOAD_SUCCESS,
        client=client,
        collection_id=deposit_collection.id,
        software_version="v1",
        release_notes="overwrite deposit_v1",
    )
    deposit_v2 = Deposit.objects.create(
        origin_url="http://releases.localhost",
        complete_date=timezone.now(),
        status=DEPOSIT_STATUS_LOAD_SUCCESS,
        client=client,
        collection_id=deposit_collection.id,
        software_version="v2",
    )
    Deposit.objects.create(
        origin_url="http://releases.localhost",
        complete_date=timezone.now(),
        status=DEPOSIT_STATUS_LOAD_SUCCESS,
        client=client,
        collection_id=deposit_collection.id,
        software_version="",  # missing version number
    )
    url = reverse(PRIVATE_GET_RELEASES, args=[deposit_v2.id])

    response = anonymous_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response["content-type"] == "application/json"
    releases_list = response.json()
    assert len(releases_list) == 3
    assert releases_list[0]["id"] == deposit_v0.id
    assert releases_list[1]["id"] == deposit_v1_overwrite.id
    assert releases_list[2]["id"] == deposit_v2.id
