# Copyright (C) 2025 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import List, Tuple

from django.db.models import FileField
from django.http.request import HttpRequest
from rest_framework import status

from swh.deposit.api.common import APIGet
from swh.deposit.api.private import APIPrivateView, DepositReadMixin
from swh.deposit.config import ARCHIVE_TYPE
from swh.deposit.models import Deposit


class APIUploadURLs(APIPrivateView, APIGet, DepositReadMixin):
    """
    Private API endpoint returning a list of URLs for downloading
    tarballs uploaded with a deposit request.

    Only GET is supported.

    """

    @classmethod
    def _get_archive_url(cls, archive: FileField, request: HttpRequest) -> str:
        url = archive.storage.url(archive.name)
        if url.startswith("/"):
            url = request.build_absolute_uri(url)
        return url

    def process_get(
        self, request: HttpRequest, collection_name: str, deposit: Deposit
    ) -> Tuple[int, List[str], str]:
        """
        Returns list of URLs for downloading tarballs uploaded with
        a deposit request.

        Args:
            request: input HTTP request
            collection_name: Collection owning the deposit
            deposit: Deposit to get tarball download URLs

        Returns:
            Tuple status, list of URLs, content-type

        """
        upload_urls = [
            self._get_archive_url(r.archive, request)
            # ensure that tarball URLs are sorted in ascending order of their upload
            # dates as tarball contents will be aggregated into a single tarball by the
            # deposit loader and the files they contain can overlap
            for r in reversed(
                list(self._deposit_requests(deposit, request_type=ARCHIVE_TYPE))
            )
        ]
        return status.HTTP_200_OK, upload_urls, "application/json"
