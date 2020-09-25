# Copyright (C) 2018-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest


@pytest.mark.db
def test_task_check_eventful(
    mocker, deposit_config_path, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    """Successful check should make the check succeed

    """
    client = mocker.patch("swh.deposit.loader.checker.PrivateApiDepositClient.check")
    client.return_value = "verified"

    collection = "collection"
    deposit_id = 42
    res = swh_scheduler_celery_app.send_task(
        "swh.deposit.loader.tasks.ChecksDepositTsk", args=[collection, deposit_id]
    )
    assert res
    res.wait()
    assert res.successful()

    assert res.result == {"status": "eventful"}
    client.assert_called_once_with(f"/{collection}/{deposit_id}/check/")


@pytest.mark.db
def test_task_check_failure(
    mocker, deposit_config_path, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    """Unverified check status should make the check fail

    """
    client = mocker.patch("swh.deposit.loader.checker.PrivateApiDepositClient.check")
    client.return_value = "not-verified"  # will make the status "failed"

    collection = "collec"
    deposit_id = 666
    res = swh_scheduler_celery_app.send_task(
        "swh.deposit.loader.tasks.ChecksDepositTsk", args=[collection, deposit_id]
    )
    assert res
    res.wait()
    assert res.successful()

    assert res.result == {"status": "failed"}
    client.assert_called_once_with(f"/{collection}/{deposit_id}/check/")


@pytest.mark.db
def test_task_check_3(
    mocker, deposit_config_path, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    """Unexpected failures should fail the check

    """
    client = mocker.patch("swh.deposit.loader.checker.PrivateApiDepositClient.check")
    client.side_effect = ValueError("unexpected failure will make it fail")

    collection = "another-collection"
    deposit_id = 999
    res = swh_scheduler_celery_app.send_task(
        "swh.deposit.loader.tasks.ChecksDepositTsk", args=[collection, deposit_id]
    )
    assert res
    res.wait()
    assert res.successful()

    assert res.result == {"status": "failed"}
    client.assert_called_once_with(f"/{collection}/{deposit_id}/check/")
