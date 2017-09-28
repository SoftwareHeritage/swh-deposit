# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..common import BasicTestCase, WithAuthTestCase


def assert_test_home_is_ok(testcase):
    url = reverse('home')
    response = testcase.client.get(url)
    testcase.assertEqual(response.status_code, status.HTTP_200_OK)
    testcase.assertEqual(response.content, b'SWH Deposit API')


class IndexNoAuthCase(APITestCase, BasicTestCase):
    """Access to main entry point is ok without authentication

    """
    def test_get_home_is_ok(self):
        """Without authentication, endpoint refuses access with 401 response

        """
        assert_test_home_is_ok(self)


class IndexWithAuthCase(WithAuthTestCase, APITestCase, BasicTestCase):
    """Access to main entry point is ok with authentication as well

    """
    def test_get_home_is_ok_2(self):
        """Without authentication, endpoint refuses access with 401 response

        """
        assert_test_home_is_ok(self)
