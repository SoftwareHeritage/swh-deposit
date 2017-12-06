# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json

from django.core.urlresolvers import reverse
from nose.tools import istest
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
    @istest
    def read_metadata(self):
        """Private metadata read api to existing deposit should return metadata

        """
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
                'url': 'https://hal.test.fr/some-external-id',
                'type': 'deposit'
            },
            'origin_metadata': {
                'metadata': {
                    '{http://www.w3.org/2005/Atom}external_identifier':
                        'some-external-id'
                },
                'provider': {
                    'provider_name': '',
                    'provider_type': 'deposit_client',
                    'provider_url': 'https://hal.test.fr/',
                    'metadata': {}
                },
                'tool': {
                    'tool_name': 'swh-deposit',
                    'tool_version': '0.0.1',
                    'tool_configuration': {
                        'sword_version': '2'
                    }
                }
            },
            'revision': {
                'synthetic': True,
                'committer_date': None,
                'message': ': Deposit %s in collection hal' % deposit_id,
                'author': SWH_PERSON,
                'committer': SWH_PERSON,
                'date': None,
                'metadata': {
                    '{http://www.w3.org/2005/Atom}external_identifier':
                        'some-external-id'
                },
                'type': 'tar'
            },
            'occurrence': {
                'branch': 'master'
            }
        }

        self.assertEquals(data, expected_meta)

    @istest
    def read_metadata_revision_with_parent(self):
        """Private read metadata to a deposit (with parent) returns metadata

        """
        swh_id = 'da78a9d4cf1d5d29873693fd496142e3a18c20fa'
        deposit_id1 = self.create_deposit_with_status(
            status=DEPOSIT_STATUS_LOAD_SUCCESS,
            external_id='some-external-id',
            swh_id=swh_id)

        deposit_parent = Deposit.objects.get(pk=deposit_id1)
        self.assertEquals(deposit_parent.swh_id, swh_id)
        self.assertEquals(deposit_parent.external_id, 'some-external-id')
        self.assertEquals(deposit_parent.status, DEPOSIT_STATUS_LOAD_SUCCESS)

        deposit_id = self.create_deposit_partial(
            external_id='some-external-id')

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEquals(deposit.external_id, 'some-external-id')
        self.assertEquals(deposit.swh_id, None)
        self.assertEquals(deposit.parent, deposit_parent)
        self.assertEquals(deposit.status, DEPOSIT_STATUS_PARTIAL)

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
                'url': 'https://hal.test.fr/some-external-id',
                'type': 'deposit'
            },
            'origin_metadata': {
                'metadata': {
                    '{http://www.w3.org/2005/Atom}external_identifier':
                    'some-external-id'
                },
                'provider': {
                    'provider_name': '',
                    'provider_type': 'deposit_client',
                    'provider_url': 'https://hal.test.fr/',
                    'metadata': {}
                },
                'tool': {
                    'tool_name': 'swh-deposit',
                    'tool_version': '0.0.1',
                    'tool_configuration': {
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
                'message': ': Deposit %s in collection hal' % deposit_id,
                'metadata': {
                    '{http://www.w3.org/2005/Atom}external_identifier':
                    'some-external-id'
                },
                'parents': [swh_id]
            },
            'occurrence': {
                'branch': 'master'
            }
        }

        self.assertEquals(data, expected_meta)

    @istest
    def access_to_nonexisting_deposit_returns_404_response(self):
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

    @istest
    def access_to_nonexisting_collection_returns_404_response(self):
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
