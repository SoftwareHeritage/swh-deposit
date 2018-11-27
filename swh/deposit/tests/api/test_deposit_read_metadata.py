# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.models import Deposit
from swh.deposit.config import PRIVATE_GET_DEPOSIT_METADATA
from swh.deposit.config import DEPOSIT_STATUS_LOAD_SUCCESS
from swh.deposit.config import DEPOSIT_STATUS_PARTIAL


from ...config import SWH_PERSON
from ..common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine


class DepositReadMetadataTest(APITestCase, WithAuthTestCase, BasicTestCase,
                              CommonCreationRoutine):
    """Deposit access to read metadata information on deposit.

    """
    def test_read_metadata(self):
        """Private metadata read api to existing deposit should return metadata

        """
        deposit_id = self.create_deposit_partial()

        url = reverse(PRIVATE_GET_DEPOSIT_METADATA,
                      args=[self.collection.name, deposit_id])

        response = self.client.get(url)

        self.assertEqual(response.status_code,
                         status.HTTP_200_OK)
        self.assertEqual(response._headers['content-type'][1],
                         'application/json')
        data = response.json()

        expected_meta = {
            'origin': {
                'url': 'https://hal-test.archives-ouvertes.fr/' +
                       'some-external-id',
                'type': 'deposit'
            },
            'origin_metadata': {
                'metadata': {
                    '@xmlns': ['http://www.w3.org/2005/Atom'],
                    'author': ['some awesome author', 'another one', 'no one'],
                    'external_identifier': 'some-external-id',
                    'url': 'https://hal-test.archives-ouvertes.fr/' +
                           'some-external-id'
                },
                'provider': {
                    'provider_name': 'hal',
                    'provider_type': 'deposit_client',
                    'provider_url': 'https://hal-test.archives-ouvertes.fr/',
                    'metadata': {}
                },
                'tool': {
                    'name': 'swh-deposit',
                    'version': '0.0.1',
                    'configuration': {
                        'sword_version': '2'
                    }
                }
            },
            'revision': {
                'synthetic': True,
                'committer_date': None,
                'message': 'hal: Deposit %s in collection hal' % deposit_id,
                'author': SWH_PERSON,
                'committer': SWH_PERSON,
                'date': None,
                'metadata': {
                    '@xmlns': ['http://www.w3.org/2005/Atom'],
                    'author': ['some awesome author', 'another one', 'no one'],
                    'external_identifier': 'some-external-id',
                    'url': 'https://hal-test.archives-ouvertes.fr/' +
                           'some-external-id'
                },
                'type': 'tar'
            },
            'branch_name': 'master',
        }

        self.assertEqual(data, expected_meta)

    def test_read_metadata_revision_with_parent(self):
        """Private read metadata to a deposit (with parent) returns metadata

        """
        swh_id = 'da78a9d4cf1d5d29873693fd496142e3a18c20fa'
        swh_persistent_id = 'swh:1:rev:%s' % swh_id
        deposit_id1 = self.create_deposit_with_status(
            status=DEPOSIT_STATUS_LOAD_SUCCESS,
            external_id='some-external-id',
            swh_id=swh_persistent_id)

        deposit_parent = Deposit.objects.get(pk=deposit_id1)
        self.assertEqual(deposit_parent.swh_id, swh_persistent_id)
        self.assertEqual(deposit_parent.external_id, 'some-external-id')
        self.assertEqual(deposit_parent.status, DEPOSIT_STATUS_LOAD_SUCCESS)

        deposit_id = self.create_deposit_partial(
            external_id='some-external-id')

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.external_id, 'some-external-id')
        self.assertEqual(deposit.swh_id, None)
        self.assertEqual(deposit.parent, deposit_parent)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_PARTIAL)

        url = reverse(PRIVATE_GET_DEPOSIT_METADATA,
                      args=[self.collection.name, deposit_id])

        response = self.client.get(url)

        self.assertEqual(response.status_code,
                         status.HTTP_200_OK)
        self.assertEqual(response._headers['content-type'][1],
                         'application/json')
        data = response.json()

        expected_meta = {
            'origin': {
                'url': 'https://hal-test.archives-ouvertes.fr/' +
                       'some-external-id',
                'type': 'deposit'
            },
            'origin_metadata': {
                'metadata': {
                    '@xmlns': ['http://www.w3.org/2005/Atom'],
                    'author': ['some awesome author', 'another one', 'no one'],
                    'external_identifier': 'some-external-id',
                    'url': 'https://hal-test.archives-ouvertes.fr/' +
                           'some-external-id'
                },
                'provider': {
                    'provider_name': 'hal',
                    'provider_type': 'deposit_client',
                    'provider_url': 'https://hal-test.archives-ouvertes.fr/',
                    'metadata': {}
                },
                'tool': {
                    'name': 'swh-deposit',
                    'version': '0.0.1',
                    'configuration': {
                        'sword_version': '2'
                    }
                }
            },
            'revision': {
                'synthetic': True,
                'date': None,
                'committer_date': None,
                'author': SWH_PERSON,
                'committer': SWH_PERSON,
                'type': 'tar',
                'message': 'hal: Deposit %s in collection hal' % deposit_id,
                'metadata': {
                    '@xmlns': ['http://www.w3.org/2005/Atom'],
                    'author': ['some awesome author', 'another one', 'no one'],
                    'external_identifier': 'some-external-id',
                    'url': 'https://hal-test.archives-ouvertes.fr/' +
                           'some-external-id'
                },
                'parents': [swh_id]
            },
            'branch_name': 'master',
        }

        self.assertEqual(data, expected_meta)

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
