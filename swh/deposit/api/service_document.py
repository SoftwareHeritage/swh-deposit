# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.shortcuts import render
from django.urls import reverse

from .common import SWHBaseDeposit, ACCEPT_PACKAGINGS
from .common import ACCEPT_ARCHIVE_CONTENT_TYPES
from ..config import COL_IRI
from ..models import DepositClient, DepositCollection


class SWHServiceDocument(SWHBaseDeposit):
    def get(self, req, *args, **kwargs):
        client = DepositClient.objects.get(username=req.user)

        collections = {}

        for col_id in client.collections:
            col = DepositCollection.objects.get(pk=col_id)
            col_uri = req.build_absolute_uri(reverse(COL_IRI, args=[col.name]))
            collections[col.name] = col_uri

        context = {
            "max_upload_size": self.config["max_upload_size"],
            "accept_packagings": ACCEPT_PACKAGINGS,
            "accept_content_types": ACCEPT_ARCHIVE_CONTENT_TYPES,
            "collections": collections,
        }
        return render(
            req, "deposit/service_document.xml", context, content_type="application/xml"
        )
