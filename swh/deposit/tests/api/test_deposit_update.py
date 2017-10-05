# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib

from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.models import Deposit, DepositRequest
from swh.deposit.config import EDIT_SE_IRI, EM_IRI
from ..common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine


class DepositReplaceExistingDataTest(APITestCase, WithAuthTestCase,
                                     BasicTestCase, CommonCreationRoutine):
    """Try put/post (update/replace) query on EM_IRI

    """
    def setUp(self):
        super().setUp()

        self.atom_entry_data1 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <foobar>bar</foobar>
</entry>"""

    def test_replace_archive_to_deposit_is_possible(self):
        """Replace all archive with another one should return a 204 response

        """
        # given
        deposit_id = self.create_deposit_partial()

        deposit = Deposit.objects.get(pk=deposit_id)
        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['archive'])

        assert len(list(requests)) == 1
        assert 'filename0' in requests[0].archive.name

        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['metadata']))
        assert len(requests) == 1

        update_uri = reverse(EM_IRI, args=[self.username, deposit_id])

        data_text = b'some content'
        md5sum = hashlib.md5(data_text).hexdigest()
        external_id = 'some-external-id-1'

        response = self.client.put(
            update_uri,
            content_type='application/zip',  # as zip
            data=data_text,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=otherfilename')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['archive'])

        self.assertEquals(len(list(requests)), 1)
        self.assertRegex(requests[0].archive.name, 'otherfilename')

        # check we did not touch the other parts
        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['metadata']))
        self.assertEquals(len(requests), 1)

    def test_replace_metadata_to_deposit_is_possible(self):
        """Replace all metadata with another one should return a 204 response

        """
        # given
        deposit_id = self.create_deposit_partial()

        deposit = Deposit.objects.get(pk=deposit_id)
        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['metadata'])

        assert len(list(requests)) == 1
        external_id_key = '{http://www.w3.org/2005/Atom}external_identifier'
        assert requests[0].metadata[external_id_key] == 'some-external-id'

        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['archive']))
        assert len(requests) == 1

        update_uri = reverse(EDIT_SE_IRI, args=[self.username, deposit_id])

        response = self.client.put(
            update_uri,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data1)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['metadata'])

        self.assertEquals(len(list(requests)), 1)
        metadata = requests[0].metadata
        self.assertIsNone(metadata.get(external_id_key))
        self.assertEquals(metadata["{http://www.w3.org/2005/Atom}foobar"],
                          'bar')

        # check we did not touch the other parts
        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['archive']))
        self.assertEquals(len(requests), 1)


class DepositUpdateDepositWithNewDataTest(
        APITestCase, WithAuthTestCase, BasicTestCase, CommonCreationRoutine):
    """Testing Replace/Update on EDIT_SE_IRI class.

    """
    def setUp(self):
        super().setUp()

        self.atom_entry_data1 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <foobar>bar</foobar>
</entry>"""

    def test_add_archive_to_deposit_is_possible(self):
        """Add another archive to a deposit return a 201 response

        """
        # given
        deposit_id = self.create_deposit_partial()

        deposit = Deposit.objects.get(pk=deposit_id)
        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['archive'])

        assert len(list(requests)) == 1
        assert 'filename0' in requests[0].archive.name

        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['metadata']))
        assert len(requests) == 1

        update_uri = reverse(EM_IRI, args=[self.username, deposit_id])

        data_text = b'some content'
        md5sum = hashlib.md5(data_text).hexdigest()
        external_id = 'some-external-id-1'

        response = self.client.post(
            update_uri,
            content_type='application/zip',  # as zip
            data=data_text,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=otherfilename')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        requests = list(DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['archive']).order_by('id'))

        self.assertEquals(len(requests), 2)
        # first archive still exists
        self.assertRegex(requests[0].archive.name, 'filename0')
        # a new one was added
        self.assertRegex(requests[1].archive.name, 'otherfilename')

        # check we did not touch the other parts
        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['metadata']))
        self.assertEquals(len(requests), 1)

    def test_add_metadata_to_deposit_is_possible(self):
        """Replace all metadata with another one should return a 204 response

        """
        # given
        deposit_id = self.create_deposit_partial()

        deposit = Deposit.objects.get(pk=deposit_id)
        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['metadata'])

        assert len(list(requests)) == 1
        external_id_key = '{http://www.w3.org/2005/Atom}external_identifier'
        assert requests[0].metadata[external_id_key] == 'some-external-id'

        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['archive']))
        assert len(requests) == 1

        update_uri = reverse(EDIT_SE_IRI, args=[self.username, deposit_id])

        response = self.client.post(
            update_uri,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data1)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['metadata']).order_by('id')

        self.assertEquals(len(list(requests)), 2)
        # first metadata still exists
        self.assertEquals(requests[0].metadata[external_id_key],
                          'some-external-id')
        # a new one was added
        self.assertEquals(requests[1].metadata[
            "{http://www.w3.org/2005/Atom}foobar"],
                          'bar')

        # check we did not touch the other parts
        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['archive']))
        self.assertEquals(len(requests), 1)


class DepositUpdateFailuresTest(APITestCase, WithAuthTestCase, BasicTestCase,
                                CommonCreationRoutine):
    """Failure scenario about add/replace (post/put) query on deposit.

    """
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
        """Adding metadata to unknown deposit should return a 404 response

        """
        url = reverse(EDIT_SE_IRI,
                      args=[self.username, 999]),
        response = self.client.put(
            url,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_archive_to_unknown_deposit(self):
        """Adding metadata to unknown deposit should return a 404 response

        """
        url = reverse(EM_IRI,
                      args=[self.username, 999]),
        response = self.client.post(
            url,
            content_type='application/zip',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_replace_archive_to_unknown_deposit(self):
        """Replacing archive to unknown deposit should return a 404 response

        """
        url = reverse(EM_IRI,
                      args=[self.username, 999]),
        response = self.client.put(
            url,
            content_type='application/zip',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_metadata_to_em_iri_failure(self):
        """Add archive with wrong content type should return a 400 response

        """
        deposit_id = self.create_deposit_ready()

        update_uri = reverse(EM_IRI, args=[self.username, deposit_id])
        response = self.client.put(
            update_uri,
            content_type='application/binary',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_metadata_to_em_iri_failure(self):
        """Update archive with wrong content type should return 400 response

        """
        # given
        deposit_id = self.create_deposit_ready()
        # when
        update_uri = reverse(EM_IRI, args=[self.username, deposit_id])
        response = self.client.put(
            update_uri,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0)
        # then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
