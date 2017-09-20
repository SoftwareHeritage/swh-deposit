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
from rest_framework.urlpatterns import format_suffix_patterns

from .api.service_document import SWHServiceDocument
from .api.deposit import SWHDeposit, SWHDepositStatus
from .api.deposit import SWHUpdateMetadataDeposit, SWHUpdateArchiveDeposit

urlpatterns = [
    url(r'^admin', admin.site.urls,
        name='admin'),
    # SD IRI - Service Document IRI
    # -> GET
    url(r'^1/servicedocument/', SWHServiceDocument.as_view(),
        name='servicedocument'),
    # Col IRI - Collection IRI
    # -> POST
    url(r'^1/(?P<client_name>[^/]+)/$', SWHDeposit.as_view(),
        name='upload'),
    # EM IRI - Atom Edit Media IRI (update archive IRI)
    # -> PUT
    url(r'^1/(?P<client_name>[^/]+)/(?P<deposit_id>[^/]+)/$',
        SWHUpdateArchiveDeposit.as_view(),
        name='em_iri'),
    # Edit IRI - Atom Entry Edit IRI (update metadata IRI)
    # -> PUT
    # SE IRI - Sword Edit IRI (update metadata IRI) ;; same as Edit IRI
    # -> POST
    url(r'^1/(?P<client_name>[^/]+)/(?P<deposit_id>[^/]+)/$',
        SWHUpdateMetadataDeposit.as_view(),
        name='edit_se_iri'),

    # State IRI
    # -> GET
    url(r'^1/status/(?P<deposit_id>[^/]+)/$', SWHDepositStatus.as_view(),
        name='deposit_status'),

]

urlpatterns = format_suffix_patterns(urlpatterns)
