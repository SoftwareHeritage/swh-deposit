# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib

from django.core.urlresolvers import reverse
from io import BytesIO
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.config import COL_IRI, EDIT_SE_IRI, DEPOSIT_STATUS_REJECTED
from swh.deposit.config import DEPOSIT_STATUS_PARTIAL
from swh.deposit.config import DEPOSIT_STATUS_LOAD_SUCCESS
from swh.deposit.config import DEPOSIT_STATUS_LOAD_FAILURE
from swh.deposit.models import Deposit, DepositClient, DepositCollection
from swh.deposit.parsers import parse_xml

from ..common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine


class DepositNoAuthCase(APITestCase, BasicTestCase):
    """Deposit access are protected with basic authentication.

    """
    def test_post_will_fail_with_401(self):
        """Without authentication, endpoint refuses access with 401 response

        """
        url = reverse(COL_IRI, args=[self.collection.name])

        # when
        response = self.client.post(url)

        # then
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class DepositFailuresTest(APITestCase, WithAuthTestCase, BasicTestCase,
                          CommonCreationRoutine):
    """Deposit access are protected with basic authentication.

    """
    def setUp(self):
        super().setUp()
        # Add another user
        _collection2 = DepositCollection(name='some')
        _collection2.save()
        _user = DepositClient.objects.create_user(username='user',
                                                  password='user')
        _user.collections = [_collection2.id]
        self.collection2 = _collection2

    def test_access_to_another_user_collection_is_forbidden(self):
        """Access to another user collection should return a 403

        """
        url = reverse(COL_IRI, args=[self.collection2.name])
        response = self.client.post(url)
        self.assertEqual(response.status_code,
                         status.HTTP_403_FORBIDDEN)
        self.assertRegex(response.content.decode('utf-8'),
                         'Client hal cannot access collection %s' % (
                             self.collection2.name, ))

    def test_delete_on_col_iri_not_supported(self):
        """Delete on col iri should return a 405 response

        """
        url = reverse(COL_IRI, args=[self.collection.name])
        response = self.client.delete(url)
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertRegex(response.content.decode('utf-8'),
                         'DELETE method is not supported on this endpoint')

    def create_deposit_with_rejection_status(self):
        url = reverse(COL_IRI, args=[self.collection.name])

        data = b'some data which is clearly not a zip file'
        md5sum = hashlib.md5(data).hexdigest()
        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=data,
            # + headers
            CONTENT_LENGTH=len(data),
            # other headers needs HTTP_ prefix to be taken into account
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_content = parse_xml(BytesIO(response.content))
        actual_state = response_content['deposit_status']
        self.assertEqual(actual_state, DEPOSIT_STATUS_REJECTED)

    def test_act_on_deposit_rejected_is_not_permitted(self):
        deposit_id = self.create_deposit_with_status(DEPOSIT_STATUS_REJECTED)

        deposit = Deposit.objects.get(pk=deposit_id)
        assert deposit.status == DEPOSIT_STATUS_REJECTED

        response = self.client.post(
            reverse(EDIT_SE_IRI, args=[self.collection.name, deposit_id]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data1,
            HTTP_SLUG='external-id')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertRegex(
            response.content.decode('utf-8'),
            "You can only act on deposit with status &#39;%s&#39;" % (
                DEPOSIT_STATUS_PARTIAL, ))

    def test_add_deposit_with_parent(self):
        # given multiple deposit already loaded
        deposit_id = self.create_deposit_with_status(
            status=DEPOSIT_STATUS_LOAD_SUCCESS,
            external_id='some-external-id')

        deposit1 = Deposit.objects.get(pk=deposit_id)
        self.assertIsNotNone(deposit1)
        self.assertEqual(deposit1.external_id, 'some-external-id')
        self.assertEqual(deposit1.status, DEPOSIT_STATUS_LOAD_SUCCESS)

        deposit_id2 = self.create_deposit_with_status(
            status=DEPOSIT_STATUS_LOAD_SUCCESS,
            external_id='some-external-id')

        deposit2 = Deposit.objects.get(pk=deposit_id2)
        self.assertIsNotNone(deposit2)
        self.assertEqual(deposit2.external_id, 'some-external-id')
        self.assertEqual(deposit2.status, DEPOSIT_STATUS_LOAD_SUCCESS)

        deposit_id3 = self.create_deposit_with_status(
            status=DEPOSIT_STATUS_LOAD_FAILURE,
            external_id='some-external-id')

        deposit3 = Deposit.objects.get(pk=deposit_id3)
        self.assertIsNotNone(deposit3)
        self.assertEqual(deposit3.external_id, 'some-external-id')
        self.assertEqual(deposit3.status, DEPOSIT_STATUS_LOAD_FAILURE)

        # when
        deposit_id3 = self.create_simple_deposit_partial(
            external_id='some-external-id')

        # then
        deposit4 = Deposit.objects.get(pk=deposit_id3)

        self.assertIsNotNone(deposit4)
        self.assertEqual(deposit4.external_id, 'some-external-id')
        self.assertEqual(deposit4.status, DEPOSIT_STATUS_PARTIAL)
        self.assertEqual(deposit4.parent, deposit2)
