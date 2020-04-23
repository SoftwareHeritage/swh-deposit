# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.conf.urls import url

from ...config import (
    PRIVATE_GET_RAW_CONTENT,
    PRIVATE_PUT_DEPOSIT,
    PRIVATE_GET_DEPOSIT_METADATA,
    PRIVATE_CHECK_DEPOSIT,
    PRIVATE_LIST_DEPOSITS,
)
from .deposit_read import SWHDepositReadArchives
from .deposit_read import SWHDepositReadMetadata
from .deposit_update_status import SWHUpdateStatusDeposit
from .deposit_check import SWHChecksDeposit
from .deposit_list import DepositList

urlpatterns = [
    # Retrieve deposit's raw archives' content
    # -> GET
    url(
        r"^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/raw/$",
        SWHDepositReadArchives.as_view(),
        name=PRIVATE_GET_RAW_CONTENT,
    ),
    # Update deposit's status
    # -> PUT
    url(
        r"^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/update/$",
        SWHUpdateStatusDeposit.as_view(),
        name=PRIVATE_PUT_DEPOSIT,
    ),
    # Retrieve metadata information on a specific deposit
    # -> GET
    url(
        r"^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/meta/$",
        SWHDepositReadMetadata.as_view(),
        name=PRIVATE_GET_DEPOSIT_METADATA,
    ),
    # Check archive and metadata information on a specific deposit
    # -> GET
    url(
        r"^(?P<collection_name>[^/]+)/(?P<deposit_id>[^/]+)/check/$",
        SWHChecksDeposit.as_view(),
        name=PRIVATE_CHECK_DEPOSIT,
    ),
    # Retrieve deposit's raw archives' content
    # -> GET
    url(
        r"^(?P<deposit_id>[^/]+)/raw/$",
        SWHDepositReadArchives.as_view(),
        name=PRIVATE_GET_RAW_CONTENT + "-nc",
    ),
    # Update deposit's status
    # -> PUT
    url(
        r"^(?P<deposit_id>[^/]+)/update/$",
        SWHUpdateStatusDeposit.as_view(),
        name=PRIVATE_PUT_DEPOSIT + "-nc",
    ),
    # Retrieve metadata information on a specific deposit
    # -> GET
    url(
        r"^(?P<deposit_id>[^/]+)/meta/$",
        SWHDepositReadMetadata.as_view(),
        name=PRIVATE_GET_DEPOSIT_METADATA + "-nc",
    ),
    # Check archive and metadata information on a specific deposit
    # -> GET
    url(
        r"^(?P<deposit_id>[^/]+)/check/$",
        SWHChecksDeposit.as_view(),
        name=PRIVATE_CHECK_DEPOSIT + "-nc",
    ),
    url(r"^deposits/$", DepositList.as_view(), name=PRIVATE_LIST_DEPOSITS),
]
