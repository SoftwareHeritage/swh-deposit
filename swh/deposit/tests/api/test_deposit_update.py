# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.models import Deposit, DepositRequest
from swh.deposit.config import EDIT_SE_IRI, EM_IRI

from ..common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine
from ..common import FileSystemCreationRoutine, create_arborescence_archive


class DepositUpdateOrReplaceExistingDataTest(
        APITestCase, WithAuthTestCase, BasicTestCase,
        FileSystemCreationRoutine, CommonCreationRoutine):
    """Try put/post (update/replace) query on EM_IRI

    """
    def setUp(self):
        super().setUp()

        self.atom_entry_data1 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <foobar>bar</foobar>
</entry>"""

        self.atom_entry_data1 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <foobar>bar</foobar>
</entry>"""

        self.archive2 = create_arborescence_archive(
            self.root_path, 'archive2', 'file2', b'some other content in file')

    def test_replace_archive_to_deposit_is_possible(self):
        """Replace all archive with another one should return a 204 response

        """
        # given
        deposit_id = self.create_simple_binary_deposit(status_partial=True)

        deposit = Deposit.objects.get(pk=deposit_id)
        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['archive'])

        assert len(list(requests)) == 1
        assert self.archive['name'] in requests[0].archive.name

        # we have no metadata for that deposit
        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['metadata']))
        assert len(requests) == 0

        deposit_id = self._update_deposit_with_status(deposit_id,
                                                      status_partial=True)

        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['metadata']))
        assert len(requests) == 1

        update_uri = reverse(EM_IRI, args=[self.collection.name, deposit_id])

        external_id = 'some-external-id-1'

        response = self.client.put(
            update_uri,
            content_type='application/zip',  # as zip
            data=self.archive2['data'],
            # + headers
            CONTENT_LENGTH=self.archive2['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=self.archive2['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_DISPOSITION='attachment; filename=%s' % (
                self.archive2['name'], ))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['archive'])

        self.assertEqual(len(list(requests)), 1)
        self.assertRegex(requests[0].archive.name, self.archive2['name'])

        # check we did not touch the other parts
        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['metadata']))
        self.assertEqual(len(requests), 1)

    def test_replace_metadata_to_deposit_is_possible(self):
        """Replace all metadata with another one should return a 204 response

        """
        # given
        deposit_id = self.create_simple_binary_deposit(status_partial=True)

        deposit = Deposit.objects.get(pk=deposit_id)
        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['metadata'])
        assert len(list(requests)) == 0

        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['archive']))
        assert len(requests) == 1

        update_uri = reverse(EDIT_SE_IRI, args=[self.collection.name,
                                                deposit_id])

        response = self.client.put(
            update_uri,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data1)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['metadata'])

        self.assertEqual(len(list(requests)), 1)
        metadata = requests[0].metadata
        self.assertEqual(metadata['foobar'], 'bar')

        # check we did not touch the other parts
        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['archive']))
        self.assertEqual(len(requests), 1)

    def test_add_archive_to_deposit_is_possible(self):
        """Add another archive to a deposit return a 201 response

        """
        # given
        deposit_id = self.create_simple_binary_deposit(status_partial=True)

        deposit = Deposit.objects.get(pk=deposit_id)
        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['archive'])

        assert len(list(requests)) == 1
        assert self.archive['name'] in requests[0].archive.name

        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['metadata']))
        assert len(requests) == 0

        update_uri = reverse(EM_IRI, args=[self.collection.name, deposit_id])

        external_id = 'some-external-id-1'

        response = self.client.post(
            update_uri,
            content_type='application/zip',  # as zip
            data=self.archive2['data'],
            # + headers
            CONTENT_LENGTH=self.archive2['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=self.archive2['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_DISPOSITION='attachment; filename=%s' % (
                self.archive2['name'],))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        requests = list(DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['archive']).order_by('id'))

        self.assertEqual(len(requests), 2)
        # first archive still exists
        self.assertRegex(requests[0].archive.name, self.archive['name'])
        # a new one was added
        self.assertRegex(requests[1].archive.name, self.archive2['name'])

        # check we did not touch the other parts
        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['metadata']))
        self.assertEqual(len(requests), 0)

    def test_add_metadata_to_deposit_is_possible(self):
        """Add metadata with another one should return a 204 response

        """
        # given
        deposit_id = self.create_deposit_partial()

        deposit = Deposit.objects.get(pk=deposit_id)
        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['metadata'])

        assert len(list(requests)) == 2

        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['archive']))
        assert len(requests) == 0

        update_uri = reverse(EDIT_SE_IRI, args=[self.collection.name,
                                                deposit_id])

        response = self.client.post(
            update_uri,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data1)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['metadata']).order_by('id')

        self.assertEqual(len(list(requests)), 3)
        # a new one was added
        self.assertEqual(requests[1].metadata['foobar'], 'bar')

        # check we did not touch the other parts
        requests = list(DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['archive']))
        self.assertEqual(len(requests), 0)


