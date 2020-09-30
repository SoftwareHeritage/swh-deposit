# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from itertools import chain
import re
from shutil import get_unpack_formats
import tarfile
from typing import Dict, Optional, Tuple
import zipfile

from rest_framework import status
from rest_framework.request import Request

from swh.scheduler.utils import create_oneshot_task_dict

from . import APIPrivateView, DepositReadMixin
from ...config import ARCHIVE_TYPE, DEPOSIT_STATUS_REJECTED, DEPOSIT_STATUS_VERIFIED
from ...models import Deposit, DepositRequest
from ..checks import check_metadata
from ..common import APIGet

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
    """Dedicated class to read a deposit's raw archives content.

    Only GET is supported.

    """

    def _check_deposit_archives(self, deposit: Deposit) -> Tuple[bool, Optional[Dict]]:
        """Given a deposit, check each deposit request of type archive.

        Args:
            The deposit to check archives for

        Returns
            tuple (status, error_detail): True, None if all archives
            are ok, (False, <detailed-error>) otherwise.

        """
        requests = list(self._deposit_requests(deposit, request_type=ARCHIVE_TYPE))
        if len(requests) == 0:  # no associated archive is refused
            return False, {"archive": [{"summary": MANDATORY_ARCHIVE_MISSING,}]}

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
        archive_path = archive_request.archive.path

        if not known_archive_format(archive_path):
            return False, MANDATORY_ARCHIVE_UNSUPPORTED

        try:
            if zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path) as zipfile_:
                    files = zipfile_.namelist()
            elif tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path) as tarfile_:
                    files = tarfile_.getnames()
            else:
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
        self, req: Request, collection_name: str, deposit_id: int
    ) -> Tuple[int, Dict, str]:
        """Build a unique tarball from the multiple received and stream that
           content to the client.

        Args:
            req: Client request
            collection_name: Collection owning the deposit
            deposit_id: Deposit concerned by the reading

        Returns:
            Tuple status, stream of content, content-type

        """
        deposit = Deposit.objects.get(pk=deposit_id)
        metadata, _ = self._metadata_get(deposit)
        problems: Dict = {}
        # will check each deposit's associated request (both of type
        # archive and metadata) for errors
        archives_status, error_detail = self._check_deposit_archives(deposit)
        if not archives_status:
            assert error_detail is not None
            problems.update(error_detail)

        metadata_status, error_detail = check_metadata(metadata)
        if not metadata_status:
            assert error_detail is not None
            problems.update(error_detail)

        deposit_status = archives_status and metadata_status

        # if any problems arose, the deposit is rejected
        if not deposit_status:
            deposit.status = DEPOSIT_STATUS_REJECTED
            deposit.status_detail = problems
            response = {
                "status": deposit.status,
                "details": deposit.status_detail,
            }
        else:
            deposit.status = DEPOSIT_STATUS_VERIFIED
            response = {
                "status": deposit.status,
            }
            if not deposit.load_task_id and self.config["checks"]:
                url = deposit.origin_url
                task = create_oneshot_task_dict(
                    "load-deposit", url=url, deposit_id=deposit.id, retries_left=3
                )
                load_task_id = self.scheduler.create_tasks([task])[0]["id"]
                deposit.load_task_id = load_task_id

        deposit.save()

        return status.HTTP_200_OK, response, "application/json"
