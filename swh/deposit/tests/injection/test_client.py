# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import shutil
import tempfile
import unittest

from nose.plugins.attrib import attr
from nose.tools import istest
from unittest.mock import patch

from swh.deposit.injection.client import DepositClient


class StreamedResponse:
    """Streamed response facsimile

    """
    def __init__(self, ok, stream):
        self.ok = ok
        self.stream = stream

    def iter_content(self):
        yield from self.stream


@attr('fs')
class DepositClientReadArchiveTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.client = DepositClient(config={})
        self.temporary_directory = tempfile.mkdtemp(dir='/tmp')

    def tearDown(self):
        super().setUp()
        shutil.rmtree(self.temporary_directory)

    @patch('swh.deposit.injection.client.requests')
    @istest
    def archive_get(self, mock_requests):
        """Reading archive should write data in temporary directory

        """
        stream_content = [b"some", b"streamed", b"response"]
        mock_requests.get.return_value = StreamedResponse(
            ok=True,
            stream=(s for s in stream_content))

        archive_path = os.path.join(self.temporary_directory, 'test.archive')
        archive_path = self.client.archive_get(
            'http://nowhere:9000/some/url', archive_path)

        self.assertTrue(os.path.exists(archive_path))

        with open(archive_path, 'rb') as f:
            actual_content = f.read()

        self.assertEquals(actual_content, b''.join(stream_content))

    @patch('swh.deposit.injection.client.requests')
    @istest
    def archive_get_can_fail(self, mock_requests):
        """Reading archive can fail for some reasons

        """
        mock_requests.get.return_value = StreamedResponse(ok=False,
                                                          stream=None)

        url = 'http://nowhere:9001/some/url'
        with self.assertRaisesRegex(
                ValueError,
                'Problem when retrieving deposit archive at %s' % url):
            self.client.archive_get(url, 'some/path')


class JsonResponse:
    """Json response facsimile

    """
    def __init__(self, ok, response):
        self.ok = ok
        self.response = response

    def json(self):
        return self.response


class DepositClientReadMetadataTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.client = DepositClient(config={})

    @patch('swh.deposit.injection.client.requests')
    @istest
    def metadata_get(self, mock_requests):
        """Reading archive should write data in temporary directory

        """
        expected_response = {"some": "dict"}
        mock_requests.get.return_value = JsonResponse(
            ok=True,
            response=expected_response)

        actual_metadata = self.client.metadata_get(
            'http://nowhere:9000/metadata')

        self.assertEquals(actual_metadata, expected_response)

    @patch('swh.deposit.injection.client.requests')
    @istest
    def metadata_get_can_fail(self, mock_requests):
        """Reading metadata can fail for some reasons

        """
        mock_requests.get.return_value = StreamedResponse(ok=False,
                                                          stream=None)

        url = 'http://nowhere:9001/some/metadata'
        with self.assertRaisesRegex(
                ValueError,
                'Problem when retrieving metadata at %s' % url):
            self.client.metadata_get(url)


class DepositClientStatusUpdateTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.client = DepositClient(config={})

    @patch('swh.deposit.injection.client.requests')
    @istest
    def status_update(self, mock_requests):
        """Update status

        """
        def side_effect(status_url, json):
            global actual_status_url, actual_json
            actual_status_url = status_url
            actual_json = json

        mock_requests.put.side_effect = side_effect

        self.client.status_update('http://nowhere:9000/update/status',
                                  'success', revision_id='some-revision-id')

        self.assertEquals(actual_status_url,
                          'http://nowhere:9000/update/status')
        self.assertEquals(actual_json, {
            'status': 'success',
            'revision_id': 'some-revision-id',
        })

    @patch('swh.deposit.injection.client.requests')
    @istest
    def status_update_with_no_revision_id(self, mock_requests):
        """Reading metadata can fail for some reasons

        """
        def side_effect(status_url, json):
            global actual_status_url, actual_json
            actual_status_url = status_url
            actual_json = json

        mock_requests.put.side_effect = side_effect

        self.client.status_update('http://nowhere:9000/update/status',
                                  'failure')

        self.assertEquals(actual_status_url,
                          'http://nowhere:9000/update/status')
        self.assertEquals(actual_json, {
            'status': 'failure',
        })
