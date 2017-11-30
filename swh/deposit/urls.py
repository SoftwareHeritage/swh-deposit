# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""swhdeposit URL Configuration

The :data:`urlpatterns` list routes URLs to views. For more information please
    see: https://docs.djangoproject.com/en/1.11/topics/http/urls/

Examples:

- Function views:

  1. Add an import: ``from my_app import views``
  2. Add a URL to urlpatterns: ``url(r'^$', views.home, name='home')``

- Class-based views:

  1. Add an import: ``from other_app.views import Home``
  2. Add a URL to urlpatterns: ``url(r'^$', Home.as_view(), name='home')``

- Including another URLconf:

  1. Import the include function: ``from django.conf.urls import url, include``
  2. Add a URL to urlpatterns: ``url(r'^blog/', include('blog.urls'))``

"""

from django.conf.urls import url, include
from django.http import HttpResponse
from rest_framework.urlpatterns import format_suffix_patterns


def index(req):
    return HttpResponse('SWH Deposit API')


urlpatterns = [
    url(r'^$', index, name='home'),
    url(r'^1/', include('swh.deposit.api.urls')),
    url(r'^1/private/', include('swh.deposit.api.private.urls')),
]

urlpatterns = format_suffix_patterns(urlpatterns)
