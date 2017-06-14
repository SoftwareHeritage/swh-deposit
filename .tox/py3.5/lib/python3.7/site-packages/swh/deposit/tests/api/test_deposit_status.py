# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from django.core.urlresolvers import reverse
from io import BytesIO
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.config import (COL_IRI, STATE_IRI, DEPOSIT_STATUS_DEPOSITED,
                                DEPOSIT_STATUS_REJECTED)
from swh.deposit.models import Deposit, DEPOSIT_STATUS_DETAIL
from swh.deposit.models import DEPOSIT_STATUS_LOAD_SUCCESS
from swh.deposit.parsers import parse_xml

from ..common import BasicTestCase, WithAuthTestCase, FileSystemCreationRoutine
from ..common import CommonCreationRoutine


class DepositStatusTestCase(APITestCase, WithAuthTestCase, BasicTestCase,
                            FileSystemCreationRoutine, CommonCreationRoutine):
    """Status on deposit

    """
    def test_post_deposit_with_status_check(self):
        """Binary upload should be accepted

        """
        # given
        url = reverse(COL_IRI, args=[self.collection.name])

        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=self.archive['data'],
            # + headers
            CONTENT_LENGTH=self.archive['length'],
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=self.archive['md5sum'],
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_IN_PROGRESS='false',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        deposit = Deposit.objects.get(external_id=external_id)

        status_url = reverse(STATE_IRI,
                             args=[self.collection.name, deposit.id])

        # check status
        status_response = self.client.get(status_url)

        self.assertEqual(status_response.status_code, status.HTTP_200_OK)
        r = parse_xml(BytesIO(status_response.content))

        self.assertEqual(int(r['deposit_id']), deposit.id)
        self.assertEqual(r['deposit_status'], DEPOSIT_STATUS_DEPOSITED)
        self.assertEqual(r['deposit_status_detail'],
                         DEPOSIT_STATUS_DETAIL[DEPOSIT_STATUS_DEPOSITED])

    def test_status_with_swh_information(self):
        _status = DEPOSIT_STATUS_LOAD_SUCCESS
        _context = 'https://hal.archives-ouvertes.fr/hal-01727745'
        _swh_id = 'swh:1:dir:42a13fc721c8716ff695d0d62fc851d641f3a12b'
        _swh_id_context = '%s;%s' % (_swh_id, _context)
        _swh_anchor_id = 'swh:rev:1:548b3c0a2bb43e1fca191e24b5803ff6b3bc7c10'
        _swh_anchor_id_context = '%s;%s' % (_swh_anchor_id, _context)

        # given
        deposit_id = self.create_deposit_with_status(
            status=_status,
            swh_id=_swh_id,
            swh_id_context=_swh_id_context,
            swh_anchor_id=_swh_anchor_id,
            swh_anchor_id_context=_swh_anchor_id_context
        )

        url = reverse(STATE_IRI, args=[self.collection.name, deposit_id])

        # when
        status_response = self.client.get(url)

        # then
        self.assertEqual(status_response.status_code, status.HTTP_200_OK)
        r = parse_xml(BytesIO(status_response.content))
        self.assertEqual(int(r['deposit_id']), deposit_id)
        self.assertEqual(r['deposit_status'], _status)
        self.assertEqual(r['deposit_status_detail'],
                         DEPOSIT_STATUS_DETAIL[DEPOSIT_STATUS_LOAD_SUCCESS])
        self.assertEqual(r['deposit_swh_id'], _swh_id)
        self.assertEqual(r['deposit_swh_id_context'], _swh_id_context)
        self.assertEqual(r['deposit_swh_anchor_id'], _swh_anchor_id)
        self.assertEqual(r['deposit_swh_anchor_id_context'],
                         _swh_anchor_id_context)

    def test_status_on_unknown_deposit(self):
        """Asking for the status of unknown deposit returns 404 response"""
        status_url = reverse(STATE_IRI, args=[self.collection.name, 999])
        status_response = self.client.get(status_url)
        self.assertEqual(status_response.status_code,
                         status.HTTP_404_NOT_FOUND)

    def test_status_with_http_accept_header_should_not_break(self):
        """Asking deposit status with Accept header should return 200

        """
        deposit_id = self.create_deposit_partial()

        status_url = reverse(STATE_IRI, args=[
            self.collection.name, deposit_id])
        response = self.client.get(
            status_url,
            HTTP_ACCEPT='text/html,application/xml;q=9,*/*,q=8')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_status_on_deposit_rejected(self):
        _status = DEPOSIT_STATUS_REJECTED
        _swh_id = '548b3c0a2bb43e1fca191e24b5803ff6b3bc7c10'
        _status_detail = {'url': {'summary': 'Wrong url'}}

        # given
        deposit_id = self.create_deposit_with_status(
            status=_status, swh_id=_swh_id, status_detail=_status_detail)

        url = reverse(STATE_IRI, args=[self.collection.name, deposit_id])

        # when
        status_response = self.client.get(url)

        # then
        self.assertEqual(status_response.status_code, status.HTTP_200_OK)
        r = parse_xml(BytesIO(status_response.content))
        self.assertEqual(int(r['deposit_id']), deposit_id)
        self.assertEqual(r['deposit_status'], _status)
        self.assertEqual(r['deposit_status_detail'], '- Wrong url')
        self.assertEqual(r['deposit_swh_id'], _swh_id)
