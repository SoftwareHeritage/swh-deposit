# Copyright (C) 2017-2025  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.urls import path
from django.urls import re_path as url

from swh.deposit.api.private.deposit_list import APIList, deposit_list_datatables
from swh.deposit.api.private.deposit_read import APIReadArchives, APIReadMetadata
from swh.deposit.api.private.deposit_releases import APIReleases
from swh.deposit.api.private.deposit_update_status import APIUpdateStatus
from swh.deposit.api.private.deposit_upload_urls import APIUploadURLs
from swh.deposit.config import (
    PRIVATE_GET_DEPOSIT_METADATA,
    PRIVATE_GET_RAW_CONTENT,
    PRIVATE_GET_RELEASES,
    PRIVATE_GET_UPLOAD_URLS,
    PRIVATE_LIST_DEPOSITS,
    PRIVATE_LIST_DEPOSITS_DATATABLES,
    PRIVATE_PUT_DEPOSIT,
)

urlpatterns = [
    # Retrieve deposit's raw archives' content
    # -> GET
    url(
        r"^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/raw/$",
        APIReadArchives.as_view(),
        name=PRIVATE_GET_RAW_CONTENT,
    ),
    # Update deposit's status
    # -> PUT
    url(
        r"^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/update/$",
        APIUpdateStatus.as_view(),
        name=PRIVATE_PUT_DEPOSIT,
    ),
    # Retrieve metadata information on a specific deposit
    # -> GET
    url(
        r"^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/meta/$",
        APIReadMetadata.as_view(),
        name=PRIVATE_GET_DEPOSIT_METADATA,
    ),
    # Retrieve deposit's raw archives' content
    # -> GET
    url(
        r"^(?P<deposit_id>[^/]+)/raw/$",
        APIReadArchives.as_view(),
        name=PRIVATE_GET_RAW_CONTENT + "-nc",
    ),
    # Update deposit's status
    # -> PUT
    url(
        r"^(?P<deposit_id>[^/]+)/update/$",
        APIUpdateStatus.as_view(),
        name=PRIVATE_PUT_DEPOSIT + "-nc",
    ),
    # Retrieve metadata information on a specific deposit
    # -> GET
    url(
        r"^(?P<deposit_id>[^/]+)/meta/$",
        APIReadMetadata.as_view(),
        name=PRIVATE_GET_DEPOSIT_METADATA + "-nc",
    ),
    url(r"^deposits/$", APIList.as_view(), name=PRIVATE_LIST_DEPOSITS),
    url(
        r"^deposits/datatables/$",
        deposit_list_datatables,
        name=PRIVATE_LIST_DEPOSITS_DATATABLES,
    ),
    # Retrieve all releases for a specific deposit
    # -> GET
    path(
        "<int:deposit_id>/releases/",
        APIReleases.as_view(),
        name=PRIVATE_GET_RELEASES,
    ),
    # Retrieve download URLs for the tarballs uploaded with a deposit
    # -> GET
    path(
        "<int:deposit_id>/upload-urls/",
        APIUploadURLs.as_view(),
        name=PRIVATE_GET_UPLOAD_URLS,
    ),
]
