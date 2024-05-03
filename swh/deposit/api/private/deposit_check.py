# Copyright (C) 2017-2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from itertools import chain
import os
import re
from shutil import get_unpack_formats
import tarfile
from typing import Dict, Optional, Tuple
from xml.etree import ElementTree
import zipfile

from rest_framework import status
from rest_framework.request import Request

from swh.deposit.api.checks import check_metadata
from swh.deposit.api.common import APIGet
from swh.deposit.api.private import APIPrivateView, DepositReadMixin
from swh.deposit.config import (
    ARCHIVE_TYPE,
    DEPOSIT_STATUS_REJECTED,
    DEPOSIT_STATUS_VERIFIED,
)
from swh.deposit.models import Deposit, DepositRequest
from swh.scheduler.utils import create_oneshot_task

MANDATORY_ARCHIVE_UNREADABLE = (
    "At least one of its associated archives is not readable"  # noqa
)
MANDATORY_ARCHIVE_INVALID = (
    "Mandatory archive is invalid (i.e contains only one archive)"  # noqa
)
MANDATORY_ARCHIVE_UNSUPPORTED = "Mandatory archive type is not supported"
MANDATORY_ARCHIVE_MISSING = "Deposit without archive is rejected"

ARCHIVE_EXTENSIONS = [
    "zip",
    "tar",
    "tar.gz",
    "xz",
    "tar.xz",
    "bz2",
    "tar.bz2",
    "Z",
    "tar.Z",
    "tgz",
    "7z",
]

PATTERN_ARCHIVE_EXTENSION = re.compile(r".*\.(%s)$" % "|".join(ARCHIVE_EXTENSIONS))


def known_archive_format(filename):
    return any(
        filename.endswith(t) for t in chain(*(x[1] for x in get_unpack_formats()))
    )


