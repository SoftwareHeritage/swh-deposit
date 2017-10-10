# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.core.urlresolvers import reverse
from io import BytesIO
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.config import COL_IRI
from swh.deposit.models import Deposit, DepositRequest
from swh.deposit.parsers import parse_xml

from ..common import BasicTestCase, WithAuthTestCase


class DepositAtomEntryTestCase(APITestCase, WithAuthTestCase, BasicTestCase):
    """Try and post atom entry deposit.

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

    def test_post_deposit_atom_empty_body_request(self):
        response = self.client.post(
            reverse(COL_IRI, args=[self.username]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data_empty_body)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_deposit_atom_unknown_collection(self):
        response = self.client.post(
            reverse(COL_IRI, args=['unknown-one']),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data3,
            HTTP_SLUG='something')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_deposit_atom_entry_initial(self):
        """One deposit upload as atom entry

        """
        # given
        external_id = 'urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a'

        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

        atom_entry_data = self.atom_entry_data0 % external_id.encode('utf-8')

        # when
        response = self.client.post(
            reverse(COL_IRI, args=[self.username]),
            content_type='application/atom+xml;type=entry',
            data=atom_entry_data,
            HTTP_IN_PROGRESS='false')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.status, 'ready')
        self.assertEqual(deposit.client, self.user)

        # one associated request to a deposit
        deposit_request = DepositRequest.objects.get(deposit=deposit)
        actual_metadata = deposit_request.metadata
        self.assertIsNone(actual_metadata.get('archive'))

    def test_post_deposit_atom_entry_multiple_steps(self):
        """Test one deposit upload."""
        # given
        external_id = 'urn:uuid:2225c695-cfb8-4ebb-aaaa-80da344efa6a'

        with self.assertRaises(Deposit.DoesNotExist):
            deposit = Deposit.objects.get(external_id=external_id)

        # when
        response = self.client.post(
            reverse(COL_IRI, args=[self.username]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data1,
            HTTP_IN_PROGRESS='True',
            HTTP_SLUG=external_id)

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.status, 'partial')
        self.assertEqual(deposit.client, self.user)

        # one associated request to a deposit
        deposit_requests = DepositRequest.objects.filter(deposit=deposit)
        self.assertEqual(len(deposit_requests), 1)

        atom_entry_data = self.atom_entry_data2 % external_id.encode('utf-8')

        update_uri = response._headers['location'][1]

        # when updating the first deposit post
        response = self.client.post(
            update_uri,
            content_type='application/atom+xml;type=entry',
            data=atom_entry_data,
            HTTP_IN_PROGRESS='False',
            HTTP_SLUG=external_id)

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.collection, self.collection)
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
