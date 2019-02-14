# Copyright (C) 2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch


@patch('swh.deposit.loader.loader.DepositLoader.load')
def test_deposit_load(mock_loader, swh_app, celery_session_worker):
    mock_loader.return_value = {'status': 'eventful'}

    res = swh_app.send_task(
        'swh.deposit.loader.tasks.LoadDepositArchiveTsk',
        kwargs=dict(archive_url='archive_url',
                    deposit_meta_url='deposit_meta_url',
                    deposit_update_url='deposit_update_url'))
    assert res
    res.wait()
    assert res.successful()

    assert res.result == {'status': 'eventful'}
    mock_loader.assert_called_once_with(
        archive_url='archive_url',
        deposit_meta_url='deposit_meta_url',
        deposit_update_url='deposit_update_url')


@patch('swh.deposit.loader.checker.DepositChecker.check')
def test_check_deposit(mock_checker, swh_app, celery_session_worker):
    mock_checker.return_value = {'status': 'uneventful'}

    res = swh_app.send_task(
        'swh.deposit.loader.tasks.ChecksDepositTsk',
        args=('check_deposit_url',))
    assert res
    res.wait()
    assert res.successful()

    assert res.result == {'status': 'uneventful'}
    mock_checker.assert_called_once_with('check_deposit_url')
