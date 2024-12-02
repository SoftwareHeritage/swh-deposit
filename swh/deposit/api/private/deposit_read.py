# Copyright (C) 2017-2024 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Dict, Iterator, List, Optional, Tuple
from xml.etree import ElementTree

from rest_framework import status

from swh.core import tarball
from swh.deposit.api.common import APIGet
from swh.deposit.api.private import APIPrivateView, DepositReadMixin
from swh.deposit.config import ARCHIVE_TYPE, SWH_PERSON
from swh.deposit.models import Deposit
from swh.deposit.utils import NAMESPACES, normalize_date
from swh.model.hashutil import hash_to_hex
from swh.model.model import MetadataAuthorityType
from swh.model.swhids import CoreSWHID


@contextmanager
def aggregate_tarballs(extraction_dir: str, archives: List) -> Iterator[str]:
    """Aggregate multiple tarballs into one and returns this new archive's
       path.

    Args:
        extraction_dir: Path to use for the tarballs computation
        archive_paths: Deposit's archive paths

    Returns:
        Tuple (directory to clean up, archive path (aggregated or not))

    """
    # rebuild one zip archive from (possibly) multiple ones
    os.makedirs(extraction_dir, 0o755, exist_ok=True)
    dir_path = tempfile.mkdtemp(prefix="swh.deposit-", dir=extraction_dir)

    # root folder to build an aggregated tarball
    aggregated_tarball_rootdir = os.path.join(dir_path, "aggregate")
    download_tarball_rootdir = os.path.join(dir_path, "download")

    # uncompress in a temporary location all client's deposit archives
    for archive in archives:
        with archive.open("rb") as archive_fp:
            try:
                # For storage which supports the path method access, let's retrieve it
                archive_path = archive.path
            except NotImplementedError:
                # otherwise for remote backend which do not support it, let's download
                # the tarball locally first
                tarball_path = Path(archive.name)

                tarball_path_dir = Path(download_tarball_rootdir) / tarball_path.parent
                tarball_path_dir.mkdir(0o755, parents=True, exist_ok=True)

                archive_path = str(tarball_path_dir / tarball_path.name)
                with open(archive_path, "wb") as f:
                    while chunk := archive_fp.read(10 * 1024 * 1024):
                        f.write(chunk)

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
        archives = [
            r.archive
            for r in self._deposit_requests(deposit, request_type=ARCHIVE_TYPE)
        ]
        return (
            status.HTTP_200_OK,
            aggregate_tarballs(self.extraction_dir, archives),
            "swh/generator",
        )


class APIReadMetadata(APIPrivateView, APIGet, DepositReadMixin):
    """Class in charge of aggregating metadata on a deposit."""

    def _parse_dates(
        self, deposit: Deposit, metadata: ElementTree.Element
    ) -> Tuple[dict, dict]:
        """Normalize the date to use as a tuple of author date, committer date
           from the incoming metadata.

        Returns:
            Tuple of author date, committer date. Those dates are
            swh normalized.

        """
        commit_date_elt = metadata.find("codemeta:datePublished", namespaces=NAMESPACES)
        author_date_elt = metadata.find("codemeta:dateCreated", namespaces=NAMESPACES)

        author_date: Any
        commit_date: Any

        if author_date_elt is None and commit_date_elt is None:
            author_date = commit_date = deposit.complete_date
        elif commit_date_elt is None:
            author_date = commit_date = author_date_elt.text  # type: ignore
        elif author_date_elt is None:
            author_date = commit_date = commit_date_elt.text
        else:
            author_date = author_date_elt.text
            commit_date = commit_date_elt.text

        return (normalize_date(author_date), normalize_date(commit_date))

    def metadata_read(self, deposit: Deposit) -> Dict[str, Any]:
        """Read and aggregate multiple deposit information into one unified dictionary.

        Args:
            deposit: Deposit to retrieve information from

        Returns:
            Dictionary of deposit information read by the deposit loader, with the
            following keys:

                **origin** (Dict): Information about the origin

                **raw_metadata** (str): List of raw metadata received for the
                  deposit

                **provider** (Dict): the metadata provider information about the
                  deposit client

                **tool** (Dict): the deposit information

                **deposit** (Dict): deposit information relevant to build the revision
                  (author_date, committer_date, etc...)

        """
        raw_metadata = self._metadata_get(deposit)
        author_date: Optional[dict]
        commit_date: Optional[dict]
        if raw_metadata:
            metadata_tree = ElementTree.fromstring(raw_metadata)
            author_date, commit_date = self._parse_dates(deposit, metadata_tree)
            release_notes_elements = metadata_tree.findall(
                "codemeta:releaseNotes", namespaces=NAMESPACES
            )
        else:
            author_date = commit_date = None
            release_notes_elements = []

        if deposit.parent and deposit.parent.swhid:
            parent_swhid = deposit.parent.swhid
            assert parent_swhid is not None
            swhid = CoreSWHID.from_string(parent_swhid)
            parent_revision = hash_to_hex(swhid.object_id)
            parents = [parent_revision]
        else:
            parents = []

        release_notes: Optional[str]
        if release_notes_elements:
            release_notes = "\n\n".join(
                element.text for element in release_notes_elements if element.text
            )
        else:
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
            "raw_metadata": raw_metadata,
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
