# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from rest_framework.test import APITestCase

from swh.deposit.models import Deposit
from swh.deposit.config import PRIVATE_CHECK_DEPOSIT, DEPOSIT_STATUS_VERIFIED
from swh.deposit.config import DEPOSIT_STATUS_REJECTED
from swh.deposit.loader.checker import DepositChecker
from django.core.urlresolvers import reverse


from .common import SWHDepositTestClient, CLIENT_TEST_CONFIG
from ..common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine
from ..common import FileSystemCreationRoutine


class DepositCheckerScenarioTest(APITestCase, WithAuthTestCase,
                                 BasicTestCase, CommonCreationRoutine,
                                 FileSystemCreationRoutine):

    def setUp(self):
        super().setUp()

        # 2. Sets a basic client which accesses the test data
        checker_client = SWHDepositTestClient(client=self.client,
                                              config=CLIENT_TEST_CONFIG)
        # 3. setup loader with no persistence and that client
        self.checker = DepositChecker(client=checker_client)

    def test_check_deposit_ready(self):
        """Check on a valid 'deposited' deposit should result in 'verified'

        """
        # 1. create a deposit with archive and metadata
        deposit_id = self.create_simple_binary_deposit()
        deposit_id = self.update_binary_deposit(deposit_id,
                                                status_partial=False)

        args = [self.collection.name, deposit_id]
        deposit_check_url = reverse(PRIVATE_CHECK_DEPOSIT, args=args)

        # when
        actual_result = self.checker.check(deposit_check_url=deposit_check_url)
        # then
        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_VERIFIED)
        self.assertEqual(actual_result, {'status': 'eventful'})

    def test_check_deposit_rejected(self):
        """Check on invalid 'deposited' deposit should result in 'rejected'

        """
        # 1. create a deposit with archive and metadata
        deposit_id = self.create_deposit_with_invalid_archive()

        args = [self.collection.name, deposit_id]
        deposit_check_url = reverse(PRIVATE_CHECK_DEPOSIT, args=args)

        # when
        actual_result = self.checker.check(deposit_check_url=deposit_check_url)

        # then
        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_REJECTED)
        self.assertEqual(actual_result, {'status': 'eventful'})
