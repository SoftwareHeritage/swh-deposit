# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.contrib.auth.models import User
from django.test import TestCase

from swh.deposit.models import DepositType


class BasicTestCase(TestCase):
    """Mixin intended for adding a specific user

    """
    def setUp(self, auth=False):
        super().setUp()
        """Define the test client and other test variables."""
        _name = 'hal'
        _type = DepositType(name=_name)
        _type.save()
        _user = User.objects.create_user(username=_name, password=_name)
        self.type = _type
        self.user = _user
        self.user_name = _name
        self.user_pass = _name
        self.maxDiff = None


class WithAuthTestCase(TestCase):
    """Mixin intended for login/logout automatically during setUp/tearDown
       test method call.

    """
    def setUp(self):
        super().setUp()
        r = self.client.login(username=self.user_name, password=self.user_pass)
        if not r:
            raise ValueError(
                'Dev error - test misconfiguration. Bad credential provided!')

    def tearDown(self):
        super().tearDown()
        self.client.logout()