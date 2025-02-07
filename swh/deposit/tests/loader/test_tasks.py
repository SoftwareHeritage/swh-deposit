# Copyright (C) 2018-2025  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def test_task_check_eventful(
    mocker, deposit_config_path, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    """Successful check should make the check succeed"""
    check = mocker.patch("swh.deposit.loader.checker.DepositChecker.check")
    check.return_value = {"status": "eventful"}

    collection = "collection"
    deposit_id = 42
    res = swh_scheduler_celery_app.send_task(
        "swh.deposit.loader.tasks.ChecksDepositTsk", args=[collection, deposit_id]
    )
    assert res
    res.wait()
    assert res.successful()

    assert res.result == {"status": "eventful"}


def test_task_check_failure(
    mocker, deposit_config_path, swh_scheduler_celery_app, swh_scheduler_celery_worker
):
    """Unverified check status should make the check fail"""
    check = mocker.patch("swh.deposit.loader.checker.DepositChecker.check")
    check.return_value = {"status": "failed"}

    collection = "collec"
    deposit_id = 666
    res = swh_scheduler_celery_app.send_task(
        "swh.deposit.loader.tasks.ChecksDepositTsk", args=[collection, deposit_id]
    )
    assert res
    res.wait()
    assert res.successful()

    assert res.result == {"status": "failed"}
