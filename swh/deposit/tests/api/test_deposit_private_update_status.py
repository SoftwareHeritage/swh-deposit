# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json

from django.urls import reverse
from rest_framework import status

from swh.deposit.models import Deposit, DEPOSIT_STATUS_DETAIL
from swh.deposit.config import (
    PRIVATE_PUT_DEPOSIT,
    DEPOSIT_STATUS_VERIFIED,
    DEPOSIT_STATUS_LOAD_SUCCESS,
)


PRIVATE_PUT_DEPOSIT_NC = PRIVATE_PUT_DEPOSIT + "-nc"


def private_check_url_endpoints(collection, deposit):
    """There are 2 endpoints to check (one with collection, one without)"""
    return [
        reverse(PRIVATE_PUT_DEPOSIT, args=[collection.name, deposit.id]),
        reverse(PRIVATE_PUT_DEPOSIT_NC, args=[deposit.id]),
    ]


def test_update_deposit_status(
    authenticated_client, deposit_collection, ready_deposit_verified
):
    """Existing status for update should return a 204 response

    """
    deposit = ready_deposit_verified
    for url in private_check_url_endpoints(deposit_collection, deposit):
        possible_status = set(DEPOSIT_STATUS_DETAIL.keys()) - set(
            [DEPOSIT_STATUS_LOAD_SUCCESS]
        )

        for _status in possible_status:
            response = authenticated_client.put(
                url,
                content_type="application/json",
                data=json.dumps({"status": _status}),
            )

            assert response.status_code == status.HTTP_204_NO_CONTENT

            deposit = Deposit.objects.get(pk=deposit.id)
            assert deposit.status == _status

            deposit.status = DEPOSIT_STATUS_VERIFIED
            deposit.save()  # hack the same deposit


def test_update_deposit_status_with_info(
    authenticated_client, deposit_collection, ready_deposit_verified
):
    """Existing status for update with info should return a 204 response

    """
    deposit = ready_deposit_verified
    for url in private_check_url_endpoints(deposit_collection, deposit):
        expected_status = DEPOSIT_STATUS_LOAD_SUCCESS
        origin_url = "something"
        directory_id = "42a13fc721c8716ff695d0d62fc851d641f3a12b"
        revision_id = "47dc6b4636c7f6cba0df83e3d5490bf4334d987e"
        expected_swh_id = "swh:1:dir:%s" % directory_id
        expected_swh_id_context = "swh:1:dir:%s;origin=%s" % (directory_id, origin_url)
        expected_swh_anchor_id = "swh:1:rev:%s" % revision_id
        expected_swh_anchor_id_context = "swh:1:rev:%s;origin=%s" % (
            revision_id,
            origin_url,
        )

        response = authenticated_client.put(
            url,
            content_type="application/json",
            data=json.dumps(
                {
                    "status": expected_status,
                    "revision_id": revision_id,
                    "directory_id": directory_id,
                    "origin_url": origin_url,
                }
            ),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        deposit = Deposit.objects.get(pk=deposit.id)
        assert deposit.status == expected_status
        assert deposit.swh_id == expected_swh_id
        assert deposit.swh_id_context == expected_swh_id_context
        assert deposit.swh_anchor_id == expected_swh_anchor_id
        assert deposit.swh_anchor_id_context == expected_swh_anchor_id_context

        deposit.swh_id = None
        deposit.swh_id_context = None
        deposit.swh_anchor_id = None
        deposit.swh_anchor_id_context = None
        deposit.status = DEPOSIT_STATUS_VERIFIED
        deposit.save()


def test_update_deposit_status_will_fail_with_unknown_status(
    authenticated_client, deposit_collection, ready_deposit_verified
):
    """Unknown status for update should return a 400 response

    """
    deposit = ready_deposit_verified
    for url in private_check_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.put(
            url, content_type="application/json", data=json.dumps({"status": "unknown"})
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_update_deposit_status_will_fail_with_no_status_key(
    authenticated_client, deposit_collection, ready_deposit_verified
):
    """No status provided for update should return a 400 response

    """
    deposit = ready_deposit_verified
    for url in private_check_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.put(
            url,
            content_type="application/json",
            data=json.dumps({"something": "something"}),
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_update_deposit_status_success_without_swh_id_fail(
    authenticated_client, deposit_collection, ready_deposit_verified
):
    """Providing successful status without swh_id should return a 400

    """
    deposit = ready_deposit_verified
    for url in private_check_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.put(
            url,
            content_type="application/json",
            data=json.dumps({"status": DEPOSIT_STATUS_LOAD_SUCCESS}),
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
