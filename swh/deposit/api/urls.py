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

from ..config import EDIT_SE_IRI, EM_IRI, CONT_FILE_IRI
from ..config import SD_IRI, COL_IRI, STATE_IRI
from .deposit import SWHDeposit
from .deposit_status import SWHDepositStatus
from .deposit_update import SWHUpdateMetadataDeposit
from .deposit_update import SWHUpdateArchiveDeposit
from .deposit_content import SWHDepositContent
from .service_document import SWHServiceDocument

urlpatterns = [
    # PUBLIC API

    # SD IRI - Service Document IRI
    # -> GET
    url(r'^servicedocument/', SWHServiceDocument.as_view(),
        name=SD_IRI),
    # Col IRI - Collection IRI
    # -> POST
    url(r'^(?P<collection_name>[^/]+)/$', SWHDeposit.as_view(),
        name=COL_IRI),
    # EM IRI - Atom Edit Media IRI (update archive IRI)
    # -> PUT (update-in-place existing archive)
    # -> POST (add new archive)
    url(r'^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/media/$',
        SWHUpdateArchiveDeposit.as_view(),
        name=EM_IRI),
    # Edit IRI - Atom Entry Edit IRI (update metadata IRI)
    # SE IRI - Sword Edit IRI ;; possibly same as Edit IRI
    # -> PUT (update in place)
    # -> POST (add new metadata)
    url(r'^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/metadata/$',
        SWHUpdateMetadataDeposit.as_view(),
        name=EDIT_SE_IRI),
    # State IRI
    # -> GET
    url(r'^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/status/$',
        SWHDepositStatus.as_view(),
        name=STATE_IRI),
    # Cont/File IRI
    # -> GET
    url(r'^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/content/$',
        SWHDepositContent.as_view(),
        name=CONT_FILE_IRI),  # specification is not clear about
                              # FILE-IRI, we assume it's the same as
                              # the CONT-IRI one
]
