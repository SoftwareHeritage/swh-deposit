# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import unittest

from django.core.urlresolvers import reverse
from nose.tools import istest
from nose.plugins.attrib import attr
from rest_framework import status
from rest_framework.test import APITestCase

from ...models import Deposit
from ...config import DEPOSIT_STATUS_READY, PRIVATE_CHECK_DEPOSIT
from ...config import DEPOSIT_STATUS_READY_FOR_CHECKS, DEPOSIT_STATUS_REJECTED
from ..common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine
from ..common import FileSystemCreationRoutine
from ...api.private.deposit_check import SWHChecksDeposit


@attr('fs')
class CheckDepositTest(APITestCase, WithAuthTestCase,
                       BasicTestCase, CommonCreationRoutine,
                       FileSystemCreationRoutine):
    """Check deposit endpoints.

    """
    def setUp(self):
        super().setUp()

    @istest
    def deposit_ok(self):
        """Proper deposit should succeed the checks (-> status ready)

        """
        deposit_id = self.create_simple_binary_deposit(status_partial=True)
        deposit_id = self.update_binary_deposit(deposit_id,
                                                status_partial=False)

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEquals(deposit.status, DEPOSIT_STATUS_READY_FOR_CHECKS)

        url = reverse(PRIVATE_CHECK_DEPOSIT,
                      args=[self.collection.name, deposit.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], DEPOSIT_STATUS_READY)
        deposit = Deposit.objects.get(pk=deposit.id)
        self.assertEquals(deposit.status, DEPOSIT_STATUS_READY)

    @istest
    def deposit_ko(self):
        """Invalid deposit should fail the checks (-> status rejected)

        """
        deposit_id = self.create_invalid_deposit()

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEquals(deposit.status, DEPOSIT_STATUS_READY_FOR_CHECKS)

        url = reverse(PRIVATE_CHECK_DEPOSIT,
                      args=[self.collection.name, deposit.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], DEPOSIT_STATUS_REJECTED)
        self.assertEqual(data['details'],
                         'Some archive(s) and metadata and url ' +
                         'failed the checks.')
        deposit = Deposit.objects.get(pk=deposit.id)
        self.assertEquals(deposit.status, DEPOSIT_STATUS_REJECTED)

    @istest
    def check_deposit_metadata_ok(self):
        """Proper deposit should succeed the checks (-> status ready)
           with all **MUST** metadata

           using the codemeta metadata test set
        """
        deposit_id = self.create_simple_binary_deposit(status_partial=True)
        deposit_id_metadata = self.add_metadata_to_deposit(deposit_id)
        self.assertEquals(deposit_id, deposit_id_metadata)

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEquals(deposit.status, DEPOSIT_STATUS_READY_FOR_CHECKS)

        url = reverse(PRIVATE_CHECK_DEPOSIT,
                      args=[self.collection.name, deposit.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['status'], DEPOSIT_STATUS_READY)
        deposit = Deposit.objects.get(pk=deposit.id)
        self.assertEquals(deposit.status, DEPOSIT_STATUS_READY)


class CheckMetadata(unittest.TestCase, SWHChecksDeposit):
    @istest
    def check_metadata_ok(self):
        actual_check = self._check_metadata({
            'url': 'something',
            'external_identifier': 'something-else',
            'name': 'foo',
            'author': 'someone',
        })

        self.assertTrue(actual_check)

    @istest
    def check_metadata_ok2(self):
        actual_check = self._check_metadata({
            'url': 'something',
            'external_identifier': 'something-else',
            'title': 'bar',
            'author': 'someone',
        })

        self.assertTrue(actual_check)

    @istest
    def check_metadata_ko(self):
        actual_check = self._check_metadata({
            'url': 'something',
            'external_identifier': 'something-else',
            'author': 'someone',
        })

        self.assertFalse(actual_check)

    @istest
    def check_metadata_ko2(self):
        actual_check = self._check_metadata({
            'url': 'something',
            'external_identifier': 'something-else',
            'title': 'foobar',
        })

        self.assertFalse(actual_check)