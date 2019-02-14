# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..common import BasicTestCase, WithAuthTestCase


class IndexNoAuthCase(APITestCase, BasicTestCase):
    """Access to main entry point is ok without authentication

    """
    def test_get_home_is_ok(self):
        """Without authentication, endpoint refuses access with 401 response

        """
        url = reverse('home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b'The Software Heritage Deposit', response.content)


class IndexWithAuthCase(WithAuthTestCase, APITestCase, BasicTestCase):
    """Access to main entry point is ok with authentication as well

    """
    def test_get_home_is_ok_2(self):
        """Without authentication, endpoint refuses access with 401 response

        """
        url = reverse('home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b'The Software Heritage Deposit', response.content)
