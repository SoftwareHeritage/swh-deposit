# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from nose.tools import istest
from rest_framework.test import APITestCase

from swh.deposit.models import Deposit
from swh.deposit.config import PRIVATE_CHECK_DEPOSIT, DEPOSIT_STATUS_READY
from swh.deposit.config import DEPOSIT_STATUS_REJECTED
from swh.deposit.injection.checker import DepositChecker
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

    @istest
    def check_deposit_ready(self):
        """Check a valid deposit ready-for-checks should result in ready state

        """
        # 1. create a deposit with archive and metadata
        deposit_id = self.create_simple_binary_deposit()

        args = [self.collection.name, deposit_id]
        deposit_check_url = reverse(PRIVATE_CHECK_DEPOSIT, args=args)

        # when
        actual_status = self.checker.check(deposit_check_url=deposit_check_url)

        # then
        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEquals(deposit.status, DEPOSIT_STATUS_READY)
        self.assertEquals(actual_status, DEPOSIT_STATUS_READY)

    @istest
    def check_deposit_rejected(self):
        """Check an invalid deposit ready-for-checks should result in rejected

        """
        # 1. create a deposit with archive and metadata
        deposit_id = self.create_invalid_deposit()

        args = [self.collection.name, deposit_id]
        deposit_check_url = reverse(PRIVATE_CHECK_DEPOSIT, args=args)

        # when
        actual_status = self.checker.check(deposit_check_url=deposit_check_url)

        # then
        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEquals(deposit.status, DEPOSIT_STATUS_REJECTED)
        self.assertEquals(actual_status, DEPOSIT_STATUS_REJECTED)
