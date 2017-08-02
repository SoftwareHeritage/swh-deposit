# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""swh URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin

from swh.deposit.views import index, SWHServiceDocument, SWHUser


urlpatterns = [
    url(r'^admin', admin.site.urls),
    url(r'^deposit[/]+$', index),
    url(r'^deposit/clients[/]+$', SWHUser.as_view()),
    url(r'^deposit/clients/(?P<client_id>[0-9]+)', SWHUser.as_view()),
    url(r'^deposit/sd', SWHServiceDocument.as_view())
]
