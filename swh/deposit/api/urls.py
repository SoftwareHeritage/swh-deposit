# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""SWH's deposit api URL Configuration

"""

from django.conf.urls import url
from django.shortcuts import render

from ..config import COL_IRI, CONT_FILE_IRI, EDIT_IRI, EM_IRI, SD_IRI, SE_IRI, STATE_IRI
from .collection import CollectionAPI
from .content import ContentAPI
from .edit import EditAPI
from .edit_media import EditMediaAPI
from .service_document import ServiceDocumentAPI
from .state import StateAPI
from .sword_edit import SwordEditAPI


def api_view(req):
    return render(req, "api.html")


# PUBLIC API
urlpatterns = [
    # simple view on the api
    url(r"^$", api_view, name="api"),
    # SD IRI - Service Document IRI
    # -> GET
    url(r"^servicedocument/", ServiceDocumentAPI.as_view(), name=SD_IRI),
    # Col-IRI - Collection IRI
    # -> POST
    url(r"^(?P<collection_name>[^/]+)/$", CollectionAPI.as_view(), name=COL_IRI),
    # EM IRI - Atom Edit Media IRI (update archive IRI)
    # -> PUT (update-in-place existing archive)
    # -> POST (add new archive)
    url(
        r"^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/media/$",
        EditMediaAPI.as_view(),
        name=EM_IRI,
    ),
    # Edit IRI - Atom Entry Edit IRI (update metadata IRI)
    # -> PUT (update in place)
    # -> DELETE (delete container)
    url(
        r"^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/atom/$",
        EditAPI.as_view(),
        name=EDIT_IRI,
    ),
    # SE IRI - Sword Edit IRI ;; possibly same as Edit IRI
    # -> POST (add new metadata)
    url(
        r"^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/metadata/$",
        SwordEditAPI.as_view(),
        name=SE_IRI,
    ),
    # State IRI
    # -> GET
    url(
        r"^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/status/$",
        StateAPI.as_view(),
        name=STATE_IRI,
    ),
    # Cont-IRI
    # -> GET
    url(
        r"^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/content/$",
        ContentAPI.as_view(),
        name=CONT_FILE_IRI,
    ),  # specification is not clear about
    # File-IRI, we assume it's the same as
    # the Cont-IRI one
]
