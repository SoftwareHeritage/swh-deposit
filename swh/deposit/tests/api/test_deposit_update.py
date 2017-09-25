# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib

from django.core.urlresolvers import reverse
from io import BytesIO
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.models import Deposit, DepositRequest
from ..common import BasicTestCase, WithAuthTestCase
from ...parsers import parse_xml
from ...config import EM_IRI, EDIT_SE_IRI, COL_IRI


class CommonData:
    def _create_deposit_partial(self):
        response = self.client.post(
            reverse(COL_IRI, args=[self.username]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0,
            HTTP_IN_PROGRESS='true')

        # then
        assert response.status_code == status.HTTP_201_CREATED
        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']
        return deposit_id

    def _update_deposit_with_status(self, deposit_id, status_partial=False):
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

    def _create_deposit_ready(self):
        """Creating a deposit"""
        deposit_id = self._create_deposit_partial()
        deposit_id = self._update_deposit_with_status(deposit_id)
        return deposit_id

    def _create_deposit_complex_partial(self):
        """Creating a deposit"""
        deposit_id = self._create_deposit_partial()
        deposit_id = self._update_deposit_with_status(
            deposit_id, status_partial=True)
        return deposit_id


class DepositUpdateFailuresTest(APITestCase, WithAuthTestCase, BasicTestCase,
                                CommonData):
    """Try and post/put deposit on unknown ones

    """
    def setUp(self):
        super().setUp()
        self.atom_entry_data0 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <external_identifier>%s</external_identifier>
</entry>"""

    def test_add_metadata_to_unknown_collection(self):
        """Replacing metadata to unknown deposit should return a 404 response

        """
        url = reverse(EDIT_SE_IRI,
                      args=['unknown', 999]),
        response = self.client.post(
            url,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_metadata_to_unknown_deposit(self):
        """Replacing metadata to unknown deposit should return a 404 response

        """
        url = reverse(EDIT_SE_IRI,
                      args=[self.username, 999]),
        response = self.client.post(
            url,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_replace_metadata_to_unknown_deposit(self):
        """Adding metadata to unknown deposit should return a 404 response"""
        url = reverse(EDIT_SE_IRI,
                      args=[self.username, 999]),
        response = self.client.put(
            url,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_archive_to_unknown_deposit(self):
        """Adding metadata to unknown deposit should return a 404 response"""
        url = reverse(EM_IRI,
                      args=[self.username, 999]),
        response = self.client.post(
            url,
            content_type='application/zip',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_replace_archive_to_unknown_deposit(self):
        """Replacing archive to unknown deposit should return a 404 response"""
        url = reverse(EM_IRI,
                      args=[self.username, 999]),
        response = self.client.put(
            url,
            content_type='application/zip',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_metadata_to_em_iri_failure(self):
        """Add archive with wrong content type should return a 400 response"""
        deposit_id = self._create_deposit_ready()

        update_uri = reverse(EM_IRI, args=[self.username, deposit_id])
        response = self.client.put(
            update_uri,
            content_type='application/binary',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_metadata_to_em_iri_failure(self):
        """Update archive with wrong content type should return 400 response"""
        # given
        deposit_id = self._create_deposit_ready()
        # when
        update_uri = reverse(EM_IRI, args=[self.username, deposit_id])
        response = self.client.put(
            update_uri,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0)
        # then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DepositUpdateTest(APITestCase, WithAuthTestCase, BasicTestCase,
                        CommonData):

    def setUp(self):
        super().setUp()
        self.atom_entry_data0 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <external_identifier>%s</external_identifier>
</entry>"""

    def test_delete_archive_on_partial_deposit_works(self):
        """Removing partial deposit's archive should return a 204 response

        """
        # given
        deposit_id = self._create_deposit_complex_partial()
        deposit = Deposit.objects.get(pk=deposit_id)
        deposit_requests = DepositRequest.objects.filter(deposit=deposit)

        self.assertEquals(len(deposit_requests), 2)
        for dr in deposit_requests:
            if dr.type.name == 'archive':
                continue
            elif dr.type.name == 'metadata':
                continue
            else:
                self.fail('only archive and metadata type should exist '
                          'in this test context')

        # when
        update_uri = reverse(EM_IRI, args=[self.username, deposit_id])
        response = self.client.delete(update_uri)
        # then
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        deposit = Deposit.objects.get(pk=deposit_id)
        requests = list(DepositRequest.objects.filter(deposit=deposit))

        self.assertEquals(len(requests), 1)
        self.assertEquals(requests[0].type.name, 'metadata')

    def test_delete_archive_on_undefined_deposit_fails(self):
        """Delete undefined deposit returns a 404 response

        """
        # when
        update_uri = reverse(EM_IRI, args=[self.username, 999])
        response = self.client.delete(update_uri)
        # then
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_archive_on_non_partial_deposit_fails(self):
        """Delete !partial status deposit should return a 400 response"""
        deposit_id = self._create_deposit_ready()
        deposit = Deposit.objects.get(pk=deposit_id)
        assert deposit.status == 'ready'

        # when
        update_uri = reverse(EM_IRI, args=[self.username, deposit_id])
        response = self.client.delete(update_uri)
        # then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertIsNotNone(deposit)

    def test_delete_partial_deposit_works(self):
        """Delete deposit should return a 204 response

        """
        # given
        deposit_id = self._create_deposit_partial()
        deposit = Deposit.objects.get(pk=deposit_id)
        assert deposit.id == deposit_id

        # when
        url = reverse(EDIT_SE_IRI, args=[self.username, deposit_id])
        response = self.client.delete(url)
        # then
        self.assertEqual(response.status_code,
                         status.HTTP_204_NO_CONTENT)
        deposit_requests = list(DepositRequest.objects.filter(deposit=deposit))
        self.assertEquals(deposit_requests, [])
        deposits = list(Deposit.objects.filter(pk=deposit_id))
        self.assertEquals(deposits, [])

    def test_delete_on_edit_se_iri_cannot_delete_non_partial_deposit(self):
        """Delete !partial deposit should return a 400 response

        """
        # given
        deposit_id = self._create_deposit_ready()
        deposit = Deposit.objects.get(pk=deposit_id)
        assert deposit.id == deposit_id

        # when
        url = reverse(EDIT_SE_IRI, args=[self.username, deposit_id])
        response = self.client.delete(url)
        # then
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)
        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertIsNotNone(deposit)
