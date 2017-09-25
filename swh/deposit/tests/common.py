# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.test import TestCase

from swh.deposit.models import DepositClient, DepositCollection
from swh.deposit.models import DepositRequestType


class BasicTestCase(TestCase):
    """Mixin intended for data setup purposes (user, collection, etc...)

    """
    def setUp(self):
        """Define the test client and other test variables."""
        super().setUp()

        # Add deposit request types
        for deposit_request_type in ['archive', 'metadata']:
            drt = DepositRequestType(name=deposit_request_type)
            drt.save()

        _name = 'hal'
        # set collection up
        _collection = DepositCollection(name=_name)
        _collection.save()
        # set user/client up
        _client = DepositClient.objects.create_user(username=_name,
                                                    password=_name)
        _client.collections = [_collection.id]
        _client.save()

        self.collection = _collection
        self.user = _client
        self.username = _name
        self.userpass = _name
        self.maxDiff = None


class WithAuthTestCase(TestCase):
    """Mixin intended for login/logout automatically during setUp/tearDown
       test method call.

    """
    def setUp(self):
        super().setUp()
        r = self.client.login(username=self.username, password=self.userpass)
        if not r:
            raise ValueError(
                'Dev error - test misconfiguration. Bad credentials provided!')

    def tearDown(self):
        super().tearDown()
        self.client.logout()
