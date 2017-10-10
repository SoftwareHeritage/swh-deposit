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

from swh.deposit.config import COL_IRI, EM_IRI
from swh.deposit.models import Deposit, DepositRequest
from swh.deposit.parsers import parse_xml
from ..common import BasicTestCase, WithAuthTestCase


class DepositNoAuthCase(APITestCase, BasicTestCase):
    """Deposit access are protected with basic authentication.

    """
    def test_post_will_fail_with_401(self):
        """Without authentication, endpoint refuses access with 401 response

        """
        url = reverse(COL_IRI, args=[self.username])
        data_text = b'some content'
        md5sum = hashlib.md5(data_text).hexdigest()

        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=data_text,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class DepositTestCase(APITestCase, WithAuthTestCase, BasicTestCase):
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

    def test_post_deposit_binary_upload_final_and_status_check(self):
        """Binary upload should be accepted

        """
        # given
        url = reverse(COL_IRI, args=[self.username])
        data_text = b'some content'
        md5sum = hashlib.md5(data_text).hexdigest()

        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=data_text,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, 'ready')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertEquals(deposit_request.deposit, deposit)
        self.assertRegex(deposit_request.archive.name, 'filename0')

        response_content = parse_xml(BytesIO(response.content))
        self.assertEqual(
            response_content['{http://www.w3.org/2005/Atom}deposit_archive'],
            'filename0')
        self.assertEqual(
            response_content['{http://www.w3.org/2005/Atom}deposit_id'],
            deposit.id)

        edit_se_iri = reverse('edit_se_iri',
                              args=[self.username, deposit.id])

        self.assertEqual(response._headers['location'],
                         ('Location', edit_se_iri))

    def test_post_deposit_binary_upload_only_supports_zip(self):
        """Binary upload only supports application/zip (for now)...

        """
        # given
        url = reverse(COL_IRI, args=[self.username])
        data_text = b'some content'
        md5sum = hashlib.md5(data_text).hexdigest()

        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/octet-stream',
            data=data_text,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

    def test_post_deposit_binary_fails_if_unsupported_packaging_header(
            self):
        """Binary upload must have content_disposition header provided...

        """
        # given
        url = reverse(COL_IRI, args=[self.username])
        data_text = b'some content'
        md5sum = hashlib.md5(data_text).hexdigest()

        external_id = 'some-external-id'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',
            data=data_text,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='something-unsupported',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)
        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

    def test_post_deposit_binary_upload_fail_if_no_content_disposition_header(
            self):
        """Binary upload must have content_disposition header provided...

        """
        # given
        url = reverse(COL_IRI, args=[self.username])
        data_text = b'some content'
        md5sum = hashlib.md5(data_text).hexdigest()

        external_id = 'some-external-id'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',
            data=data_text,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text))

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)
        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

    def test_post_deposit_mediation_not_supported(self):
        """Binary upload only supports application/zip (for now)...

        """
        # given
        url = reverse(COL_IRI, args=[self.username])
        data_text = b'some content'
        md5sum = hashlib.md5(data_text).hexdigest()

        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',
            data=data_text,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_ON_BEHALF_OF='someone',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_412_PRECONDITION_FAILED)

        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

    # FIXME: Test this scenario (need a way to override the default
    # size limit in test scenario)

    # def test_post_deposit_binary_upload_fail_if_upload_size_limit_exceeded(
    #         self):
    #     """Binary upload must not exceed the limit set up...

    #     """
    #     # given
    #     url = reverse(COL_IRI, args=[self.username])
    #     data_text = b'some content'
    #     md5sum = hashlib.md5(data_text).hexdigest()

    #     external_id = 'some-external-id'

    #     # when
    #     response = self.client.post(
    #         url,
    #         content_type='application/zip',
    #         data=data_text,
    #         # + headers
    #         HTTP_SLUG=external_id,
    #         HTTP_CONTENT_MD5=md5sum,
    #         HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
    #         HTTP_IN_PROGRESS='false',
    #         CONTENT_LENGTH=len(data_text),
    #         HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

    #     # then
    #     self.assertEqual(response.status_code,
    #                      status.HTTP_403_FORBIDDEN)
    #     with self.assertRaises(Deposit.DoesNotExist):
    #         Deposit.objects.get(external_id=external_id)

    def test_post_deposit_2_post_2_different_deposits(self):
        """Making 2 post requests result in 2 different deposit

        """
        url = reverse(COL_IRI, args=[self.username])
        data_text = b'some content'
        md5sum = hashlib.md5(data_text).hexdigest()

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=data_text,
            # + headers
            HTTP_SLUG='some-external-id-1',
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)

        deposits = Deposit.objects.all()
        self.assertEqual(len(deposits), 1)
        self.assertEqual(deposits[0], deposit)

        # second post
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=data_text,
            # + headers
            HTTP_SLUG='another-external-id',
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename1')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id2 = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']

        deposit2 = Deposit.objects.get(pk=deposit_id2)

        self.assertNotEqual(deposit, deposit2)

        deposits = Deposit.objects.all().order_by('id')
        self.assertEqual(len(deposits), 2)
        self.assertEqual(list(deposits), [deposit, deposit2])

    def test_post_deposit_binary_and_post_to_add_another_archive(self):
        """One post to post a binary deposit, One other post to update the
        first deposit.

        """
        # given
        url = reverse(COL_IRI, args=[self.username])

        external_id = 'some-external-id-1'

        # 1st archive to upload
        data_text0 = b'some other content'
        md5sum0 = hashlib.md5(data_text0).hexdigest()

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=data_text0,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum0,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='true',
            HTTP_CONTENT_LENGTH=len(data_text0),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, 'partial')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertEquals(deposit_request.deposit, deposit)
        self.assertEquals(deposit_request.type.name, 'archive')
        self.assertRegex(deposit_request.archive.name, 'filename0')

        # 2nd archive to upload
        data_text = b'second archive uploaded'
        md5sum1 = hashlib.md5(data_text).hexdigest()

        # uri to update the content
        update_uri = reverse(EM_IRI, args=[self.username, deposit_id])

        # adding another archive for the deposit
        response = self.client.post(
            update_uri,
            content_type='application/zip',  # as zip
            data=data_text,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum1,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename1')

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, 'ready')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_requests = list(DepositRequest.objects.filter(deposit=deposit).
                                order_by('id'))

        # 2 deposit requests for the same deposit
        self.assertEquals(len(deposit_requests), 2)
        self.assertEquals(deposit_requests[0].deposit, deposit)
        self.assertEquals(deposit_requests[0].type.name, 'archive')
        self.assertRegex(deposit_requests[0].archive.name, 'filename0')

        self.assertEquals(deposit_requests[1].deposit, deposit)
        self.assertEquals(deposit_requests[1].type.name, 'archive')
        self.assertRegex(deposit_requests[1].archive.name, 'filename1')

        # only 1 deposit in db
        deposits = Deposit.objects.all()
        self.assertEqual(len(deposits), 1)

    def test_post_deposit_then_post_or_put_is_refused_when_status_ready(self):
        """When a deposit is complete, updating/adding new data to it is
           forbidden.

        """
        url = reverse(COL_IRI, args=[self.username])

        external_id = 'some-external-id-1'

        # 1st archive to upload
        data_text0 = b'some other content'
        md5sum0 = hashlib.md5(data_text0).hexdigest()

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=data_text0,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum0,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text0),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, 'ready')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertEquals(deposit_request.deposit, deposit)
        self.assertRegex(deposit_request.archive.name, 'filename0')

        # updating/adding is forbidden

        # uri to update the content
        edit_se_iri = reverse(
            'edit_se_iri', args=[self.username, deposit_id])
        em_iri = reverse(
            'em_iri', args=[self.username, deposit_id])

        # Testing all update/add endpoint should fail
        # since the status is ready

        # replacing file is no longer possible since the deposit's
        # status is ready
        r = self.client.put(
            em_iri,
            content_type='application/zip',
            data=data_text0,
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum0,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text0),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        self.assertEquals(r.status_code, status.HTTP_400_BAD_REQUEST)

        # adding file is no longer possible since the deposit's status
        # is ready
        r = self.client.post(
            em_iri,
            content_type='application/zip',
            data=data_text0,
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum0,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text0),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        self.assertEquals(r.status_code, status.HTTP_400_BAD_REQUEST)

        # replacing metadata is no longer possible since the deposit's
        # status is ready
        r = self.client.put(
            edit_se_iri,
            content_type='application/atom+xml;type=entry',
            data=self.data_atom_entry_ok,
            HTTP_SLUG=external_id,
            HTTP_CONTENT_LENGTH=len(self.data_atom_entry_ok))

        self.assertEquals(r.status_code, status.HTTP_400_BAD_REQUEST)

        # adding new metadata is no longer possible since the
        # deposit's status is ready
        r = self.client.post(
            edit_se_iri,
            content_type='application/atom+xml;type=entry',
            data=self.data_atom_entry_ok,
            HTTP_SLUG=external_id,
            HTTP_CONTENT_LENGTH=len(self.data_atom_entry_ok))

        self.assertEquals(r.status_code, status.HTTP_400_BAD_REQUEST)

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

        self.assertEquals(r.status_code, status.HTTP_400_BAD_REQUEST)

        # adding new metadata is no longer possible since the
        # deposit's status is ready
        r = self.client.post(
            edit_se_iri,
            format='multipart',
            data={
                'archive': archive,
                'atom_entry': atom_entry,
            })

        self.assertEquals(r.status_code, status.HTTP_400_BAD_REQUEST)
