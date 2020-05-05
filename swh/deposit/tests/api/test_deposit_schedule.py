# Copyright (C) 2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import datetime
from io import BytesIO
from typing import Dict

from django.urls import reverse
import pytest
from rest_framework import status

from swh.deposit.config import (
    COL_IRI,
    DEPOSIT_STATUS_DEPOSITED,
)
from swh.deposit.parsers import parse_xml


from ..conftest import TEST_CONFIG


TEST_CONFIG_WITH_CHECKS: Dict[str, object] = {
    **TEST_CONFIG,
    "checks": True,
}


@pytest.fixture()
def deposit_config():
    """Overrides the `deposit_config` fixture define in swh/deposit/tests/conftest.py
    to re-enable the checks."""
    return TEST_CONFIG_WITH_CHECKS


def now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


def test_add_deposit_schedules_check(
    authenticated_client, deposit_collection, sample_archive, swh_scheduler
):
    """Posting deposit on collection creates a checker task

    """
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
    actual_state = response_content["deposit_status"]
    assert actual_state == DEPOSIT_STATUS_DEPOSITED
    deposit_id = response_content["deposit_id"]

    tasks = swh_scheduler.grab_ready_tasks("check-deposit")
    assert len(tasks) == 1
    task = tasks[0]

    assert timestamp_before_call <= task.pop("next_run") <= timestamp_after_call
    assert task == {
        "arguments": {
            "args": [],
            "kwargs": {"collection": "test", "deposit_id": int(deposit_id),},
        },
        "current_interval": datetime.timedelta(days=1),
        "id": 1,
        "policy": "oneshot",
        "priority": None,
        "retries_left": 3,
        "status": "next_run_scheduled",
        "type": "check-deposit",
    }
