# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import re
import tarfile
import zipfile

from rest_framework import status


from . import DepositReadMixin
from ..common import SWHGetDepositAPI, SWHPrivateAPIView
from ...config import DEPOSIT_STATUS_VERIFIED, DEPOSIT_STATUS_REJECTED
from ...config import ARCHIVE_TYPE
from ...models import Deposit

MANDATORY_FIELDS_MISSING = 'Mandatory fields are missing'
ALTERNATE_FIELDS_MISSING = 'Mandatory alternate fields are missing'
INCOMPATIBLE_URL_FIELDS = "At least one url field must be compatible with the client's domain name"  # noqa
MANDATORY_ARCHIVE_UNREADABLE = 'At least one of its associated archives is not readable'  # noqa
MANDATORY_ARCHIVE_INVALID = 'Mandatory archive is invalid (i.e contains only one archive)'  # noqa
MANDATORY_ARCHIVE_UNSUPPORTED = 'Mandatory archive type is not supported'
MANDATORY_ARCHIVE_MISSING = 'Deposit without archive is rejected'

ARCHIVE_EXTENSIONS = [
    'zip', 'tar', 'tar.gz', 'xz', 'tar.xz', 'bz2',
    'tar.bz2', 'Z', 'tar.Z', 'tgz', '7z'
]

PATTERN_ARCHIVE_EXTENSION = re.compile(
    r'.*\.(%s)$' % '|'.join(ARCHIVE_EXTENSIONS))


class SWHChecksDeposit(SWHGetDepositAPI, SWHPrivateAPIView, DepositReadMixin):
    """Dedicated class to read a deposit's raw archives content.

    Only GET is supported.

    """
    def _check_deposit_archives(self, deposit):
        """Given a deposit, check each deposit request of type archive.

        Args:
            The deposit to check archives for

        Returns
            tuple (status, error_detail): True, None if all archives
            are ok, (False, <detailed-error>) otherwise.

        """
        requests = list(self._deposit_requests(
            deposit, request_type=ARCHIVE_TYPE))
        if len(requests) == 0:  # no associated archive is refused
            return False, {
                'archive': [{
                    'summary': MANDATORY_ARCHIVE_MISSING,
                }]
            }

        errors = []
        for archive_request in requests:
            check, error_message = self._check_archive(archive_request)
            if not check:
                errors.append({
                    'summary': error_message,
                    'fields': [archive_request.id]
                })

        if not errors:
            return True, None
        return False, {
            'archive': errors
        }

    def _check_archive(self, archive_request):
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
        try:
            if zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path) as f:
                    files = f.namelist()
            elif tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path) as f:
                    files = f.getnames()
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

    def _check_metadata(self, metadata):
        """Check to execute on all metadata for mandatory field presence.

        Args:
            metadata (dict): Metadata dictionary to check for mandatory fields

        Returns:
            tuple (status, error_detail): True, None if metadata are
              ok (False, <detailed-error>) otherwise.

        """
        required_fields = {
            'url': False,
            'external_identifier': False,
            'author': False,
        }
        alternate_fields = {
            ('name', 'title'): False,  # alternate field, at least one
            # of them must be present
        }

        for field, value in metadata.items():
            for name in required_fields:
                if name in field:
                    required_fields[name] = True

            for possible_names in alternate_fields:
                for possible_name in possible_names:
                    if possible_name in field:
                        alternate_fields[possible_names] = True
                        continue

        mandatory_result = [k for k, v in required_fields.items() if not v]
        optional_result = [
            ' or '.join(k) for k, v in alternate_fields.items() if not v]

        if mandatory_result == [] and optional_result == []:
            return True, None
        detail = []
        if mandatory_result != []:
            detail.append({
                'summary': MANDATORY_FIELDS_MISSING,
                'fields': mandatory_result
            })
        if optional_result != []:
            detail.append({
                'summary': ALTERNATE_FIELDS_MISSING,
                'fields': optional_result,
            })
        return False, {
            'metadata': detail
        }

    def _check_url(self, client_domain, metadata):
        """Check compatibility between client_domain and url field in metadata

        Args:
            client_domain (str): url associated with the deposit's client
            metadata (dict): Metadata where to find url

        Returns:
            tuple (status, error_detail): True, None if url associated
              with the deposit's client is ok, (False,
              <detailed-error>) otherwise.

        """
        url_fields = []
        for field in metadata:
            if 'url' in field:
                if client_domain in metadata[field]:
                    return True, None
                url_fields.append(field)

        detail = {
            'url': {
                'summary': INCOMPATIBLE_URL_FIELDS,
            }
        }
        if url_fields:
            detail['url']['fields'] = url_fields
        return False, detail

    def process_get(self, req, collection_name, deposit_id):
        """Build a unique tarball from the multiple received and stream that
           content to the client.

        Args:
            req (Request):
            collection_name (str): Collection owning the deposit
            deposit_id (id): Deposit concerned by the reading

        Returns:
            Tuple status, stream of content, content-type

        """
        deposit = Deposit.objects.get(pk=deposit_id)
        client_domain = deposit.client.domain
        metadata = self._metadata_get(deposit)
        problems = {}
        # will check each deposit's associated request (both of type
        # archive and metadata) for errors
        archives_status, error_detail = self._check_deposit_archives(deposit)
        if not archives_status:
            problems.update(error_detail)

        metadata_status, error_detail = self._check_metadata(metadata)
        if not metadata_status:
            problems.update(error_detail)

        url_status, error_detail = self._check_url(client_domain, metadata)
        if not url_status:
            problems.update(error_detail)

        deposit_status = archives_status and metadata_status and url_status

        # if any problems arose, the deposit is rejected
        if not deposit_status:
            deposit.status = DEPOSIT_STATUS_REJECTED
            deposit.status_detail = problems
            response = {
                'status': deposit.status,
                'details': deposit.status_detail,
            }
        else:
            deposit.status = DEPOSIT_STATUS_VERIFIED
            response = {
                'status': deposit.status,
            }

        deposit.save()

        return status.HTTP_200_OK, json.dumps(response), 'application/json'
