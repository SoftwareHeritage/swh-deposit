# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.config import EDIT_SE_IRI, EM_IRI, ARCHIVE_KEY, METADATA_KEY
from swh.deposit.config import DEPOSIT_STATUS_DEPOSITED

from swh.deposit.models import Deposit, DepositRequest
from ..common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine


class DepositDeleteTest(APITestCase, WithAuthTestCase, BasicTestCase,
                        CommonCreationRoutine):

    def test_delete_archive_on_partial_deposit_works(self):
        """Removing partial deposit's archive should return a 204 response

        """
        # given
        deposit_id = self.create_deposit_partial()
        deposit = Deposit.objects.get(pk=deposit_id)
        deposit_requests = DepositRequest.objects.filter(deposit=deposit)

        self.assertEqual(len(deposit_requests), 2)
        for dr in deposit_requests:
            if dr.type.name == ARCHIVE_KEY:
                continue
            elif dr.type.name == METADATA_KEY:
                continue
            else:
                self.fail('only archive and metadata type should exist '
                          'in this test context')

        # when
        update_uri = reverse(EM_IRI, args=[self.collection.name, deposit_id])
        response = self.client.delete(update_uri)
        # then
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        deposit = Deposit.objects.get(pk=deposit_id)
        requests = list(DepositRequest.objects.filter(deposit=deposit))

        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0].type.name, 'metadata')
        self.assertEqual(requests[1].type.name, 'metadata')

    def test_delete_archive_on_undefined_deposit_fails(self):
        """Delete undefined deposit returns a 404 response

        """
        # when
        update_uri = reverse(EM_IRI, args=[self.collection.name, 999])
        response = self.client.delete(update_uri)
        # then
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_archive_on_non_partial_deposit_fails(self):
        """Delete !partial status deposit should return a 400 response"""
        deposit_id = self.create_deposit_ready()
        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_DEPOSITED)

        # when
        update_uri = reverse(EM_IRI, args=[self.collection.name, deposit_id])
        response = self.client.delete(update_uri)
        # then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertIsNotNone(deposit)

    def test_delete_partial_deposit_works(self):
        """Delete deposit should return a 204 response

        """
        # given
        deposit_id = self.create_simple_deposit_partial()
        deposit = Deposit.objects.get(pk=deposit_id)
        assert deposit.id == deposit_id

        # when
        url = reverse(EDIT_SE_IRI, args=[self.collection.name, deposit_id])
        response = self.client.delete(url)
        # then
        self.assertEqual(response.status_code,
                         status.HTTP_204_NO_CONTENT)
        deposit_requests = list(DepositRequest.objects.filter(deposit=deposit))
        self.assertEqual(deposit_requests, [])
        deposits = list(Deposit.objects.filter(pk=deposit_id))
        self.assertEqual(deposits, [])

    def test_delete_on_edit_se_iri_cannot_delete_non_partial_deposit(self):
        """Delete !partial deposit should return a 400 response

        """
        # given
        deposit_id = self.create_deposit_ready()
        deposit = Deposit.objects.get(pk=deposit_id)
        assert deposit.id == deposit_id

        # when
        url = reverse(EDIT_SE_IRI, args=[self.collection.name, deposit_id])
        response = self.client.delete(url)
        # then
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)
        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertIsNotNone(deposit)
