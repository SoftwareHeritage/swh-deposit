# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.urlresolvers import reverse
from io import BytesIO
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.models import Deposit, DepositRequest
from swh.deposit.parsers import parse_xml

from ..common import BasicTestCase, WithAuthTestCase


class DepositMultipartTestCase(APITestCase, WithAuthTestCase, BasicTestCase):
    """Post multipart deposit scenario

    """
    def setUp(self):
        super().setUp()

        self.data_atom_entry_ok = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom"
        xmlns:dcterms="http://purl.org/dc/terms/">
    <title>Title</title>
    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
    <updated>2005-10-07T17:17:08Z</updated>
    <author><name>Contributor</name></author>
    <summary type="text">The abstract</summary>

    <!-- some embedded metadata -->
    <dcterms:abstract>The abstract</dcterms:abstract>
    <dcterms:accessRights>Access Rights</dcterms:accessRights>
    <dcterms:alternative>Alternative Title</dcterms:alternative>
    <dcterms:available>Date Available</dcterms:available>
    <dcterms:bibliographicCitation>Bibliographic Citation</dcterms:bibliographicCitation>  # noqa
    <dcterms:contributor>Contributor</dcterms:contributor>
    <dcterms:description>Description</dcterms:description>
    <dcterms:hasPart>Has Part</dcterms:hasPart>
    <dcterms:hasVersion>Has Version</dcterms:hasVersion>
    <dcterms:identifier>Identifier</dcterms:identifier>
    <dcterms:isPartOf>Is Part Of</dcterms:isPartOf>
    <dcterms:publisher>Publisher</dcterms:publisher>
    <dcterms:references>References</dcterms:references>
    <dcterms:rightsHolder>Rights Holder</dcterms:rightsHolder>
    <dcterms:source>Source</dcterms:source>
    <dcterms:title>Title</dcterms:title>
    <dcterms:type>Type</dcterms:type>

</entry>"""

        self.data_atom_entry_update_in_place = """<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom"
        xmlns:dcterms="http://purl.org/dc/terms/">
    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa7b</id>
    <dcterms:title>Title</dcterms:title>
    <dcterms:type>Type</dcterms:type>
</entry>"""

    def test_post_deposit_multipart(self):
        """one multipart deposit should be accepted

        """
        # given
        url = reverse('upload', args=[self.username])

        # from django.core.files import uploadedfile
        data_atom_entry = self.data_atom_entry_ok

        archive_content = b'some content representing archive'
        archive = InMemoryUploadedFile(
            BytesIO(archive_content),
            field_name='archive0',
            name='archive0',
            content_type='application/zip',
            size=len(archive_content),
            charset=None)

        atom_entry = InMemoryUploadedFile(
            BytesIO(data_atom_entry),
            field_name='atom0',
            name='atom0',
            content_type='application/atom+xml; charset="utf-8"',
            size=len(data_atom_entry),
            charset='utf-8')

        external_id = 'external-id'
        id1 = hashlib.sha1(archive_content).hexdigest()

        # when
        response = self.client.post(
            url,
            format='multipart',
            data={
                'archive': archive,
                'atom_entry': atom_entry,
            },
            # + headers
            HTTP_IN_PROGRESS='false',
            HTTP_SLUG=external_id)

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, 'ready')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.type, self.type)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_requests = DepositRequest.objects.filter(deposit=deposit)
        self.assertEquals(len(deposit_requests), 2)
        for deposit_request in deposit_requests:
            self.assertEquals(deposit_request.deposit, deposit)
            if deposit_request.type.name == 'archive':
                self.assertEquals(deposit_request.metadata['archive'], {
                    'id': id1,
                    'name': 'archive0',
                })
            else:
                self.assertEquals(
                    deposit_request.metadata[
                        '{http://www.w3.org/2005/Atom}id'],
                    'urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a')

    def test_post_deposit_multipart_put_to_replace_metadata(self):
        """One multipart deposit followed by a metadata update should be
           accepted

        """
        # given
        url = reverse('upload', args=[self.username])

        data_atom_entry = self.data_atom_entry_ok

        archive_content = b'some content representing archive'
        archive = InMemoryUploadedFile(
            BytesIO(archive_content),
            field_name='archive0',
            name='archive0',
            content_type='application/zip',
            size=len(archive_content),
            charset=None)

        atom_entry = InMemoryUploadedFile(
            BytesIO(data_atom_entry),
            field_name='atom0',
            name='atom0',
            content_type='application/atom+xml; charset="utf-8"',
            size=len(data_atom_entry),
            charset='utf-8')

        external_id = 'external-id'
        id1 = hashlib.sha1(archive_content).hexdigest()

        # when
        response = self.client.post(
            url,
            format='multipart',
            data={
                'archive': archive,
                'atom_entry': atom_entry,
            },
            # + headers
            HTTP_IN_PROGRESS='true',
            HTTP_SLUG=external_id)

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, 'partial')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.type, self.type)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_requests = DepositRequest.objects.filter(deposit=deposit)

        self.assertEquals(len(deposit_requests), 2)
        for deposit_request in deposit_requests:
            self.assertEquals(deposit_request.deposit, deposit)
            if deposit_request.type.name == 'archive':
                self.assertEquals(deposit_request.metadata['archive'], {
                    'id': id1,
                    'name': 'archive0',
                })
            else:
                self.assertEquals(
                    deposit_request.metadata[
                        '{http://www.w3.org/2005/Atom}id'],
                    'urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a')

        replace_metadata_uri = response._headers['location'][1]
        response = self.client.put(
            replace_metadata_uri,
            content_type='application/atom+xml;type=entry',
            data=self.data_atom_entry_update_in_place,
            HTTP_IN_PROGRESS='false')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # deposit_id did not change
        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, 'ready')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.type, self.type)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_requests = DepositRequest.objects.filter(deposit=deposit)
        self.assertEquals(len(deposit_requests), 2)
        for deposit_request in deposit_requests:
            self.assertEquals(deposit_request.deposit, deposit)
            if deposit_request.type.name == 'archive':
                self.assertEquals(deposit_request.metadata, {
                    'archive': {
                        'id': id1,
                        'name': 'archive0',
                    },
                })
            else:
                self.assertEquals(
                    deposit_request.metadata[
                        '{http://www.w3.org/2005/Atom}id'],
                    'urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa7b')

    # FAILURE scenarios

    def test_post_deposit_multipart_only_archive_and_atom_entry(self):
        """Multipart deposit only accepts one archive and one atom+xml"""
        # given
        url = reverse('upload', args=[self.username])

        # from django.core.files import uploadedfile

        archive_content = b'some content representing archive'
        archive = InMemoryUploadedFile(BytesIO(archive_content),
                                       field_name='archive0',
                                       name='archive0',
                                       content_type='application/zip',
                                       size=len(archive_content),
                                       charset=None)

        other_archive_content = b"some-other-content"
        other_archive = InMemoryUploadedFile(BytesIO(other_archive_content),
                                             field_name='atom0',
                                             name='atom0',
                                             content_type='application/zip',
                                             size=len(other_archive_content),
                                             charset='utf-8')

        # when
        response = self.client.post(
            url,
            format='multipart',
            data={
                'archive': archive,
                'atom_entry': other_archive,
            },
            # + headers
            HTTP_IN_PROGRESS='false',
            HTTP_SLUG='external-id')

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        # when
        archive.seek(0)
        response = self.client.post(
            url,
            format='multipart',
            data={
                'archive': archive,
            },
            # + headers
            HTTP_IN_PROGRESS='false',
            HTTP_SLUG='external-id')

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)