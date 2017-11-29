# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json

from django.core.urlresolvers import reverse
from nose.tools import istest
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.models import Deposit, DEPOSIT_STATUS_DETAIL
from swh.deposit.config import PRIVATE_PUT_DEPOSIT, DEPOSIT_STATUS_READY
from ..common import BasicTestCase


class UpdateDepositStatusTest(APITestCase, BasicTestCase):
    """Update the deposit's status scenario

    """
    def setUp(self):
        super().setUp()
        deposit = Deposit(status=DEPOSIT_STATUS_READY,
                          collection=self.collection,
                          client=self.user)
        deposit.save()
        self.deposit = Deposit.objects.get(pk=deposit.id)
        assert self.deposit.status == DEPOSIT_STATUS_READY

    @istest
    def update_deposit_status(self):
        """Existing status for update should return a 204 response

        """
        url = reverse(PRIVATE_PUT_DEPOSIT,
                      args=[self.collection.name, self.deposit.id])

        possible_status = set(DEPOSIT_STATUS_DETAIL.keys()) - set(['success'])

        for _status in possible_status:
            response = self.client.put(
                url,
                content_type='application/json',
                data=json.dumps({'status': _status}))

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

            deposit = Deposit.objects.get(pk=self.deposit.id)
            self.assertEquals(deposit.status, _status)

    @istest
    def update_deposit_with_success_ingestion_and_swh_id(self):
        """Existing status for update should return a 204 response

        """
        url = reverse(PRIVATE_PUT_DEPOSIT,
                      args=[self.collection.name, self.deposit.id])

        expected_status = 'success'
        expected_id = revision_id = '47dc6b4636c7f6cba0df83e3d5490bf4334d987e'
        response = self.client.put(
            url,
            content_type='application/json',
            data=json.dumps({
                'status': expected_status,
                'revision_id': revision_id,
            }))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        deposit = Deposit.objects.get(pk=self.deposit.id)
        self.assertEquals(deposit.status, expected_status)
        self.assertEquals(deposit.swh_id, expected_id)

    @istest
    def update_deposit_status_will_fail_with_unknown_status(self):
        """Unknown status for update should return a 400 response

        """
        url = reverse(PRIVATE_PUT_DEPOSIT,
                      args=[self.collection.name, self.deposit.id])

        response = self.client.put(
            url,
            content_type='application/json',
            data=json.dumps({'status': 'unknown'}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @istest
    def update_deposit_status_will_fail_with_no_status_key(self):
        """No status provided for update should return a 400 response

        """
        url = reverse(PRIVATE_PUT_DEPOSIT,
                      args=[self.collection.name, self.deposit.id])

        response = self.client.put(
            url,
            content_type='application/json',
            data=json.dumps({'something': 'something'}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @istest
    def update_deposit_status_success_without_swh_id_fail(self):
        """Providing 'success' status without swh_id should return a 400

        """
        url = reverse(PRIVATE_PUT_DEPOSIT,
                      args=[self.collection.name, self.deposit.id])

        response = self.client.put(
            url,
            content_type='application/json',
            data=json.dumps({'status': 'success'}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
