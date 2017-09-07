# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.test import TestCase
from io import BytesIO
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.models import Deposit, DepositType, DepositRequest
from .parsers import parse_xml

# from swh.deposit.views import SWHDeposit


class BasicTestCase(TestCase):
    def setUp(self):
        super().setUp()
        """Define the test client and other test variables."""
        _type = DepositType(name='hal')
        _type.save()
        _user = User(first_name='hal',
                     last_name='hal',
                     username='hal')
        _user.save()
        self.type = _type
        self.user = _user


class ModelTestCase(BasicTestCase):
    """This class defines the test suite for the bucketlist model.

    """
    def setUp(self):
        super().setUp()
        """Define the test client and other test variables."""
        deposit = {
            'type': self.type,
            'external_id': 'some-external-id',
            'client': self.user,
        }
        self.deposit = Deposit(**deposit)

    def test_model_can_create_a_deposit(self):
        """Test the deposit model can create a deposit.

        """
        old_count = Deposit.objects.count()
        self.deposit.save()
        new_count = Deposit.objects.count()
        self.assertNotEqual(old_count, new_count)


class DepositTestCase(APITestCase, BasicTestCase):
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

    def test_post_deposit_binary_upload_final(self):
        """Binary upload should be accepted

        """
        # given
        url = reverse('upload', args=['hal'])
        data_text = b'some content'
        md5sum = hashlib.md5(data_text).hexdigest()
        id = hashlib.sha1(data_text).hexdigest()

        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=data_text,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZIP',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        deposit = Deposit.objects.get(external_id=external_id)
        self.assertIsNotNone(deposit)
        self.assertEqual(deposit.status, 'ready')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.type, self.type)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertIsNotNone(deposit_request)
        self.assertEquals(deposit_request.deposit, deposit)
        self.assertEquals(deposit_request.metadata, {
            'archive': {
                'id': id,
                'name': 'filename0',
            },
        })

        response_content = parse_xml(BytesIO(response.content))
        self.assertEqual(
            response_content['{http://www.w3.org/2005/Atom}deposit_archive'],
            'filename0')
        self.assertEqual(
            response_content['{http://www.w3.org/2005/Atom}deposit_id'],
            deposit.id)

    def test_post_deposit_binary_upload_2_steps(self):
        """Binary upload should be accepted

        """
        # given
        url = reverse('upload', args=['hal'])

        external_id = 'some-external-id-1'

        # 1st archive to upload
        data_text0 = b'some other content'
        md5sum0 = hashlib.md5(data_text0).hexdigest()
        id0 = hashlib.sha1(data_text0).hexdigest()

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=data_text0,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum0,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZIP',
            HTTP_IN_PROGRESS='true',
            HTTP_CONTENT_LENGTH=len(data_text0),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        deposit = Deposit.objects.get(external_id=external_id)
        self.assertIsNotNone(deposit)
        self.assertEqual(deposit.status, 'partial')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.type, self.type)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertIsNotNone(deposit_request)
        self.assertEquals(deposit_request.deposit, deposit)
        self.assertEquals(deposit_request.metadata, {
            'archive': {
                'id': id0,
                'name': 'filename0',
            },
        })

        # 2nd archive to upload
        data_text = b'second archive uploaded'
        md5sum1 = hashlib.md5(data_text).hexdigest()
        id1 = hashlib.sha1(data_text).hexdigest()

        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=data_text,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum1,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZIP',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename1')

        deposit = Deposit.objects.get(external_id=external_id)
        self.assertIsNotNone(deposit)
        self.assertEqual(deposit.status, 'ready')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.type, self.type)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_requests = list(DepositRequest.objects.filter(deposit=deposit))

        self.assertIsNotNone(deposit_requests)
        self.assertEquals(len(deposit_requests), 2)
        self.assertEquals(deposit_requests[0].deposit, deposit)
        self.assertEquals(deposit_requests[0].metadata, {
            'archive': {
                'id': id0,
                'name': 'filename0',
            },
        })
        self.assertEquals(deposit_requests[1].deposit, deposit)
        self.assertEquals(deposit_requests[1].metadata, {
            'archive': {
                'id': id1,
                'name': 'filename1',
            },
        })

    def test_post_deposit_binary_upload_only_supports_zip(self):
        """Binary upload only supports application/zip (for now)...

        """
        # given
        url = reverse('upload', args=['hal'])
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
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZIP',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        try:
            Deposit.objects.get(external_id=external_id)
        except Deposit.DoesNotExist:
            pass

    def test_post_deposit_binary_upload_fail_if_no_content_disposition_header(
            self):
        """Binary upload must have content_disposition header provided...

        """
        # given
        url = reverse('upload', args=['hal'])
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
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZIP',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text))

        # then
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)

        try:
            Deposit.objects.get(external_id=external_id)
        except Deposit.DoesNotExist:
            pass

    # FIXME: Test this scenario (need a way to override the default
    # size limit in test scenario)

    # def test_post_deposit_binary_upload_fail_if_upload_size_limit_exceeded(
    #         self):
    #     """Binary upload must not exceed the limit set up...

    #     """
    #     # given
    #     url = reverse('upload', args=['hal'])
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
    #         HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZIP',
    #         HTTP_IN_PROGRESS='false',
    #         CONTENT_LENGTH=len(data_text),
    #         HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

    #     # then
    #     self.assertEqual(response.status_code,
    #                      status.HTTP_403_FORBIDDEN)
    #     try:
    #         Deposit.objects.get(external_id=external_id)
    #     except Deposit.DoesNotExist:
    #         pass

    def test_post_deposit_multipart(self):
        """Test one deposit upload."""
        # given
        url = reverse('upload', args=['hal'])

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

        deposit = Deposit.objects.get(external_id=external_id)
        self.assertIsNotNone(deposit)
        self.assertEqual(deposit.status, 'ready')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.type, self.type)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertIsNotNone(deposit_request)
        self.assertEquals(deposit_request.deposit, deposit)
        self.assertEquals(deposit_request.metadata['archive'], {
            'id': id1,
            'name': 'archive0',
        })

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        deposit = Deposit.objects.get(external_id=external_id)
        self.assertIsNotNone(deposit)
        self.assertEqual(deposit.status, 'ready')
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.type, self.type)
        self.assertEqual(deposit.client, self.user)
        self.assertIsNone(deposit.swh_id)

        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertIsNotNone(deposit_request)
        self.assertEquals(deposit_request.deposit, deposit)
        self.assertEquals(deposit_request.metadata['archive'], {
            'id': id1,
            'name': 'archive0',
        })

    def test_post_deposit_multipart_only_archive_and_atom_entry(self):
        """Multipart deposit only accepts one archive and one atom+xml"""
        # given
        url = reverse('upload', args=['hal'])

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
        self.assertEqual(response.content,
                         b'Only 1 application/zip archive and 1 '
                         b'atom+xml entry is supported.')

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
        self.assertEqual(response.content,
                         b'You must provide both 1 application/zip and'
                         b' 1 atom+xml entry for multipart deposit.')

    def test_post_deposit_atom_empty_body_request(self):
        response = self.client.post(
            reverse('upload', args=['hal']),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data_empty_body)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.content,
                         b'Empty body request is not supported')

    def test_post_deposit_atom_unknown_no_external_id(self):
        response = self.client.post(
            reverse('upload', args=['hal']),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data3)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.content,
                         b'You need to provide an unique external identifier')

    def test_post_deposit_atom_unknown_client(self):
        response = self.client.post(
            reverse('upload', args=['unknown-one']),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data3,
            HTTP_SLUG='something')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.content, b'Unknown client unknown-one')

    def test_post_deposit_atom_entry_initial(self):
        """One deposit upload as atom entry

        """
        # given
        external_id = 'urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a'

        try:
            deposit = Deposit.objects.get(external_id=external_id)
        except Deposit.DoesNotExist:
            assert True

        atom_entry_data = self.atom_entry_data0 % external_id.encode('utf-8')

        # when
        response = self.client.post(
            reverse('upload', args=['hal']),
            content_type='application/atom+xml;type=entry',
            data=atom_entry_data,
            HTTP_IN_PROGRESS='false')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        deposit = Deposit.objects.get(external_id=external_id)
        self.assertIsNotNone(deposit)
        self.assertEqual(deposit.type, self.type)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.status, 'ready')
        self.assertEqual(deposit.client, self.user)

        # one associated request to a deposit
        deposit_request = DepositRequest.objects.get(deposit=deposit)
        actual_metadata = deposit_request.metadata
        self.assertIsNotNone(actual_metadata)
        self.assertIsNone(actual_metadata.get('archive'))

    def test_post_deposit_atom_entry_multiple_step(self):
        """Test one deposit upload."""
        # given
        external_id = 'urn:uuid:2225c695-cfb8-4ebb-aaaa-80da344efa6a'

        try:
            deposit = Deposit.objects.get(external_id=external_id)
        except Deposit.DoesNotExist:
            assert True

        # when
        response = self.client.post(
            reverse('upload', args=['hal']),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data1,
            HTTP_IN_PROGRESS='True',
            HTTP_SLUG=external_id)

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        deposit = Deposit.objects.get(external_id=external_id)
        self.assertIsNotNone(deposit)
        self.assertEqual(deposit.type, self.type)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.status, 'partial')
        self.assertEqual(deposit.client, self.user)

        # one associated request to a deposit
        deposit_requests = DepositRequest.objects.filter(deposit=deposit)
        self.assertEqual(len(deposit_requests), 1)

        atom_entry_data = self.atom_entry_data2 % external_id.encode('utf-8')

        # when
        response = self.client.post(
            reverse('upload', args=['hal']),
            content_type='application/atom+xml;type=entry',
            data=atom_entry_data,
            HTTP_IN_PROGRESS='False',
            HTTP_SLUG=external_id)

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        deposit = Deposit.objects.get(external_id=external_id)
        self.assertIsNotNone(deposit)
        self.assertEqual(deposit.type, self.type)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.status, 'ready')
        self.assertEqual(deposit.client, self.user)

        self.assertEqual(len(Deposit.objects.all()), 1)

        # now 2 associated requests to a same deposit
        deposit_requests = DepositRequest.objects.filter(deposit=deposit)
        self.assertEqual(len(deposit_requests), 2)

        for deposit_request in deposit_requests:
            actual_metadata = deposit_request.metadata
            self.assertIsNotNone(actual_metadata)
            self.assertIsNone(actual_metadata.get('archive'))
