# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.urlresolvers import reverse
from io import BytesIO

from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.tests import TEST_CONFIG
from swh.deposit.config import COL_IRI, EM_IRI
from swh.deposit.config import DEPOSIT_STATUS_DEPOSITED
from swh.deposit.models import Deposit, DepositRequest
from swh.deposit.parsers import parse_xml
from ..common import (
    BasicTestCase, WithAuthTestCase, create_arborescence_archive,
    FileSystemCreationRoutine
)


class DepositTestCase(APITestCase, WithAuthTestCase, BasicTestCase,
                      FileSystemCreationRoutine):
    """Try and upload one single deposit

    """
    def setUp(self):
        super().setUp()

        self.atom_entry_data0 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <title>Awesome Compiler</title>
    <client>hal</client>
    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
    <external_identifier>%s</external_identifier>
    <updated>2017-10-07T15:17:08Z</updated>
    <author>some awesome author</author>
    <applicationCategory>something</applicationCategory>
    <name>awesome-compiler</name>
    <description>This is an awesome compiler destined to
awesomely compile stuff
and other stuff</description>
    <keywords>compiler,programming,language</keywords>
    <dateCreated>2005-10-07T17:17:08Z</dateCreated>
    <datePublished>2005-10-07T17:17:08Z</datePublished>
    <releaseNotes>release note</releaseNotes>
    <relatedLink>related link</relatedLink>
    <sponsor></sponsor>
    <programmingLanguage>Awesome</programmingLanguage>
    <codeRepository>https://hoster.org/awesome-compiler</codeRepository>
    <operatingSystem>GNU/Linux</operatingSystem>
    <version>0.0.1</version>
    <developmentStatus>running</developmentStatus>
    <runtimePlatform>all</runtimePlatform>
</entry>"""

        self.atom_entry_data1 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <client>hal</client>
    <id>urn:uuid:2225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
    <updated>2017-10-07T15:17:08Z</updated>
    <author>some awesome author</author>
    <applicationCategory>something</applicationCategory>
    <name>awesome-compiler</name>
    <description>This is an awesome compiler destined to
awesomely compile stuff
and other stuff</description>
    <keywords>compiler,programming,language</keywords>
    <dateCreated>2005-10-07T17:17:08Z</dateCreated>
    <datePublished>2005-10-07T17:17:08Z</datePublished>
    <releaseNotes>release note</releaseNotes>
    <relatedLink>related link</relatedLink>
    <sponsor></sponsor>
    <programmingLanguage>Awesome</programmingLanguage>
    <codeRepository>https://hoster.org/awesome-compiler</codeRepository>
    <operatingSystem>GNU/Linux</operatingSystem>
    <version>0.0.1</version>
    <developmentStatus>running</developmentStatus>
    <runtimePlatform>all</runtimePlatform>
</entry>"""

        self.atom_entry_data2 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <external_identifier>%s</external_identifier>
</entry>"""

        self.atom_entry_data_empty_body = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom"></entry>"""

        self.atom_entry_data3 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <something>something</something>
