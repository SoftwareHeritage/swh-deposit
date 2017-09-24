# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.config import COL_IRI, EDIT_SE_IRI

from ..common import BasicTestCase, WithAuthTestCase


class DepositFailuresTest(APITestCase, WithAuthTestCase, BasicTestCase):
    """Deposit access are protected with basic authentication.

    """
    def test_delete_on_col_iri_not_supported(self):
        """Delete on col iri should return a 405 response

        """
        url = reverse(COL_IRI, args=[self.username])
        response = self.client.delete(url)
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_on_edit_se_iri_not_supported(self):
        """Delete on col iri should return a 405 response

        """
        url = reverse(EDIT_SE_IRI, args=[self.username, 1])
        response = self.client.delete(url)
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)
