# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.core.urlresolvers import reverse
from io import BytesIO
from rest_framework import status
from rest_framework.test import APITestCase

from ..common import BasicTestCase, WithAuthTestCase
from ...parsers import parse_xml
from ...config import EM_IRI, EDIT_SE_IRI, COL_IRI


class DepositUpdateFailuresTest(APITestCase, WithAuthTestCase, BasicTestCase):
    """Try and post/put deposit on unknown ones

    """
    def setUp(self):
        super().setUp()
        self.atom_entry_data0 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <external_identifier>%s</external_identifier>
</entry>"""

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

    def _create_deposit(self):
        """Creating a deposit"""
        response = self.client.post(
            reverse(COL_IRI, args=[self.username]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0,
            HTTP_IN_PROGRESS='false')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']

        return deposit_id

    def test_post_metadata_to_em_iri_failure(self):
        """Post query with wrong content type should return a 400 response"""
        deposit_id = self._create_deposit()

        update_uri = reverse(EM_IRI, args=[self.username, deposit_id])
        response = self.client.put(
            update_uri,
            content_type='application/binary',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_metadata_to_em_iri_failure(self):
        """Put query with wrong content type should return a 400 response"""
        # given
        deposit_id = self._create_deposit()
        # when
        update_uri = reverse(EM_IRI, args=[self.username, deposit_id])
        response = self.client.put(
            update_uri,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0)
        # then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
