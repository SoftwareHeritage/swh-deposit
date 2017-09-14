# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.contrib.auth.models import User
from django.http import HttpResponse

from django.views.generic import ListView

from .common import SWHView


class SWHUser(ListView, SWHView):
    model = User

    def get(self, *args, **kwargs):
        if 'client_id' in kwargs:
            msg = 'Client '
            cs = self.get_queryset().filter(pk=kwargs['client_id'])
        else:
            msg = 'Clients'
            cs = self.get_queryset().all()
        return HttpResponse('%s: %s' % (msg, ','.join((str(c) for c in cs))))
