# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.config import COL_IRI
from swh.deposit.models import DepositClient, DepositCollection

from ..common import BasicTestCase, WithAuthTestCase


class DepositFailuresTest(APITestCase, WithAuthTestCase, BasicTestCase):
    """Deposit access are protected with basic authentication.

    """
    def setUp(self):
        super().setUp()
        # Add another user
        _collection2 = DepositCollection(name='some')
        _collection2.save()
        _user = DepositClient.objects.create_user(username='user',
                                                  password='user')
        _user.collections = [_collection2.id]
        self.collection2 = _collection2

    def test_access_to_another_user_collection_is_forbidden(self):
        url = reverse(COL_IRI, args=[self.collection2.name])
        response = self.client.post(url)
        self.assertEqual(response.status_code,
                         status.HTTP_403_FORBIDDEN)

    def test_delete_on_col_iri_not_supported(self):
        """Delete on col iri should return a 405 response

        """
        url = reverse(COL_IRI, args=[self.collection.name])
        response = self.client.delete(url)
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)
