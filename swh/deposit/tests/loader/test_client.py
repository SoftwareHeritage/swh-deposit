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

from swh.deposit.loader.client import DepositClient

from .common import CLIENT_TEST_CONFIG


class StreamedResponse:
    """Streamed response facsimile

    """
    def __init__(self, ok, stream):
        self.ok = ok
        self.stream = stream

    def iter_content(self):
        yield from self.stream


class FakeRequestClientGet:
    """Fake request client dedicated to get method calls.

    """
    def __init__(self, response):
        self.response = response

    def get(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self.response


@attr('fs')
class DepositClientReadArchiveTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.temporary_directory = tempfile.mkdtemp(dir='/tmp')

    def tearDown(self):
        super().setUp()
        shutil.rmtree(self.temporary_directory)

    @istest
    def archive_get(self):
        """Reading archive should write data in temporary directory

        """
        stream_content = [b"some", b"streamed", b"response"]
        response = StreamedResponse(
            ok=True,
            stream=(s for s in stream_content))
        _client = FakeRequestClientGet(response)

        deposit_client = DepositClient(config=CLIENT_TEST_CONFIG,
                                       _client=_client)

        archive_path = os.path.join(self.temporary_directory, 'test.archive')
        archive_path = deposit_client.archive_get('/some/url', archive_path)

        self.assertTrue(os.path.exists(archive_path))

        with open(archive_path, 'rb') as f:
            actual_content = f.read()

        self.assertEquals(actual_content, b''.join(stream_content))
        self.assertEquals(_client.args, ('http://nowhere:9000/some/url', ))
        self.assertEquals(_client.kwargs, {
            'stream': True
        })

    @istest
    def archive_get_with_authentication(self):
        """Reading archive should write data in temporary directory

        """
        stream_content = [b"some", b"streamed", b"response", b"for", b"auth"]
        response = StreamedResponse(
            ok=True,
            stream=(s for s in stream_content))
        _client = FakeRequestClientGet(response)

        _config = CLIENT_TEST_CONFIG.copy()
        _config['auth'] = {  # add authentication setup
            'username': 'user',
            'password': 'pass'
        }
        deposit_client = DepositClient(_config, _client=_client)

        archive_path = os.path.join(self.temporary_directory, 'test.archive')
        archive_path = deposit_client.archive_get('/some/url', archive_path)

        self.assertTrue(os.path.exists(archive_path))

        with open(archive_path, 'rb') as f:
            actual_content = f.read()

        self.assertEquals(actual_content, b''.join(stream_content))
        self.assertEquals(_client.args, ('http://nowhere:9000/some/url', ))
        self.assertEquals(_client.kwargs, {
            'stream': True,
            'auth': ('user', 'pass')
        })

    @istest
    def archive_get_can_fail(self):
        """Reading archive can fail for some reasons

        """
        response = StreamedResponse(ok=False, stream=None)
        _client = FakeRequestClientGet(response)
        deposit_client = DepositClient(config=CLIENT_TEST_CONFIG,
                                       _client=_client)

        with self.assertRaisesRegex(
                ValueError,
                'Problem when retrieving deposit archive'):
            deposit_client.archive_get('/some/url', 'some/path')


class JsonResponse:
    """Json response facsimile

    """
    def __init__(self, ok, response):
        self.ok = ok
        self.response = response

    def json(self):
        return self.response


class DepositClientReadMetadataTest(unittest.TestCase):
    @istest
    def metadata_get(self):
        """Reading archive should write data in temporary directory

        """
        expected_response = {"some": "dict"}

        response = JsonResponse(
            ok=True,
            response=expected_response)
        _client = FakeRequestClientGet(response)
        deposit_client = DepositClient(config=CLIENT_TEST_CONFIG,
                                       _client=_client)

        actual_metadata = deposit_client.metadata_get('/metadata')

        self.assertEquals(actual_metadata, expected_response)

    @istest
    def metadata_get_can_fail(self):
        """Reading metadata can fail for some reasons

        """
        _client = FakeRequestClientGet(JsonResponse(ok=False, response=None))
        deposit_client = DepositClient(config=CLIENT_TEST_CONFIG,
                                       _client=_client)
        with self.assertRaisesRegex(
                ValueError,
                'Problem when retrieving metadata at'):
            deposit_client.metadata_get('/some/metadata/url')


class FakeRequestClientPut:
    """Fake Request client dedicated to put request method calls.

    """
    args = None
    kwargs = None

    def put(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class DepositClientStatusUpdateTest(unittest.TestCase):
    @istest
    def status_update(self):
        """Update status

        """
        _client = FakeRequestClientPut()
        deposit_client = DepositClient(config=CLIENT_TEST_CONFIG,
                                       _client=_client)

        deposit_client.status_update('/update/status',
                                     'success', revision_id='some-revision-id')

        self.assertEquals(_client.args,
                          ('http://nowhere:9000/update/status', ))
        self.assertEquals(_client.kwargs, {
            'json': {
                'status': 'success',
                'revision_id': 'some-revision-id',
            }
        })

    @istest
    def status_update_with_no_revision_id(self):
        """Reading metadata can fail for some reasons

        """
        _client = FakeRequestClientPut()
        deposit_client = DepositClient(config=CLIENT_TEST_CONFIG,
                                       _client=_client)

        deposit_client.status_update('/update/status/fail', 'failure')

        self.assertEquals(_client.args,
                          ('http://nowhere:9000/update/status/fail', ))
        self.assertEquals(_client.kwargs, {
            'json': {
                'status': 'failure',
            }
        })


class DepositClientCheckTest(unittest.TestCase):
    @istest
    def check(self):
        """When check ok, this should return the deposit's status

        """
        _client = FakeRequestClientGet(
            JsonResponse(ok=True, response={'status': 'something'}))
        deposit_client = DepositClient(config=CLIENT_TEST_CONFIG,
                                       _client=_client)

        r = deposit_client.check('/check')

        self.assertEquals(_client.args,
                          ('http://nowhere:9000/check', ))
        self.assertEquals(_client.kwargs, {})
        self.assertEquals(r, 'something')

    @istest
    def check_fails(self):
        """Checking deposit can fail for some reason

        """
        _client = FakeRequestClientGet(
            JsonResponse(ok=False, response=None))
        deposit_client = DepositClient(config=CLIENT_TEST_CONFIG,
                                       _client=_client)

        with self.assertRaisesRegex(
                ValueError,
                'Problem when checking deposit'):
            deposit_client.check('/check/fails')

        self.assertEquals(_client.args,
                          ('http://nowhere:9000/check/fails', ))
        self.assertEquals(_client.kwargs, {})