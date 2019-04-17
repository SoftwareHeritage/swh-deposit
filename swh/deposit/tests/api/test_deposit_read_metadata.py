# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from django.urls import reverse
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.template_metadata = """<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
  <title>Composing a Web of Audio Applications</title>
  <client>hal</client>
  <id>hal-01243065</id>
  <external_identifier>hal-01243065</external_identifier>
  <codemeta:url>https://hal-test.archives-ouvertes.fr/hal-01243065</codemeta:url>
  <codemeta:applicationCategory>test</codemeta:applicationCategory>
  <codemeta:keywords>DSP programming</codemeta:keywords>
  <codemeta:description>this is the description</codemeta:description>
  <codemeta:version>1</codemeta:version>
  <codemeta:runtimePlatform>phpstorm</codemeta:runtimePlatform>
  <codemeta:developmentStatus>stable</codemeta:developmentStatus>
  <codemeta:programmingLanguage>php</codemeta:programmingLanguage>
  <codemeta:programmingLanguage>python</codemeta:programmingLanguage>
  <codemeta:programmingLanguage>C</codemeta:programmingLanguage>
  <codemeta:license>
    <codemeta:name>GNU General Public License v3.0 only</codemeta:name>
  </codemeta:license>
  <codemeta:license>
    <codemeta:name>CeCILL Free Software License Agreement v1.1</codemeta:name>
  </codemeta:license>
  <author>
    <name>HAL</name>
    <email>hal@ccsd.cnrs.fr</email>
  </author>
  <codemeta:author>
    <codemeta:name>Morane Gruenpeter</codemeta:name>
  </codemeta:author>
%s
</entry>"""

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
                    'codemeta:dateCreated': '2017-10-07T15:17:08Z',
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
                'committer_date': {
                    'timestamp': {
                        'seconds': 1507389428,
                        'microseconds': 0
                    },
                    'offset': 0,
                    'negative_utc': False
                },
                'message': 'hal: Deposit %s in collection hal' % deposit_id,
                'author': SWH_PERSON,
                'committer': SWH_PERSON,
                'date': {
                    'timestamp': {
                        'seconds': 1507389428,
                        'microseconds': 0
                    },
                    'offset': 0,
                    'negative_utc': False
                },
                'metadata': {
                    '@xmlns': ['http://www.w3.org/2005/Atom'],
                    'author': ['some awesome author', 'another one', 'no one'],
                    'external_identifier': 'some-external-id',
                    'codemeta:dateCreated': '2017-10-07T15:17:08Z',
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
                    'codemeta:dateCreated': '2017-10-07T15:17:08Z',
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
                'date': {
                    'timestamp': {
                        'seconds': 1507389428,
                        'microseconds': 0
                    },
                    'offset': 0,
                    'negative_utc': False
                },
                'committer_date': {
                    'timestamp': {
                        'seconds': 1507389428,
                        'microseconds': 0
                    },
                    'offset': 0,
                    'negative_utc': False
                },
                'author': SWH_PERSON,
                'committer': SWH_PERSON,
                'type': 'tar',
                'message': 'hal: Deposit %s in collection hal' % deposit_id,
                'metadata': {
                    '@xmlns': ['http://www.w3.org/2005/Atom'],
                    'author': ['some awesome author', 'another one', 'no one'],
                    'codemeta:dateCreated': '2017-10-07T15:17:08Z',
                    'external_identifier': 'some-external-id',
                    'url': 'https://hal-test.archives-ouvertes.fr/' +
                           'some-external-id'
                },
                'parents': [swh_id]
            },
            'branch_name': 'master',
        }

        self.assertEqual(data, expected_meta)

    def test_read_metadata_3(self):
        """date(Created|Published) provided, uses author/committer date

        """
        # add metadata to the deposit with datePublished and dateCreated
        codemeta_entry_data = self.template_metadata % """
  <codemeta:dateCreated>2015-04-06T17:08:47+02:00</codemeta:dateCreated>
  <codemeta:datePublished>2017-05-03T16:08:47+02:00</codemeta:datePublished>
"""

        deposit_id = self.create_deposit_partial_with_data_in_args(
            codemeta_entry_data)

        url = reverse(PRIVATE_GET_DEPOSIT_METADATA,
                      args=[self.collection.name, deposit_id])

        response = self.client.get(url)

        self.assertEqual(response.status_code,
                         status.HTTP_200_OK)
        self.assertEqual(response._headers['content-type'][1],
                         'application/json')
        data = response.json()

        expected_origin = {
            'type': 'deposit',
            'url': 'https://hal-test.archives-ouvertes.fr/hal-01243065'
        }
        expected_metadata = {
            '@xmlns': 'http://www.w3.org/2005/Atom',
            '@xmlns:codemeta':
            'https://doi.org/10.5063/SCHEMA/CODEMETA-2.0',
            'author': {
                'email': 'hal@ccsd.cnrs.fr',
                'name': 'HAL'
            },
            'client': 'hal',
            'codemeta:applicationCategory': 'test',
            'codemeta:author': {
                'codemeta:name': 'Morane Gruenpeter'
            },
            'codemeta:dateCreated': '2015-04-06T17:08:47+02:00',
            'codemeta:datePublished': '2017-05-03T16:08:47+02:00',
            'codemeta:description': 'this is the description',
            'codemeta:developmentStatus': 'stable',
            'codemeta:keywords': 'DSP programming',
            'codemeta:license': [
                {
                    'codemeta:name': 'GNU General Public License v3.0 only'
                },
                {
                    'codemeta:name':
                    'CeCILL Free Software License Agreement v1.1'
                }
            ],
            'codemeta:programmingLanguage': [
                'php', 'python', 'C'
            ],
            'codemeta:runtimePlatform': 'phpstorm',
            'codemeta:url': 'https://hal-test.archives-ouvertes.fr/hal-01243065',  # noqa
            'codemeta:version': '1',
            'external_identifier': 'hal-01243065',
            'id': 'hal-01243065',
            'title': 'Composing a Web of Audio Applications'
        }

        expected_origin_metadata = {
            'metadata': expected_metadata,
            'provider': {
                'metadata': {},
                'provider_name': 'hal',
                'provider_type': 'deposit_client',
                'provider_url': 'https://hal-test.archives-ouvertes.fr/'
            },
            'tool': {
                'configuration': {
                    'sword_version': '2'
                },
                'name': 'swh-deposit',
                'version': '0.0.1'
            }
        }

        expected_revision = {
            'author': {
                'email': 'robot@softwareheritage.org',
                'fullname': 'Software Heritage',
                'name': 'Software Heritage'
            },
            'committer': {
                'email': 'robot@softwareheritage.org',
                'fullname': 'Software Heritage',
                'name': 'Software Heritage'
            },
            'committer_date': {
                'negative_utc': False,
                'offset': 120,
                'timestamp': {
                    'microseconds': 0,
                    'seconds': 1493820527
                }
            },
            'date': {
                'negative_utc': False,
                'offset': 120,
                'timestamp': {
                    'microseconds': 0,
                    'seconds': 1428332927
                }
            },
            'message': 'hal: Deposit %s in collection hal' % deposit_id,
            'metadata': expected_metadata,
            'synthetic': True,
            'type': 'tar'
        }

        expected_meta = {
            'branch_name': 'master',
            'origin': expected_origin,
            'origin_metadata': expected_origin_metadata,
            'revision': expected_revision,
        }

        self.assertEqual(data, expected_meta)

    def test_read_metadata_4(self):
        """dateCreated/datePublished not provided, revision uses complete_date

        """
        codemeta_entry_data = self.template_metadata % ''

        deposit_id = self.create_deposit_partial_with_data_in_args(
            codemeta_entry_data)

        # will use the deposit completed date as fallback date
        deposit = Deposit.objects.get(pk=deposit_id)
        deposit.complete_date = '2016-04-06'
        deposit.save()

        url = reverse(PRIVATE_GET_DEPOSIT_METADATA,
                      args=[self.collection.name, deposit_id])

        response = self.client.get(url)

        self.assertEqual(response.status_code,
                         status.HTTP_200_OK)
        self.assertEqual(response._headers['content-type'][1],
                         'application/json')
        data = response.json()

        expected_origin = {
            'type': 'deposit',
            'url': 'https://hal-test.archives-ouvertes.fr/hal-01243065'
        }
        expected_metadata = {
            '@xmlns': 'http://www.w3.org/2005/Atom',
            '@xmlns:codemeta':
            'https://doi.org/10.5063/SCHEMA/CODEMETA-2.0',
            'author': {
                'email': 'hal@ccsd.cnrs.fr',
                'name': 'HAL'
            },
            'client': 'hal',
            'codemeta:applicationCategory': 'test',
            'codemeta:author': {
                'codemeta:name': 'Morane Gruenpeter'
            },
            'codemeta:description': 'this is the description',
            'codemeta:developmentStatus': 'stable',
            'codemeta:keywords': 'DSP programming',
            'codemeta:license': [
                {
                    'codemeta:name': 'GNU General Public License v3.0 only'
                },
                {
                    'codemeta:name':
                    'CeCILL Free Software License Agreement v1.1'
                }
            ],
            'codemeta:programmingLanguage': [
                'php', 'python', 'C'
            ],
            'codemeta:runtimePlatform': 'phpstorm',
            'codemeta:url': 'https://hal-test.archives-ouvertes.fr/hal-01243065',  # noqa
            'codemeta:version': '1',
            'external_identifier': 'hal-01243065',
            'id': 'hal-01243065',
            'title': 'Composing a Web of Audio Applications'
        }

        expected_origin_metadata = {
            'metadata': expected_metadata,
            'provider': {
                'metadata': {},
                'provider_name': 'hal',
                'provider_type': 'deposit_client',
                'provider_url': 'https://hal-test.archives-ouvertes.fr/'
            },
            'tool': {
                'configuration': {
                    'sword_version': '2'
                },
                'name': 'swh-deposit',
                'version': '0.0.1'
            }
        }

        expected_revision = {
            'author': {
                'email': 'robot@softwareheritage.org',
                'fullname': 'Software Heritage',
                'name': 'Software Heritage'
            },
            'committer': {
                'email': 'robot@softwareheritage.org',
                'fullname': 'Software Heritage',
                'name': 'Software Heritage'
            },
            'committer_date': {
                'negative_utc': False,
                'offset': 0,
                'timestamp': {
                    'microseconds': 0,
                    'seconds': 1459900800
                }
            },
            'date': {
                'negative_utc': False,
                'offset': 0,
                'timestamp': {
                    'microseconds': 0,
                    'seconds': 1459900800
                }
            },
            'message': 'hal: Deposit %s in collection hal' % deposit_id,
            'metadata': expected_metadata,
            'synthetic': True,
            'type': 'tar'
        }

        expected_meta = {
            'branch_name': 'master',
            'origin': expected_origin,
            'origin_metadata': expected_origin_metadata,
            'revision': expected_revision,
        }

        self.assertEqual(data, expected_meta)

    def test_read_metadata_5(self):
        """dateCreated/datePublished provided, revision uses author/committer
           date

        If multiple dateCreated provided, the first occurrence (of
        dateCreated) is selected.  If multiple datePublished provided,
        the first occurrence (of datePublished) is selected.

        """
        # add metadata to the deposit with multiple datePublished/dateCreated
        codemeta_entry_data = self.template_metadata % """
  <codemeta:dateCreated>2015-04-06T17:08:47+02:00</codemeta:dateCreated>
  <codemeta:datePublished>2017-05-03T16:08:47+02:00</codemeta:datePublished>
  <codemeta:dateCreated>2016-04-06T17:08:47+02:00</codemeta:dateCreated>
  <codemeta:datePublished>2018-05-03T16:08:47+02:00</codemeta:datePublished>
"""

        deposit_id = self.create_deposit_partial_with_data_in_args(
            codemeta_entry_data)

        url = reverse(PRIVATE_GET_DEPOSIT_METADATA,
                      args=[self.collection.name, deposit_id])

        response = self.client.get(url)

        self.assertEqual(response.status_code,
                         status.HTTP_200_OK)
        self.assertEqual(response._headers['content-type'][1],
                         'application/json')
        data = response.json()

        expected_origin = {
            'type': 'deposit',
            'url': 'https://hal-test.archives-ouvertes.fr/hal-01243065'
        }
        expected_metadata = {
            '@xmlns': 'http://www.w3.org/2005/Atom',
            '@xmlns:codemeta':
            'https://doi.org/10.5063/SCHEMA/CODEMETA-2.0',
            'author': {
                'email': 'hal@ccsd.cnrs.fr',
                'name': 'HAL'
            },
            'client': 'hal',
            'codemeta:applicationCategory': 'test',
            'codemeta:author': {
                'codemeta:name': 'Morane Gruenpeter'
            },
            'codemeta:dateCreated': [
                '2015-04-06T17:08:47+02:00',
                '2016-04-06T17:08:47+02:00',
            ],
            'codemeta:datePublished': [
                '2017-05-03T16:08:47+02:00',
                '2018-05-03T16:08:47+02:00',
            ],
            'codemeta:description': 'this is the description',
            'codemeta:developmentStatus': 'stable',
            'codemeta:keywords': 'DSP programming',
            'codemeta:license': [
                {
                    'codemeta:name': 'GNU General Public License v3.0 only'
                },
                {
                    'codemeta:name':
                    'CeCILL Free Software License Agreement v1.1'
                }
            ],
            'codemeta:programmingLanguage': [
                'php', 'python', 'C'
            ],
            'codemeta:runtimePlatform': 'phpstorm',
            'codemeta:url': 'https://hal-test.archives-ouvertes.fr/hal-01243065',  # noqa
            'codemeta:version': '1',
            'external_identifier': 'hal-01243065',
            'id': 'hal-01243065',
            'title': 'Composing a Web of Audio Applications'
        }

        expected_origin_metadata = {
            'metadata': expected_metadata,
            'provider': {
                'metadata': {},
                'provider_name': 'hal',
                'provider_type': 'deposit_client',
                'provider_url': 'https://hal-test.archives-ouvertes.fr/'
            },
            'tool': {
                'configuration': {
                    'sword_version': '2'
                },
                'name': 'swh-deposit',
                'version': '0.0.1'
            }
        }

        expected_revision = {
            'author': {
                'email': 'robot@softwareheritage.org',
                'fullname': 'Software Heritage',
                'name': 'Software Heritage'
            },
            'committer': {
                'email': 'robot@softwareheritage.org',
                'fullname': 'Software Heritage',
                'name': 'Software Heritage'
            },
            'committer_date': {
                'negative_utc': False,
                'offset': 120,
                'timestamp': {
                    'microseconds': 0,
                    'seconds': 1493820527
                }
            },
            'date': {
                'negative_utc': False,
                'offset': 120,
                'timestamp': {
                    'microseconds': 0,
                    'seconds': 1428332927
                }
            },
            'message': 'hal: Deposit %s in collection hal' % deposit_id,
            'metadata': expected_metadata,
            'synthetic': True,
            'type': 'tar'
        }

        expected_meta = {
            'branch_name': 'master',
            'origin': expected_origin,
            'origin_metadata': expected_origin_metadata,
            'revision': expected_revision,
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
