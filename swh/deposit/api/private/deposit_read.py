# Copyright (C) 2017-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from contextlib import contextmanager
import os
import shutil
import tempfile
from typing import Any, Dict, Tuple

from rest_framework import status

from swh.core import tarball
from swh.deposit.utils import normalize_date
from swh.model.hashutil import hash_to_hex
from swh.model.model import MetadataAuthorityType
from swh.model.swhids import CoreSWHID

from . import APIPrivateView, DepositReadMixin
from ...config import ARCHIVE_TYPE, SWH_PERSON
from ...models import Deposit
from ..common import APIGet


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
        aggregated_tarball_rootdir, "tar", aggregated_tarball_rootdir
    )
    # can already clean up temporary directory
    shutil.rmtree(aggregated_tarball_rootdir)

    try:
        yield temp_tarpath
    finally:
        shutil.rmtree(dir_path)


class APIReadArchives(APIPrivateView, APIGet, DepositReadMixin):
    """Dedicated class to read a deposit's raw archives content.

    Only GET is supported.

    """

    def __init__(self):
        super().__init__()
        self.extraction_dir = self.config["extraction_dir"]
        if not os.path.exists(self.extraction_dir):
            os.makedirs(self.extraction_dir)

    def process_get(
        self, request, collection_name: str, deposit: Deposit
    ) -> Tuple[int, Any, str]:
        """Build a unique tarball from the multiple received and stream that
           content to the client.

        Args:
            request (Request):
            collection_name: Collection owning the deposit
            deposit: Deposit concerned by the reading

        Returns:
            Tuple status, stream of content, content-type

        """
        archive_paths = [
            r.archive.path
            for r in self._deposit_requests(deposit, request_type=ARCHIVE_TYPE)
        ]
        return (
            status.HTTP_200_OK,
            aggregate_tarballs(self.extraction_dir, archive_paths),
            "swh/generator",
        )


class APIReadMetadata(APIPrivateView, APIGet, DepositReadMixin):
    """Class in charge of aggregating metadata on a deposit.

    """

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

    def metadata_read(self, deposit: Deposit) -> Dict[str, Any]:
        """Read and aggregate multiple deposit information into one unified dictionary.

        Args:
            deposit: Deposit to retrieve information from

        Returns:
            Dictionary of deposit information read by the deposit loader, with the
            following keys:

                **origin** (Dict): Information about the origin

                **metadata_raw** (List[str]): List of raw metadata received for the
                  deposit

                **metadata_dict** (Dict): Deposit aggregated metadata into one dict

                **provider** (Dict): the metadata provider information about the
                  deposit client

                **tool** (Dict): the deposit information

                **deposit** (Dict): deposit information relevant to build the revision
                  (author_date, committer_date, etc...)

        """
        metadata, raw_metadata = self._metadata_get(deposit)
        author_date, commit_date = self._normalize_dates(deposit, metadata)

        if deposit.parent:
            parent_swhid = deposit.parent.swhid
            assert parent_swhid is not None
            swhid = CoreSWHID.from_string(parent_swhid)
            parent_revision = hash_to_hex(swhid.object_id)
            parents = [parent_revision]
        else:
            parents = []

        release_notes = metadata.get("codemeta:releaseNotes")
        if isinstance(release_notes, list):
            release_notes = "\n\n".join(release_notes)
        if not release_notes:
            release_notes = None

        return {
            "origin": {"type": "deposit", "url": deposit.origin_url},
            "provider": {
                "provider_name": deposit.client.last_name,
                "provider_url": deposit.client.provider_url,
                "provider_type": MetadataAuthorityType.DEPOSIT_CLIENT.value,
                "metadata": {},
            },
            "tool": self.tool,
            "metadata_raw": raw_metadata,
            "metadata_dict": metadata,
            "deposit": {
                "id": deposit.id,
                "client": deposit.client.username,
                "collection": deposit.collection.name,
                "author": SWH_PERSON,
                "author_date": author_date,
                "committer": SWH_PERSON,
                "committer_date": commit_date,
                "revision_parents": parents,
                "release_notes": release_notes,
            },
        }

    def process_get(
        self, request, collection_name: str, deposit: Deposit
    ) -> Tuple[int, Dict, str]:
        data = self.metadata_read(deposit)
        return status.HTTP_200_OK, data if data else {}, "application/json"