</entry>"""

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

    def test_post_deposit_binary_without_slug_header_is_bad_request(self):
        """Posting a binary deposit without slug header should return 400

        """
        url = reverse(COL_IRI, args=[self.collection.name])

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=self.archive['data'],
            # + headers
            CONTENT_LENGTH=self.archive['length'],
            HTTP_CONTENT_MD5=self.archive['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        self.assertIn(b'Missing SLUG header', response.content)
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)

    def test_post_deposit_binary_upload_final_and_status_check(self):
        """Binary upload with correct headers should return 201 with receipt

        """
        # given
        url = reverse(COL_IRI, args=[self.collection.name])

        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=self.archive['data'],
            # + headers
            CONTENT_LENGTH=self.archive['length'],
            # other headers needs HTTP_ prefix to be taken into account
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=self.archive['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_DISPOSITION='attachment; filename=%s' % (
                self.archive['name'], ))

        # then
        response_content = parse_xml(BytesIO(response.content))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        deposit_id = response_content['deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_DEPOSITED)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertEqual(deposit_request.deposit, deposit)
        self.assertRegex(deposit_request.archive.name, self.archive['name'])
        self.assertIsNone(deposit_request.metadata)
        self.assertIsNone(deposit_request.raw_metadata)

        response_content = parse_xml(BytesIO(response.content))
        self.assertEqual(response_content['deposit_archive'],
                         self.archive['name'])
        self.assertEqual(int(response_content['deposit_id']),
                         deposit.id)
        self.assertEqual(response_content['deposit_status'],
                         deposit.status)

        edit_se_iri = reverse('edit_se_iri',
                              args=[self.collection.name, deposit.id])

        self.assertEqual(response._headers['location'],
                         ('Location', 'http://testserver' + edit_se_iri))

    def test_post_deposit_binary_upload_supports_zip_or_tar(self):
        """Binary upload with content-type not in [zip,x-tar] should return 415

        """
        # given
        url = reverse(COL_IRI, args=[self.collection.name])

        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/octet-stream',
            data=self.archive['data'],
            # + headers
            CONTENT_LENGTH=self.archive['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=self.archive['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

    def test_post_deposit_binary_fails_if_unsupported_packaging_header(
            self):
        """Bin deposit without supported content_disposition header returns 400

        """
        # given
        url = reverse(COL_IRI, args=[self.collection.name])

        external_id = 'some-external-id'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',
            data=self.archive['data'],
            # + headers
            CONTENT_LENGTH=self.archive['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=self.archive['md5sum'],
            HTTP_PACKAGING='something-unsupported',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)
        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

    def test_post_deposit_binary_upload_fail_if_no_content_disposition_header(
            self):
        """Binary upload without content_disposition header should return 400

        """
        # given
        url = reverse(COL_IRI, args=[self.collection.name])

        external_id = 'some-external-id'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',
            data=self.archive['data'],
            # + headers
            CONTENT_LENGTH=self.archive['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=self.archive['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false')

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)
        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

    def test_post_deposit_mediation_not_supported(self):
        """Binary upload with mediation should return a 412 response

        """
        # given
        url = reverse(COL_IRI, args=[self.collection.name])

        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',
            data=self.archive['data'],
            # + headers
            CONTENT_LENGTH=self.archive['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=self.archive['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_ON_BEHALF_OF='someone',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_412_PRECONDITION_FAILED)

        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

    def test_post_deposit_binary_upload_fail_if_upload_size_limit_exceeded(
            self):
        """Binary upload must not exceed the limit set up...

        """
        # given
        url = reverse(COL_IRI, args=[self.collection.name])

        archive = create_arborescence_archive(
            self.root_path, 'archive2', 'file2', b'some content in file',
            up_to_size=TEST_CONFIG['max_upload_size'])

        external_id = 'some-external-id'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',
            data=archive['data'],
            # + headers
            CONTENT_LENGTH=archive['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=archive['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        self.assertRegex(response.content, b'Upload size limit exceeded')

        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

    def test_post_deposit_2_post_2_different_deposits(self):
        """2 posting deposits should return 2 different 201 with receipt

        """
        url = reverse(COL_IRI, args=[self.collection.name])

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=self.archive['data'],
            # + headers
            CONTENT_LENGTH=self.archive['length'],
            HTTP_SLUG='some-external-id-1',
            HTTP_CONTENT_MD5=self.archive['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content['deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)

        deposits = Deposit.objects.all()
        self.assertEqual(len(deposits), 1)
        self.assertEqual(deposits[0], deposit)

        # second post
        response = self.client.post(
            url,
            content_type='application/x-tar',  # as zip
            data=self.archive['data'],
            # + headers
            CONTENT_LENGTH=self.archive['length'],
            HTTP_SLUG='another-external-id',
            HTTP_CONTENT_MD5=self.archive['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename1')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id2 = response_content['deposit_id']

        deposit2 = Deposit.objects.get(pk=deposit_id2)

        self.assertNotEqual(deposit, deposit2)

        deposits = Deposit.objects.all().order_by('id')
        self.assertEqual(len(deposits), 2)
        self.assertEqual(list(deposits), [deposit, deposit2])

    def test_post_deposit_binary_and_post_to_add_another_archive(self):
        """Updating a deposit should return a 201 with receipt

        """
        # given
        url = reverse(COL_IRI, args=[self.collection.name])

        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=self.archive['data'],
            # + headers
            CONTENT_LENGTH=self.archive['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=self.archive['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='true',
            HTTP_CONTENT_DISPOSITION='attachment; filename=%s' % (
                self.archive['name'], ))

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content['deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, 'partial')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertEqual(deposit_request.deposit, deposit)
        self.assertEqual(deposit_request.type.name, 'archive')
        self.assertRegex(deposit_request.archive.name, self.archive['name'])

        # 2nd archive to upload
        archive2 = create_arborescence_archive(
            self.root_path, 'archive2', 'file2', b'some other content in file')

        # uri to update the content
        update_uri = reverse(EM_IRI, args=[self.collection.name, deposit_id])

        # adding another archive for the deposit and finalizing it
        response = self.client.post(
            update_uri,
            content_type='application/zip',  # as zip
            data=archive2['data'],
            # + headers
            CONTENT_LENGTH=archive2['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=archive2['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_CONTENT_DISPOSITION='attachment; filename=%s' % (
                archive2['name']))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_content = parse_xml(BytesIO(response.content))

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_DEPOSITED)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_requests = list(DepositRequest.objects.filter(deposit=deposit).
                                order_by('id'))

        # 2 deposit requests for the same deposit
        self.assertEqual(len(deposit_requests), 2)
        self.assertEqual(deposit_requests[0].deposit, deposit)
        self.assertEqual(deposit_requests[0].type.name, 'archive')
        self.assertRegex(deposit_requests[0].archive.name,
                         self.archive['name'])

        self.assertEqual(deposit_requests[1].deposit, deposit)
        self.assertEqual(deposit_requests[1].type.name, 'archive')
        self.assertRegex(deposit_requests[1].archive.name,
                         archive2['name'])

        # only 1 deposit in db
        deposits = Deposit.objects.all()
        self.assertEqual(len(deposits), 1)

    def test_post_deposit_then_post_or_put_is_refused_when_status_ready(self):
        """Updating a deposit with status 'ready' should return a 400

        """
        url = reverse(COL_IRI, args=[self.collection.name])

        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=self.archive['data'],
            # + headers
            CONTENT_LENGTH=self.archive['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=self.archive['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content['deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_DEPOSITED)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertEqual(deposit_request.deposit, deposit)
        self.assertRegex(deposit_request.archive.name, 'filename0')

        # updating/adding is forbidden

        # uri to update the content
        edit_se_iri = reverse(
            'edit_se_iri', args=[self.collection.name, deposit_id])
        em_iri = reverse(
            'em_iri', args=[self.collection.name, deposit_id])

        # Testing all update/add endpoint should fail
        # since the status is ready

        archive2 = create_arborescence_archive(
            self.root_path, 'archive2', 'file2', b'some content in file 2')

        # replacing file is no longer possible since the deposit's
        # status is ready
        r = self.client.put(
            em_iri,
            content_type='application/zip',
            data=archive2['data'],
            CONTENT_LENGTH=archive2['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=archive2['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

        # adding file is no longer possible since the deposit's status
        # is ready
        r = self.client.post(
            em_iri,
            content_type='application/zip',
            data=archive2['data'],
            CONTENT_LENGTH=archive2['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=archive2['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

        # replacing metadata is no longer possible since the deposit's
        # status is ready
        r = self.client.put(
            edit_se_iri,
            content_type='application/atom+xml;type=entry',
            data=self.data_atom_entry_ok,
            CONTENT_LENGTH=len(self.data_atom_entry_ok),
            HTTP_SLUG=external_id)

        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

        # adding new metadata is no longer possible since the
        # deposit's status is ready
        r = self.client.post(
            edit_se_iri,
            content_type='application/atom+xml;type=entry',
            data=self.data_atom_entry_ok,
            CONTENT_LENGTH=len(self.data_atom_entry_ok),
            HTTP_SLUG=external_id)

        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

        archive_content = b'some content representing archive'
        archive = InMemoryUploadedFile(
            BytesIO(archive_content),
            field_name='archive0',
            name='archive0',
            content_type='application/zip',
            size=len(archive_content),
            charset=None)

        atom_entry = InMemoryUploadedFile(
            BytesIO(self.data_atom_entry_ok),
            field_name='atom0',
            name='atom0',
            content_type='application/atom+xml; charset="utf-8"',
            size=len(self.data_atom_entry_ok),
            charset='utf-8')

        # replacing multipart metadata is no longer possible since the
        # deposit's status is ready
        r = self.client.put(
            edit_se_iri,
            format='multipart',
            data={
                'archive': archive,
                'atom_entry': atom_entry,
            })

        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

        # adding new metadata is no longer possible since the
        # deposit's status is ready
        r = self.client.post(
            edit_se_iri,
            format='multipart',
            data={
                'archive': archive,
                'atom_entry': atom_entry,
            })

        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
