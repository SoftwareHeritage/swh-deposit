# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import base64
import hashlib
import os
import shutil

from django.core.urlresolvers import reverse
from django.test import TestCase
from io import BytesIO
from rest_framework import status

from swh.deposit.config import COL_IRI, EM_IRI
from swh.deposit.models import DepositClient, DepositCollection
from swh.deposit.models import DepositRequestType
from swh.deposit.parsers import parse_xml
from swh.deposit.settings.testing import MEDIA_ROOT


class BasicTestCase(TestCase):
    """Mixin intended for data setup purposes (user, collection, etc...)

    """
    def setUp(self):
        """Define the test client and other test variables."""
        super().setUp()
        # expanding diffs in tests
        self.maxDiff = None

        # basic minimum test data
        deposit_request_types = {}
        # Add deposit request types
        for deposit_request_type in ['archive', 'metadata']:
            drt = DepositRequestType(name=deposit_request_type)
            drt.save()
            deposit_request_types[deposit_request_type] = drt

        _name = 'hal'
        # set collection up
        _collection = DepositCollection(name=_name)
        _collection.save()
        # set user/client up
        _client = DepositClient.objects.create_user(username=_name,
                                                    password=_name)
        _client.collections = [_collection.id]
        _client.save()

        self.collection = _collection
        self.user = _client
        self.username = _name
        self.userpass = _name

        self.deposit_request_types = deposit_request_types

    def tearDown(self):
        # Clean up uploaded files in temporary directory (tests have
        # their own media root folder)
        if os.path.exists(MEDIA_ROOT):
            for d in os.listdir(MEDIA_ROOT):
                shutil.rmtree(os.path.join(MEDIA_ROOT, d))


class WithAuthTestCase(TestCase):
    """Mixin intended for testing the api with basic authentication.

    """
    def setUp(self):
        super().setUp()
        _token = '%s:%s' % (self.username, self.userpass)
        token = base64.b64encode(_token.encode('utf-8'))
        authorization = 'Basic %s' % token.decode('utf-8')
        self.client.credentials(HTTP_AUTHORIZATION=authorization)

    def tearDown(self):
        super().tearDown()
        self.client.credentials()


class CommonCreationRoutine(TestCase):
    """Mixin class to share initialization routine.


    cf:
        `class`:test_deposit_update.DepositReplaceExistingDataTest
        `class`:test_deposit_update.DepositUpdateDepositWithNewDataTest
        `class`:test_deposit_update.DepositUpdateFailuresTest
        `class`:test_deposit_delete.DepositDeleteTest

    """
    def setUp(self):
        super().setUp()

        self.atom_entry_data0 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <external_identifier>some-external-id</external_identifier>
</entry>"""

    def create_simple_deposit_partial(self):
        """Create a simple deposit (1 request) in `partial` state and returns
        its new identifier.

        Returns:
            deposit id

        """
        response = self.client.post(
            reverse(COL_IRI, args=[self.username]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0,
            HTTP_SLUG='external-id',
            HTTP_IN_PROGRESS='true')

        # then
        assert response.status_code == status.HTTP_201_CREATED
        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']
        return deposit_id

    def _update_deposit_with_status(self, deposit_id, status_partial=False):
        """Add to a given deposit another archive and update its current
           status to `ready` (by default).

        Returns:
            deposit id

        """
        # add an archive
        data_text = b'some content'
        md5sum = hashlib.md5(data_text).hexdigest()

        # when
        response = self.client.post(
            reverse(EM_IRI, args=[self.username, deposit_id]),
            content_type='application/zip',  # as zip
            data=data_text,
            # + headers
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS=status_partial,
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        assert response.status_code == status.HTTP_201_CREATED
        return deposit_id

    def create_deposit_ready(self):
        """Create a complex deposit (2 requests) in status `ready`.

        """
        deposit_id = self.create_simple_deposit_partial()
        deposit_id = self._update_deposit_with_status(deposit_id)
        return deposit_id

    def create_deposit_partial(self):
        """Create a complex deposit (2 requests) in status `partial`.

        """
        deposit_id = self.create_simple_deposit_partial()
        deposit_id = self._update_deposit_with_status(
            deposit_id, status_partial=True)
        return deposit_id
