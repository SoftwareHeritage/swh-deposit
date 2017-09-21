# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.http import HttpResponse
from rest_framework.views import APIView


ACCEPT_PACKAGINGS = ['http://purl.org/net/sword/package/SimpleZip']
ACCEPT_CONTENT_TYPES = ['application/zip']


def index(req):
    return HttpResponse('SWH Deposit API')


class SWHAPIView(APIView):
    """Mixin intended as a based API view to enforce the basic
       authentication check

    """
    pass
