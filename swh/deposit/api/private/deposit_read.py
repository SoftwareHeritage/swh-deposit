# Copyright (C) 2017-2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import os
import shutil
import tempfile

from contextlib import contextmanager
from django.http import FileResponse
from rest_framework import status

from swh.core import tarball
from swh.model import identifiers
from swh.deposit.utils import normalize_date

from . import DepositReadMixin, SWHPrivateAPIView
from ...config import SWH_PERSON, ARCHIVE_TYPE
from ..common import SWHGetDepositAPI
from ...models import Deposit


@contextmanager
def aggregate_tarballs(extraction_dir, archive_paths):
    """Aggregate multiple tarballs into one and returns this new archive's
       path.

    Args:
        extraction_dir (path): Path to use for the tarballs computation
        archive_paths ([str]): Deposit's archive paths

    Returns:
        Tuple (directory to clean up, archive path (aggregated or not))

    """
    # rebuild one zip archive from (possibly) multiple ones
    os.makedirs(extraction_dir, 0o755, exist_ok=True)
    dir_path = tempfile.mkdtemp(prefix="swh.deposit-", dir=extraction_dir)

    # root folder to build an aggregated tarball
    aggregated_tarball_rootdir = os.path.join(dir_path, "aggregate")
    os.makedirs(aggregated_tarball_rootdir, 0o755, exist_ok=True)

    # uncompress in a temporary location all archives
    for archive_path in archive_paths:
        tarball.uncompress(archive_path, aggregated_tarball_rootdir)

    # Aggregate into one big tarball the multiple smaller ones
    temp_tarpath = shutil.make_archive(
        aggregated_tarball_rootdir, "zip", aggregated_tarball_rootdir
    )
    # can already clean up temporary directory
    shutil.rmtree(aggregated_tarball_rootdir)

    try:
        yield temp_tarpath
    finally:
        shutil.rmtree(dir_path)


class SWHDepositReadArchives(SWHPrivateAPIView, SWHGetDepositAPI, DepositReadMixin):
    """Dedicated class to read a deposit's raw archives content.

    Only GET is supported.

    """

    ADDITIONAL_CONFIG = {
        "extraction_dir": ("str", "/tmp/swh-deposit/archive/"),
    }

    def __init__(self):
        super().__init__()
        self.extraction_dir = self.config["extraction_dir"]
        if not os.path.exists(self.extraction_dir):
            os.makedirs(self.extraction_dir)

    def process_get(self, request, collection_name, deposit_id):
        """Build a unique tarball from the multiple received and stream that
           content to the client.

        Args:
            request (Request):
            collection_name (str): Collection owning the deposit
            deposit_id (id): Deposit concerned by the reading

        Returns:
            Tuple status, stream of content, content-type

        """
        archive_paths = [
            r.archive.path
            for r in self._deposit_requests(deposit_id, request_type=ARCHIVE_TYPE)
        ]
        with aggregate_tarballs(self.extraction_dir, archive_paths) as path:
            return FileResponse(
                open(path, "rb"),
                status=status.HTTP_200_OK,
                content_type="application/zip",
            )


class SWHDepositReadMetadata(SWHPrivateAPIView, SWHGetDepositAPI, DepositReadMixin):
    """Class in charge of aggregating metadata on a deposit.

 """

    ADDITIONAL_CONFIG = {
        "provider": (
            "dict",
            {
                # 'provider_name': '',  # those are not set since read from the
                # 'provider_url': '',   # deposit's client
                "provider_type": "deposit_client",
                "metadata": {},
            },
        ),
        "tool": (
            "dict",
            {
                "name": "swh-deposit",
                "version": "0.0.1",
                "configuration": {"sword_version": "2"},
            },
        ),
    }

    def __init__(self):
        super().__init__()
        self.provider = self.config["provider"]
        self.tool = self.config["tool"]

    def _normalize_dates(self, deposit, metadata):
        """Normalize the date to use as a tuple of author date, committer date
           from the incoming metadata.

        Args:
            deposit (Deposit): Deposit model representation
            metadata (Dict): Metadata dict representation

        Returns:
            Tuple of author date, committer date. Those dates are
            swh normalized.

        """
        commit_date = metadata.get("codemeta:datePublished")
        author_date = metadata.get("codemeta:dateCreated")

        if author_date and commit_date:
            pass
        elif commit_date:
            author_date = commit_date
        elif author_date:
            commit_date = author_date
        else:
            author_date = deposit.complete_date
            commit_date = deposit.complete_date
        return (normalize_date(author_date), normalize_date(commit_date))

    def metadata_read(self, deposit):
        """Read and aggregate multiple data on deposit into one unified data
           dictionary.

        Args:
            deposit (Deposit): Deposit concerned by the data aggregation.

        Returns:
            Dictionary of data representing the deposit to inject in swh.

        """
        metadata = self._metadata_get(deposit)
        # Read information metadata
        data = {"origin": {"type": "deposit", "url": deposit.origin_url,}}

        # metadata provider
        self.provider["provider_name"] = deposit.client.last_name
        self.provider["provider_url"] = deposit.client.provider_url

        author_date, commit_date = self._normalize_dates(deposit, metadata)

        if deposit.parent:
            swh_persistent_id = deposit.parent.swh_id
            persistent_identifier = identifiers.parse_persistent_identifier(
                swh_persistent_id
            )
            parent_revision = persistent_identifier.object_id
            parents = [parent_revision]
        else:
            parents = []

        data["origin_metadata"] = {
            "provider": self.provider,
            "tool": self.tool,
            "metadata": metadata,
        }
        data["deposit"] = {
            "id": deposit.id,
            "client": deposit.client.username,
            "collection": deposit.collection.name,
            "author": SWH_PERSON,
            "author_date": author_date,
            "committer": SWH_PERSON,
            "committer_date": commit_date,
            "revision_parents": parents,
        }

        return data

    def process_get(self, request, collection_name, deposit_id):
        deposit = Deposit.objects.get(pk=deposit_id)
        data = self.metadata_read(deposit)
        d = {}
        if data:
            d = json.dumps(data)

        return status.HTTP_200_OK, d, "application/json"
