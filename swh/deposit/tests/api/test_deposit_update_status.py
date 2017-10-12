# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json

from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.models import Deposit, DEPOSIT_STATUS_DETAIL
from swh.deposit.config import PRIVATE_PUT_DEPOSIT
from ..common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine


class UpdateDepositStatusTest(APITestCase, WithAuthTestCase, BasicTestCase,
                              CommonCreationRoutine):
    """Update the deposit's status scenario

    """
    def setUp(self):
        super().setUp()
        deposit_id = self.create_deposit_ready()
        self.deposit = Deposit.objects.get(pk=deposit_id)
        assert self.deposit.status == 'ready'

    def test_update_deposit_status(self):
        """Existing status for update should return a 204 response

        """
        url = reverse(PRIVATE_PUT_DEPOSIT, args=[
            self.username, self.deposit.id])

        for _status in DEPOSIT_STATUS_DETAIL.keys():
            response = self.client.put(
                url,
                content_type='application/json',
                data=json.dumps({'status': _status}))

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

            deposit = Deposit.objects.get(pk=self.deposit.id)
            self.assertEquals(deposit.status, _status)

    def test_update_deposit_status_will_fail_with_unknown_status(self):
        """Unknown status for update should return a 400 response

        """
        url = reverse(PRIVATE_PUT_DEPOSIT, args=[
            self.username, self.deposit.id])

        response = self.client.put(
            url,
            content_type='application/json',
            data=json.dumps({'status': 'unknown'}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_deposit_status_will_fail_with_no_status_key(self):
        """No status provided for update should return a 400 response

        """
        url = reverse(PRIVATE_PUT_DEPOSIT, args=[
            self.username, self.deposit.id])

        response = self.client.put(
            url,
            content_type='application/json',
            data=json.dumps({'something': 'something'}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
