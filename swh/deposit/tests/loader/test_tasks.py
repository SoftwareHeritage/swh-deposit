# Copyright (C) 2018-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch


@patch('swh.deposit.loader.checker.DepositChecker.check')
def deposit_check(checker, swh_config, swh_app, celery_session_worker):
    checker.return_value = {'status': 'uneventful'}

    res = swh_app.send_task(
        'swh.deposit.loader.tasks.ChecksDepositTsk',
        args=['check_deposit_url'])
    assert res
    res.wait()
    assert res.successful()

    assert res.result == {'status': 'uneventful'}
    checker.assert_called_once_with('check_deposit_url')
