# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib

from django.core.urlresolvers import reverse
from io import BytesIO
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.models import Deposit
from swh.deposit.parsers import parse_xml

from ..common import BasicTestCase, WithAuthTestCase
from ...config import COL_IRI, STATE_IRI


class DepositStatusTestCase(APITestCase, WithAuthTestCase, BasicTestCase):
    """Status on deposit

    """
    def test_post_deposit_with_status_check(self):
        """Binary upload should be accepted

        """
        # given
        url = reverse(COL_IRI, args=[self.username])
        data_text = b'some content'
        md5sum = hashlib.md5(data_text).hexdigest()

        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=data_text,
            # + headers
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_LENGTH=len(data_text),
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        deposit = Deposit.objects.get(external_id=external_id)

        status_url = reverse(STATE_IRI,
                             args=[self.username, deposit.id])

        # check status
        status_response = self.client.get(status_url)

        self.assertEqual(status_response.status_code, status.HTTP_200_OK)
        r = parse_xml(BytesIO(status_response.content))

        self.assertEqual(r['{http://www.w3.org/2005/Atom}deposit_id'],
                         deposit.id)
        self.assertEqual(r['{http://www.w3.org/2005/Atom}status'],
                         'ready')
        self.assertEqual(r['{http://www.w3.org/2005/Atom}detail'],
                         'deposit is fully received and ready for injection')

    def test_status_on_unknown_deposit(self):
        """Asking for the status of unknown deposit returns 404 response"""
        status_url = reverse(STATE_IRI, args=[self.username, 999])
        status_response = self.client.get(status_url)
        self.assertEqual(status_response.status_code,
                         status.HTTP_404_NOT_FOUND)
