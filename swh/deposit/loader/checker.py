# Copyright (C) 2017-2025  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from itertools import chain
import logging
import os
import re
from shutil import get_unpack_formats
import tarfile
import tempfile
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from xml.etree import ElementTree
import zipfile

import requests
import sentry_sdk

from swh.core import config
from swh.deposit.client import PrivateApiDepositClient
from swh.deposit.config import DEPOSIT_STATUS_REJECTED, DEPOSIT_STATUS_VERIFIED
from swh.deposit.loader.checks import check_metadata

logger = logging.getLogger(__name__)

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


def _check_archive(archive_url: str) -> Tuple[bool, Optional[str]]:
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
    parsed_archive_url = urlparse(archive_url)
    archive_name = os.path.basename(parsed_archive_url.path)

    if not known_archive_format(archive_name):
        return False, MANDATORY_ARCHIVE_UNSUPPORTED

    try:
        response = requests.get(archive_url, stream=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = os.path.join(tmpdir, archive_name)
            with open(archive_path, "wb") as archive_fp:
                for chunk in response.iter_content(chunk_size=10 * 1024 * 1024):
                    archive_fp.write(chunk)
            with open(archive_path, "rb") as archive_fp:
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


def _check_deposit_archives(
    archive_urls: List[str],
) -> Tuple[bool, Optional[Dict]]:
    """Given a deposit, check each deposit request of type archive.

    Args:
        The deposit to check archives for

    Returns
        tuple (status, details): True, None if all archives
        are ok, (False, <detailed-error>) otherwise.

    """
    if len(archive_urls) == 0:  # no associated archive is refused
        return False, {
            "archive": [
                {
                    "summary": MANDATORY_ARCHIVE_MISSING,
                }
            ]
        }

    errors = []
    for archive_url in archive_urls:
        check, error_message = _check_archive(archive_url)
        if not check:
            errors.append({"summary": error_message})

    if not errors:
        return True, None
    return False, {"archive": errors}


class DepositChecker:
    """Deposit checker implementation.

    Trigger deposit's checks through the private api.

    """

    def __init__(self):
        self.config: Dict[str, Any] = config.load_from_envvar()
        self.client = PrivateApiDepositClient(config=self.config["deposit"])

    def check(self, collection: str, deposit_id: str) -> Dict[str, Any]:
        status = None
        deposit_upload_urls = f"/{deposit_id}/upload-urls/"
        logger.debug("deposit-upload-urls: %s", deposit_upload_urls)
        details_dict: Dict = {}
        try:
            raw_metadata = self.client.metadata_get(f"/{deposit_id}/meta/").get(
                "raw_metadata"
            )

            # will check each deposit's associated request (both of type
            # archive and metadata) for errors

            archive_urls = self.client.do("GET", deposit_upload_urls).json()
            logger.debug("deposit-upload-urls result: %s", archive_urls)

            archives_status_ok, details = _check_deposit_archives(archive_urls)

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

            status = (
                DEPOSIT_STATUS_VERIFIED
                if deposit_status_ok
                else DEPOSIT_STATUS_REJECTED
            )

            self.client.status_update(
                f"/{deposit_id}/update/", status=status, status_detail=details_dict
            )

            status = "eventful" if status == DEPOSIT_STATUS_VERIFIED else "failed"
        except Exception as e:
            sentry_sdk.capture_exception()
            status = "failed"
            details_dict["exception"] = f"{e.__class__.__name__}: {str(e)}"
        logger.debug("Check status: %s", status)
        return {"status": status, "status_detail": details_dict}
