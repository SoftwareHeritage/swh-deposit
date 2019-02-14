# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import unittest

from django.core.urlresolvers import reverse
import pytest
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.config import (
    DEPOSIT_STATUS_VERIFIED, PRIVATE_CHECK_DEPOSIT,
    DEPOSIT_STATUS_DEPOSITED, DEPOSIT_STATUS_REJECTED
)
from swh.deposit.api.private.deposit_check import (
    SWHChecksDeposit, MANDATORY_ARCHIVE_INVALID,
    MANDATORY_FIELDS_MISSING, INCOMPATIBLE_URL_FIELDS,
    MANDATORY_ARCHIVE_UNSUPPORTED, ALTERNATE_FIELDS_MISSING,
    MANDATORY_ARCHIVE_MISSING
)
from swh.deposit.models import Deposit

from ..common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine
from ..common import FileSystemCreationRoutine


@pytest.mark.fs
class CheckDepositTest(APITestCase, WithAuthTestCase,
                       BasicTestCase, CommonCreationRoutine,
                       FileSystemCreationRoutine):
    """Check deposit endpoints.

    """
    def setUp(self):
        super().setUp()

    def test_deposit_ok(self):
        """Proper deposit should succeed the checks (-> status ready)

        """
        deposit_id = self.create_simple_binary_deposit(status_partial=True)
        deposit_id = self.update_binary_deposit(deposit_id,
                                                status_partial=False)

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_DEPOSITED)

        url = reverse(PRIVATE_CHECK_DEPOSIT,
                      args=[self.collection.name, deposit.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['status'], DEPOSIT_STATUS_VERIFIED)
        deposit = Deposit.objects.get(pk=deposit.id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_VERIFIED)

    def test_deposit_invalid_tarball(self):
        """Deposit with tarball (of 1 tarball) should fail the checks: rejected

        """
        for archive_extension in ['zip', 'tar', 'tar.gz', 'tar.bz2', 'tar.xz']:
            deposit_id = self.create_deposit_archive_with_archive(
                archive_extension)

            deposit = Deposit.objects.get(pk=deposit_id)
            self.assertEqual(DEPOSIT_STATUS_DEPOSITED, deposit.status)

            url = reverse(PRIVATE_CHECK_DEPOSIT,
                          args=[self.collection.name, deposit.id])

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data['status'], DEPOSIT_STATUS_REJECTED)
            details = data['details']
            # archive checks failure
            self.assertEqual(len(details['archive']), 1)
            self.assertEqual(details['archive'][0]['summary'],
                             MANDATORY_ARCHIVE_INVALID)

            deposit = Deposit.objects.get(pk=deposit.id)
            self.assertEqual(deposit.status, DEPOSIT_STATUS_REJECTED)

    def test_deposit_ko_missing_tarball(self):
        """Deposit without archive should fail the checks: rejected

        """
        deposit_id = self.create_deposit_ready()  # no archive, only atom
        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(DEPOSIT_STATUS_DEPOSITED, deposit.status)

        url = reverse(PRIVATE_CHECK_DEPOSIT,
                      args=[self.collection.name, deposit.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['status'], DEPOSIT_STATUS_REJECTED)
        details = data['details']
        # archive checks failure
        self.assertEqual(len(details['archive']), 1)
        self.assertEqual(details['archive'][0]['summary'],
                         MANDATORY_ARCHIVE_MISSING)
        deposit = Deposit.objects.get(pk=deposit.id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_REJECTED)

    def test_deposit_ko_unsupported_tarball(self):
        """Deposit with an unsupported tarball should fail the checks: rejected

        """
        deposit_id = self.create_deposit_with_invalid_archive()

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(DEPOSIT_STATUS_DEPOSITED, deposit.status)

        url = reverse(PRIVATE_CHECK_DEPOSIT,
                      args=[self.collection.name, deposit.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['status'], DEPOSIT_STATUS_REJECTED)
        details = data['details']
        # archive checks failure
        self.assertEqual(len(details['archive']), 1)
        self.assertEqual(details['archive'][0]['summary'],
                         MANDATORY_ARCHIVE_UNSUPPORTED)
        # metadata check failure
        self.assertEqual(len(details['metadata']), 2)
        mandatory = details['metadata'][0]
        self.assertEqual(mandatory['summary'], MANDATORY_FIELDS_MISSING)
        self.assertEqual(set(mandatory['fields']),
                         set(['url', 'external_identifier', 'author']))
        alternate = details['metadata'][1]
        self.assertEqual(alternate['summary'], ALTERNATE_FIELDS_MISSING)
        self.assertEqual(alternate['fields'], ['name or title'])
        # url check failure
        self.assertEqual(details['url']['summary'], INCOMPATIBLE_URL_FIELDS)

        deposit = Deposit.objects.get(pk=deposit.id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_REJECTED)

    def test_check_deposit_metadata_ok(self):
        """Proper deposit should succeed the checks (-> status ready)
           with all **MUST** metadata

           using the codemeta metadata test set
        """
        deposit_id = self.create_simple_binary_deposit(status_partial=True)
        deposit_id_metadata = self.add_metadata_to_deposit(deposit_id)
        self.assertEqual(deposit_id, deposit_id_metadata)

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_DEPOSITED)

        url = reverse(PRIVATE_CHECK_DEPOSIT,
                      args=[self.collection.name, deposit.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['status'], DEPOSIT_STATUS_VERIFIED)
        deposit = Deposit.objects.get(pk=deposit.id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_VERIFIED)


class CheckMetadata(unittest.TestCase, SWHChecksDeposit):
    def test_check_metadata_ok(self):
        actual_check, detail = self._check_metadata({
            'url': 'something',
            'external_identifier': 'something-else',
            'name': 'foo',
            'author': 'someone',
        })

        self.assertTrue(actual_check)
        self.assertIsNone(detail)

    def test_check_metadata_ok2(self):
        actual_check, detail = self._check_metadata({
            'url': 'something',
            'external_identifier': 'something-else',
            'title': 'bar',
            'author': 'someone',
        })

        self.assertTrue(actual_check)
        self.assertIsNone(detail)

    def test_check_metadata_ko(self):
        """Missing optional field should be caught

        """
        actual_check, error_detail = self._check_metadata({
            'url': 'something',
            'external_identifier': 'something-else',
            'author': 'someone',
        })

        expected_error = {
            'metadata': [{
                'summary': 'Mandatory alternate fields are missing',
                'fields': ['name or title'],
            }]
        }
        self.assertFalse(actual_check)
        self.assertEqual(error_detail, expected_error)

    def test_check_metadata_ko2(self):
        """Missing mandatory fields should be caught

        """
        actual_check, error_detail = self._check_metadata({
            'url': 'something',
            'external_identifier': 'something-else',
            'title': 'foobar',
        })

        expected_error = {
            'metadata': [{
                'summary': 'Mandatory fields are missing',
                'fields': ['author'],
            }]
        }

        self.assertFalse(actual_check)
        self.assertEqual(error_detail, expected_error)
