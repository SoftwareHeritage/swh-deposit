# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import copy
import json

from django.urls import reverse
from rest_framework import status

from swh.model.identifiers import DIRECTORY, persistent_identifier, REVISION, SNAPSHOT

from swh.deposit.api.private.deposit_update_status import MANDATORY_KEYS

from swh.deposit.models import Deposit
from swh.deposit.config import (
    PRIVATE_PUT_DEPOSIT,
    DEPOSIT_STATUS_LOAD_SUCCESS,
    DEPOSIT_STATUS_LOAD_FAILURE,
)


PRIVATE_PUT_DEPOSIT_NC = PRIVATE_PUT_DEPOSIT + "-nc"


def private_check_url_endpoints(collection, deposit):
    """There are 2 endpoints to check (one with collection, one without)"""
    return [
        reverse(PRIVATE_PUT_DEPOSIT, args=[collection.name, deposit.id]),
        reverse(PRIVATE_PUT_DEPOSIT_NC, args=[deposit.id]),
    ]


def test_update_deposit_status_success_with_info(
    authenticated_client, deposit_collection, ready_deposit_verified
):
    """Update deposit with load success should require all information to succeed

    """
    deposit = ready_deposit_verified
    expected_status = DEPOSIT_STATUS_LOAD_SUCCESS
    origin_url = "something"
    directory_id = "42a13fc721c8716ff695d0d62fc851d641f3a12b"
    revision_id = "47dc6b4636c7f6cba0df83e3d5490bf4334d987e"
    snapshot_id = "68c0d26104d47e278dd6be07ed61fafb561d0d20"

    full_body_info = {
        "status": DEPOSIT_STATUS_LOAD_SUCCESS,
        "revision_id": revision_id,
        "directory_id": directory_id,
        "snapshot_id": snapshot_id,
        "origin_url": origin_url,
    }
    for url in private_check_url_endpoints(deposit_collection, deposit):
        dir_id = persistent_identifier(DIRECTORY, directory_id)
        rev_id = persistent_identifier(REVISION, revision_id)
        snp_id = persistent_identifier(SNAPSHOT, snapshot_id)

        expected_swh_id = "swh:1:dir:%s" % directory_id
        expected_swh_id_context = (
            f"{dir_id};origin={origin_url};" + f"visit={snp_id};anchor={rev_id};path=/"
        )

        response = authenticated_client.put(
            url, content_type="application/json", data=json.dumps(full_body_info),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        deposit = Deposit.objects.get(pk=deposit.id)
        assert deposit.status == expected_status
        assert deposit.swh_id == expected_swh_id
        assert deposit.swh_id_context == expected_swh_id_context

        # Reset deposit
        deposit = ready_deposit_verified
        deposit.save()


def test_update_deposit_status_rejected_with_info(
    authenticated_client, deposit_collection, ready_deposit_verified
):
    """Update deposit with rejected status needs few information to succeed

    """
    deposit = ready_deposit_verified

    for url in private_check_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.put(
            url,
            content_type="application/json",
            data=json.dumps({"status": DEPOSIT_STATUS_LOAD_FAILURE}),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        deposit = Deposit.objects.get(pk=deposit.id)
        assert deposit.status == DEPOSIT_STATUS_LOAD_FAILURE

        assert deposit.swh_id is None
        assert deposit.swh_id_context is None

        # Reset status
        deposit = ready_deposit_verified
        deposit.save()


def test_update_deposit_status_success_with_incomplete_data(
    authenticated_client, deposit_collection, ready_deposit_verified
):
    """Update deposit status with status success and incomplete information should fail

    """
    deposit = ready_deposit_verified

    origin_url = "something"
    directory_id = "42a13fc721c8716ff695d0d62fc851d641f3a12b"
    revision_id = "47dc6b4636c7f6cba0df83e3d5490bf4334d987e"
    snapshot_id = "68c0d26104d47e278dd6be07ed61fafb561d0d20"

    new_status = DEPOSIT_STATUS_LOAD_SUCCESS
    full_body_info = {
        "status": new_status,
        "revision_id": revision_id,
        "directory_id": directory_id,
        "snapshot_id": snapshot_id,
        "origin_url": origin_url,
    }

    for url in private_check_url_endpoints(deposit_collection, deposit):
        for key in MANDATORY_KEYS:
            # Crafting body with missing information so that it raises
            body = copy.deepcopy(full_body_info)
            body.pop(key)  # make the body incomplete

            response = authenticated_client.put(
                url, content_type="application/json", data=json.dumps(body),
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                f"deposit status to {new_status} requires information {key}"
                in response.content.decode("utf-8")
            )


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
