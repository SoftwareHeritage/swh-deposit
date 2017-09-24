# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.shortcuts import render

from ..models import DepositClient, DepositCollection
from ..config import SWHDefaultConfig
from .common import SWHAPIView, ACCEPT_PACKAGINGS, ACCEPT_CONTENT_TYPES


class SWHServiceDocument(SWHDefaultConfig, SWHAPIView):
    def get(self, req, *args, **kwargs):
        client = DepositClient.objects.get(username=req.user)

        collections = []
        for col_id in client.collections:
            col = DepositCollection.objects.get(pk=col_id)
            collections.append(col)

        context = {
            'max_upload_size': self.config['max_upload_size'],
            'verbose': self.config['verbose'],
            'noop': self.config['noop'],
            'accept_packagings': ACCEPT_PACKAGINGS,
            'accept_content_types': ACCEPT_CONTENT_TYPES,
            'collections': collections,
        }
        return render(req, 'deposit/service_document.xml',
                      context, content_type='application/xml')