class DepositUpdateFailuresTest(APITestCase, WithAuthTestCase, BasicTestCase,
                                CommonCreationRoutine):
    """Failure scenario about add/replace (post/put) query on deposit.

    """
    def test_add_metadata_to_unknown_collection(self):
        """Replacing metadata to unknown deposit should return a 404 response

        """
        url = reverse(EDIT_SE_IRI, args=['test', 1000])
        response = self.client.post(
            url,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertRegex(response.content.decode('utf-8'),
                         'Unknown collection name test')

    def test_add_metadata_to_unknown_deposit(self):
        """Replacing metadata to unknown deposit should return a 404 response

        """
        url = reverse(EDIT_SE_IRI, args=[self.collection.name, 999])
        response = self.client.post(
            url,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertRegex(response.content.decode('utf-8'),
                         'Deposit with id 999 does not exist')

    def test_replace_metadata_to_unknown_deposit(self):
        """Adding metadata to unknown deposit should return a 404 response

        """
        url = reverse(EDIT_SE_IRI, args=[self.collection.name, 998])
        response = self.client.put(
            url,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertRegex(response.content.decode('utf-8'),
                         'Deposit with id 998 does not exist')

    def test_add_archive_to_unknown_deposit(self):
        """Adding metadata to unknown deposit should return a 404 response

        """
        url = reverse(EM_IRI, args=[self.collection.name, 997])
        response = self.client.post(
            url,
            content_type='application/zip',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertRegex(response.content.decode('utf-8'),
                         'Deposit with id 997 does not exist')

    def test_replace_archive_to_unknown_deposit(self):
        """Replacing archive to unknown deposit should return a 404 response

        """
        url = reverse(EM_IRI, args=[self.collection.name, 996])
        response = self.client.put(
            url,
            content_type='application/zip',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertRegex(response.content.decode('utf-8'),
                         'Deposit with id 996 does not exist')

    def test_post_metadata_to_em_iri_failure(self):
        """Update (POST) archive with wrong content type should return 400

        """
        deposit_id = self.create_deposit_partial()  # only update on partial
        update_uri = reverse(EM_IRI, args=[self.collection.name, deposit_id])
        response = self.client.post(
            update_uri,
            content_type='application/x-gtar-compressed',
            data=self.atom_entry_data0)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertRegex(response.content.decode('utf-8'),
                         'Packaging format supported is restricted to '
                         'application/zip, application/x-tar')

    def test_put_metadata_to_em_iri_failure(self):
        """Update (PUT) archive with wrong content type should return 400

        """
        # given
        deposit_id = self.create_deposit_partial()  # only update on partial
        # when
        update_uri = reverse(EM_IRI, args=[self.collection.name, deposit_id])
        response = self.client.put(
            update_uri,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0)
        # then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertRegex(response.content.decode('utf-8'),
                         'Packaging format supported is restricted to '
                         'application/zip, application/x-tar')