class APIChecks(APIPrivateView, APIGet, DepositReadMixin):
    """Dedicated class to trigger the deposit checks on deposit archives and metadata.

    Only GET is supported.

    """

    def _check_deposit_archives(self, deposit: Deposit) -> Tuple[bool, Optional[Dict]]:
        """Given a deposit, check each deposit request of type archive.

        Args:
            The deposit to check archives for

        Returns
            tuple (status, details): True, None if all archives
            are ok, (False, <detailed-error>) otherwise.

        """
        requests = list(self._deposit_requests(deposit, request_type=ARCHIVE_TYPE))
        requests.reverse()
        if len(requests) == 0:  # no associated archive is refused
            return False, {
                "archive": [
                    {
                        "summary": MANDATORY_ARCHIVE_MISSING,
                    }
                ]
            }

        errors = []
        for archive_request in requests:
            check, error_message = self._check_archive(archive_request)
            if not check:
                errors.append(
                    {"summary": error_message, "fields": [archive_request.id]}
                )

        if not errors:
            return True, None
        return False, {"archive": errors}

    def _check_archive(
        self, archive_request: DepositRequest
    ) -> Tuple[bool, Optional[str]]:
        """Check that a deposit associated archive is ok:
        - readable
        - supported archive format
        - valid content: the archive does not contain a single archive file

        If any of those checks are not ok, return the corresponding
        failing check.

        Args:
            archive_path (DepositRequest): Archive to check

        Returns:
            (True, None) if archive is check compliant, (False,
            <detail-error>) otherwise.

        """
        archive = archive_request.archive
        archive_name = os.path.basename(archive.name)

        if not known_archive_format(archive_name):
            return False, MANDATORY_ARCHIVE_UNSUPPORTED

        try:
            # Use python's File api which is consistent across different types of
            # storage backends (e.g. file, azure, ...)

            # I did not find any other) workaround for azure blobstorage use, noop
            # otherwise
            reset_content_settings_if_needed(archive)
            # FIXME: ^ Implement a better way (after digging into django-storages[azure]

            with archive.open("rb") as archive_fp:
                try:
                    with zipfile.ZipFile(archive_fp) as zip_fp:
                        files = zip_fp.namelist()
                except Exception:
                    try:
                        # rewind since the first tryout reading may have moved the
                        # cursor
                        archive_fp.seek(0)
                        with tarfile.open(fileobj=archive_fp) as tar_fp:
                            files = tar_fp.getnames()
                    except Exception:
                        return False, MANDATORY_ARCHIVE_UNSUPPORTED
        except Exception:
            return False, MANDATORY_ARCHIVE_UNREADABLE
        if len(files) > 1:
            return True, None
        element = files[0]
        if PATTERN_ARCHIVE_EXTENSION.match(element):
            # archive in archive!
            return False, MANDATORY_ARCHIVE_INVALID
        return True, None

    def process_get(
        self, req: Request, collection_name: str, deposit: Deposit
    ) -> Tuple[int, Dict, str]:
        """Trigger the checks on the deposit archives and then on the deposit metadata.
        If any problems (or warnings) are raised, the deposit status and status detail
        are updated accordingly. If all checks are ok, the deposit status is updated to
        the 'verified' status (details updated with warning if any) and a loading task
        is scheduled for the deposit to be ingested. Otherwise, the deposit is marked as
        'rejected' with the error details. A json response is returned to the caller
        with the deposit checks.

        Args:
            req: Client request
            collection_name: Collection owning the deposit
            deposit: Deposit concerned by the reading

        Returns:
            Tuple (status, json response, content-type)

        """
        raw_metadata = self._metadata_get(deposit)
        details_dict: Dict = {}
        # will check each deposit's associated request (both of type
        # archive and metadata) for errors
        archives_status_ok, details = self._check_deposit_archives(deposit)
        if not archives_status_ok:
            assert details is not None
            details_dict.update(details)

        if raw_metadata is None:
            metadata_status_ok = False
            details_dict["metadata"] = [{"summary": "Missing Atom document"}]
        else:
            metadata_tree = ElementTree.fromstring(raw_metadata)
            metadata_status_ok, details = check_metadata(metadata_tree)
            # Ensure in case of error, we do have the rejection details
            assert metadata_status_ok or (
                not metadata_status_ok and details is not None
            )
            # we can have warnings even if checks are ok (e.g. missing suggested field)
            details_dict.update(details or {})

        deposit_status_ok = archives_status_ok and metadata_status_ok
        # if any details_dict arose, the deposit is rejected
        deposit.status = (
            DEPOSIT_STATUS_VERIFIED if deposit_status_ok else DEPOSIT_STATUS_REJECTED
        )
        response: Dict = {
            "status": deposit.status,
        }
        if details_dict:
            deposit.status_detail = details_dict
            response["details"] = details_dict

        # Deposit ok, then we schedule the deposit loading task (if not already done)
        if deposit_status_ok and not deposit.load_task_id and self.config["checks"]:
            url = deposit.origin_url
            task = create_oneshot_task(
                "load-deposit", url=url, deposit_id=deposit.id, retries_left=3
            )
            load_task_id = self.scheduler.create_tasks([task])[0].id
            deposit.load_task_id = str(load_task_id)

        deposit.save()

        return status.HTTP_200_OK, response, "application/json"


def reset_content_settings_if_needed(archive) -> None:
    """This resets the content_settings on the associated blob stored in an azure
    blobstorage. This prevents the correct reading of the file and failing the checks
    for no good reason.

    """
    try:
        from storages.backends.azure_storage import AzureStorage
    except ImportError:
        return None

    if not isinstance(archive.storage, AzureStorage):
        return None

    from azure.storage.blob import ContentSettings

    blob_client = archive.storage.client.get_blob_client(archive.name)

    # Get the existing blob properties
    properties = blob_client.get_blob_properties()

    # reset content encoding in the settings
    content_settings = dict(properties.content_settings)
    content_settings["content_encoding"] = ""

    # Set the content_type and content_language headers, and populate the remaining
    # headers from the existing properties
    blob_headers = ContentSettings(**content_settings)

    blob_client.set_http_headers(blob_headers)
