# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.contrib.auth.models import User
from django.shortcuts import render

from ..config import SWHDefaultConfig
from .common import SWHAPIView, ACCEPT_PACKAGINGS, ACCEPT_CONTENT_TYPES


class SWHServiceDocument(SWHDefaultConfig, SWHAPIView):
    def get(self, req, *args, **kwargs):
        user = User.objects.get(username=req.user)

        context = {
            'max_upload_size': self.config['max_upload_size'],
            'verbose': self.config['verbose'],
            'noop': self.config['noop'],
            'accept_packagings': ACCEPT_PACKAGINGS,
            'accept_content_types': ACCEPT_CONTENT_TYPES,
            'collection': user.username,
        }
        return render(req, 'deposit/service_document.xml',
                      context, content_type='application/xml')
