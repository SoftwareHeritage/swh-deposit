# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json

from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.config import PRIVATE_GET_DEPOSIT_METADATA

from ..common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine


class DepositReadMetadataTest(APITestCase, WithAuthTestCase, BasicTestCase,
                              CommonCreationRoutine):
    """Deposit access to read metadata information on deposit.

    """
    def test_access_to_an_existing_deposit_returns_metadata(self):
        deposit_id = self.create_deposit_partial()

        url = reverse(PRIVATE_GET_DEPOSIT_METADATA,
                      args=[self.collection.name, deposit_id])

        response = self.client.get(url)

        self.assertEqual(response.status_code,
                         status.HTTP_200_OK)
        self.assertEquals(response._headers['content-type'][1],
                          'application/json')
        data = json.loads(response.content.decode('utf-8'))

        expected_meta = {
            'origin': {
                'url': 'some-external-id',
                'type': 'hal'
            },
            'revision': {
                'synthetic': True,
                'committer_date': None,
                'message': ': Deposit %s in collection hal' % deposit_id,
                'author': {
                    'fullname': '', 'email': '', 'name': ''
                },
                'committer': {
                    'fullname': '', 'email': '', 'name': ''
                },
                'date': None,
                'metadata': {},
                'type': 'tar'
            },
            'occurrence': {
                'branch': 'master'
            }
        }

        self.assertEquals(data, expected_meta)

    def test_access_to_nonexisting_deposit_returns_404_response(self):
        """Read unknown collection should return a 404 response

        """
        unknown_id = '999'
        url = reverse(PRIVATE_GET_DEPOSIT_METADATA,
                      args=[self.collection.name, unknown_id])

        response = self.client.get(url)
        self.assertEqual(response.status_code,
                         status.HTTP_404_NOT_FOUND)
        self.assertIn('Deposit with id %s does not exist' % unknown_id,
                      response.content.decode('utf-8'))

    def test_access_to_nonexisting_collection_returns_404_response(self):
        """Read unknown deposit should return a 404 response

        """
        collection_name = 'non-existing'
        deposit_id = self.create_deposit_partial()
        url = reverse(PRIVATE_GET_DEPOSIT_METADATA,
                      args=[collection_name, deposit_id])

        response = self.client.get(url)
        self.assertEqual(response.status_code,
                         status.HTTP_404_NOT_FOUND)
        self.assertIn('Unknown collection name %s' % collection_name,
                      response.content.decode('utf-8'),)
