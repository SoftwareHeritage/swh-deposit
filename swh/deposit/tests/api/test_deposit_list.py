# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.core.urlresolvers import reverse
import pytest
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.api.converters import convert_status_detail

from ...config import DEPOSIT_STATUS_PARTIAL, PRIVATE_LIST_DEPOSITS
from ..common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine
from ...models import Deposit


@pytest.mark.fs
class CheckDepositListTest(APITestCase, WithAuthTestCase,
                           BasicTestCase, CommonCreationRoutine):
    """Check deposit list endpoints.

    """
    def setUp(self):
        super().setUp()

    def test_deposit_list(self):
        """Deposit list api should return the deposits

        """
        deposit_id = self.create_deposit_partial()
        # amend the deposit with a status_detail
        deposit = Deposit.objects.get(pk=deposit_id)
        status_detail = {
            'url': {
                'summary': 'At least one compatible url field. Failed',
                'fields': ['testurl'],
            },
            'metadata': [
                {
                    'summary': 'Mandatory fields missing',
                    'fields': ['9', 10, 1.212],
                },
            ],
            'archive': [
                {
                    'summary': 'Invalid archive',
                    'fields': ['3'],
                },
                {
                    'summary': 'Unsupported archive',
                    'fields': [2],
                }
            ],
        }
        deposit.status_detail = status_detail
        deposit.save()

        deposit_id2 = self.create_deposit_partial()

        # NOTE: does not work as documented
        # https://docs.djangoproject.com/en/1.11/ref/urlresolvers/#django.core.urlresolvers.reverse  # noqa
        # url = reverse(PRIVATE_LIST_DEPOSITS, kwargs={'page_size': 1})
        main_url = reverse(PRIVATE_LIST_DEPOSITS)
        url = '%s?page_size=1' % main_url
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['count'], 2)  # 2 deposits
        expected_next = '%s?page=2&page_size=1' % main_url
        self.assertTrue(data['next'].endswith(expected_next))
        self.assertIsNone(data['previous'])
        self.assertEqual(len(data['results']), 1)  # page of size 1
        deposit = data['results'][0]
        self.assertEqual(deposit['id'], deposit_id)
        self.assertEqual(deposit['status'], DEPOSIT_STATUS_PARTIAL)
        expected_status_detail = convert_status_detail(status_detail)
        self.assertEqual(deposit['status_detail'], expected_status_detail)

        # then 2nd page
        response2 = self.client.get(expected_next)

        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        data2 = response2.json()

        self.assertEqual(data2['count'], 2)  # still 2 deposits
        self.assertIsNone(data2['next'])
        expected_previous = '%s?page_size=1' % main_url
        self.assertTrue(data2['previous'].endswith(expected_previous))
        self.assertEqual(len(data2['results']), 1)  # page of size 1
        deposit2 = data2['results'][0]
        self.assertEqual(deposit2['id'], deposit_id2)
        self.assertEqual(deposit2['status'], DEPOSIT_STATUS_PARTIAL)
