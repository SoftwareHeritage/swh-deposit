# Copyright (C) 2018-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from unittest.mock import patch


@pytest.mark.db
def test_deposit_check(mocker, swh_config, swh_app, celery_session_worker):
    checker = mocker.patch("swh.deposit.loader.checker.DepositChecker.check")
    checker.return_value = {"status": "uneventful"}

    res = swh_app.send_task(
        "swh.deposit.loader.tasks.ChecksDepositTsk", args=["collection", 42]
    )
    assert res
    res.wait()
    assert res.successful()

    assert res.result == {"status": "uneventful"}
    checker.assert_called_once_with("collection", 42)
