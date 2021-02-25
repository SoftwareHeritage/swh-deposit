# Copyright (C) 2020-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import copy
import datetime
from io import BytesIO

from django.urls import reverse_lazy as reverse
import pytest
from rest_framework import status

from swh.deposit.config import (
    COL_IRI,
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_PARTIAL,
    SE_IRI,
)
from swh.deposit.parsers import parse_xml


@pytest.fixture()
def deposit_config(deposit_config):
    """Overrides the `deposit_config` fixture define in swh/deposit/tests/conftest.py
    to re-enable the checks."""
    config_d = copy.deepcopy(deposit_config)
    config_d["checks"] = True
    return config_d


def now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


def assert_task_for_deposit(
    swh_scheduler, deposit_id, timestamp_before_call, timestamp_after_call
):
    tasks = swh_scheduler.grab_ready_tasks("check-deposit")
    assert len(tasks) == 1
    task = tasks[0]

    assert timestamp_before_call <= task.pop("next_run") <= timestamp_after_call
    assert task["arguments"] == {
        "args": [],
        "kwargs": {"collection": "test", "deposit_id": deposit_id,},
    }
    assert task["policy"] == "oneshot"
    assert task["type"] == "check-deposit"
    assert task["retries_left"] == 3


def test_add_deposit_schedules_check(
    authenticated_client, deposit_collection, sample_archive, swh_scheduler
):
    """Posting deposit by POST Col-IRI creates a checker task

    """
    tasks = swh_scheduler.grab_ready_tasks("check-deposit")
    assert len(tasks) == 0

    external_id = "external-id-schedules-check"
    url = reverse(COL_IRI, args=[deposit_collection.name])

    timestamp_before_call = now()

    response = authenticated_client.post(
        url,
        content_type="application/zip",  # as zip
        data=sample_archive["data"],
        # + headers
        CONTENT_LENGTH=sample_archive["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=sample_archive["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=%s" % (sample_archive["name"]),
    )

    timestamp_after_call = now()

    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    actual_state = response_content["swh:deposit_status"]
    assert actual_state == DEPOSIT_STATUS_DEPOSITED
    deposit_id = int(response_content["swh:deposit_id"])

    assert_task_for_deposit(
        swh_scheduler, deposit_id, timestamp_before_call, timestamp_after_call
    )


def test_update_deposit_schedules_check(
    authenticated_client,
    deposit_collection,
    partial_deposit_with_metadata,
    atom_dataset,
    swh_scheduler,
):
    """Updating deposit by POST SE-IRI creates a checker task

    """
    deposit = partial_deposit_with_metadata
    assert deposit.status == DEPOSIT_STATUS_PARTIAL

    tasks = swh_scheduler.grab_ready_tasks("check-deposit")
    assert len(tasks) == 0

    update_uri = reverse(SE_IRI, args=[deposit_collection.name, deposit.id])

    timestamp_before_call = now()

    response = authenticated_client.post(
        update_uri,
        content_type="application/atom+xml;type=entry",
        data="",
        size=0,
        HTTP_IN_PROGRESS=False,
    )

    timestamp_after_call = now()

    assert response.status_code == status.HTTP_200_OK

    response_content = parse_xml(BytesIO(response.content))
    actual_state = response_content["swh:deposit_status"]
    assert actual_state == DEPOSIT_STATUS_DEPOSITED
    assert deposit.id == int(response_content["swh:deposit_id"])

    assert_task_for_deposit(
        swh_scheduler, deposit.id, timestamp_before_call, timestamp_after_call
    )
