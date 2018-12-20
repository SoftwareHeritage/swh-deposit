# Copyright (C) 2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import unittest
from unittest.mock import patch

from swh.deposit.loader.tasks import LoadDepositArchiveTsk, ChecksDepositTsk


class TestTasks(unittest.TestCase):
    def test_check_task_name(self):
        task = LoadDepositArchiveTsk()
        self.assertEqual(task.task_queue, 'swh_loader_deposit')

    @patch('swh.deposit.loader.loader.DepositLoader.load')
    def test_task(self, mock_loader):
        mock_loader.return_value = {'status': 'eventful'}
        task = LoadDepositArchiveTsk()

        # given
        actual_result = task.run_task(
            archive_url='archive_url',
            deposit_meta_url='deposit_meta_url',
            deposit_update_url='deposit_update_url')

        self.assertEqual(actual_result, {'status': 'eventful'})

        mock_loader.assert_called_once_with(
            archive_url='archive_url',
            deposit_meta_url='deposit_meta_url',
            deposit_update_url='deposit_update_url')


class TestTasks2(unittest.TestCase):
    def test_check_task_name(self):
        task = ChecksDepositTsk()
        self.assertEqual(task.task_queue, 'swh_checker_deposit')

    @patch('swh.deposit.loader.checker.DepositChecker.check')
    def test_task(self, mock_checker):
        mock_checker.return_value = {'status': 'uneventful'}
        task = ChecksDepositTsk()

        # given
        actual_result = task.run_task('check_deposit_url')
        self.assertEqual(actual_result, {'status': 'uneventful'})

        mock_checker.assert_called_once_with('check_deposit_url')
