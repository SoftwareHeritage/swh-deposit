# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json

from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.models import Deposit, DEPOSIT_STATUS_DETAIL
from swh.deposit.config import PRIVATE_PUT_DEPOSIT, DEPOSIT_STATUS_VERIFIED
from swh.deposit.config import DEPOSIT_STATUS_LOAD_SUCCESS
from ..common import BasicTestCase


class UpdateDepositStatusTest(APITestCase, BasicTestCase):
    """Update the deposit's status scenario

    """
    def setUp(self):
        super().setUp()
        deposit = Deposit(status=DEPOSIT_STATUS_VERIFIED,
                          collection=self.collection,
                          client=self.user)
        deposit.save()
        self.deposit = Deposit.objects.get(pk=deposit.id)
        assert self.deposit.status == DEPOSIT_STATUS_VERIFIED

    def test_update_deposit_status(self):
        """Existing status for update should return a 204 response

        """
        url = reverse(PRIVATE_PUT_DEPOSIT,
                      args=[self.collection.name, self.deposit.id])

        possible_status = set(DEPOSIT_STATUS_DETAIL.keys()) - set(
            [DEPOSIT_STATUS_LOAD_SUCCESS])

        for _status in possible_status:
            response = self.client.put(
                url,
                content_type='application/json',
                data=json.dumps({'status': _status}))

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

            deposit = Deposit.objects.get(pk=self.deposit.id)
            self.assertEqual(deposit.status, _status)

    def test_update_deposit_status_with_info(self):
        """Existing status for update with info should return a 204 response

        """
        url = reverse(PRIVATE_PUT_DEPOSIT,
                      args=[self.collection.name, self.deposit.id])

        expected_status = DEPOSIT_STATUS_LOAD_SUCCESS
        origin_url = 'something'
        directory_id = '42a13fc721c8716ff695d0d62fc851d641f3a12b'
        revision_id = '47dc6b4636c7f6cba0df83e3d5490bf4334d987e'
        expected_swh_id = 'swh:1:dir:%s' % directory_id
        expected_swh_id_context = 'swh:1:dir:%s;origin=%s' % (
            directory_id, origin_url)
        expected_swh_anchor_id = 'swh:1:rev:%s' % revision_id
        expected_swh_anchor_id_context = 'swh:1:rev:%s;origin=%s' % (
            revision_id, origin_url)

        response = self.client.put(
            url,
            content_type='application/json',
            data=json.dumps({
                'status': expected_status,
                'revision_id': revision_id,
                'directory_id': directory_id,
                'origin_url': origin_url,
            }))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        deposit = Deposit.objects.get(pk=self.deposit.id)
        self.assertEqual(deposit.status, expected_status)
        self.assertEqual(deposit.swh_id, expected_swh_id)
        self.assertEqual(deposit.swh_id_context, expected_swh_id_context)
        self.assertEqual(deposit.swh_anchor_id, expected_swh_anchor_id)
        self.assertEqual(deposit.swh_anchor_id_context,
                         expected_swh_anchor_id_context)

    def test_update_deposit_status_will_fail_with_unknown_status(self):
        """Unknown status for update should return a 400 response

        """
        url = reverse(PRIVATE_PUT_DEPOSIT,
                      args=[self.collection.name, self.deposit.id])

        response = self.client.put(
            url,
            content_type='application/json',
            data=json.dumps({'status': 'unknown'}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_deposit_status_will_fail_with_no_status_key(self):
        """No status provided for update should return a 400 response

        """
        url = reverse(PRIVATE_PUT_DEPOSIT,
                      args=[self.collection.name, self.deposit.id])

        response = self.client.put(
            url,
            content_type='application/json',
            data=json.dumps({'something': 'something'}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_deposit_status_success_without_swh_id_fail(self):
        """Providing successful status without swh_id should return a 400

        """
        url = reverse(PRIVATE_PUT_DEPOSIT,
                      args=[self.collection.name, self.deposit.id])

        response = self.client.put(
            url,
            content_type='application/json',
            data=json.dumps({'status': DEPOSIT_STATUS_LOAD_SUCCESS}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
