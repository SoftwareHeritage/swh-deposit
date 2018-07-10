# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import patoolib

from rest_framework import status


from ..common import SWHGetDepositAPI, SWHPrivateAPIView
from ...config import DEPOSIT_STATUS_VERIFIED, DEPOSIT_STATUS_REJECTED
from ...config import ARCHIVE_TYPE, METADATA_TYPE
from ...models import Deposit, DepositRequest


class SWHChecksDeposit(SWHGetDepositAPI, SWHPrivateAPIView):
    """Dedicated class to read a deposit's raw archives content.

    Only GET is supported.

    """
    def _deposit_requests(self, deposit, request_type):
        """Given a deposit, yields its associated deposit_request

        Args:
            deposit (Deposit): Deposit to list requests for
            request_type (str): Archive or metadata type

        Yields:
            deposit requests of type request_type associated to the deposit

        """
        deposit_requests = DepositRequest.objects.filter(
            type=self.deposit_request_types[request_type],
            deposit=deposit).order_by('id')

        for deposit_request in deposit_requests:
            yield deposit_request

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
                'archive': {
                    'summary': 'Deposit without archive is rejected.',
                    'id': deposit.id,
                }
            }

        rejected_dr_ids = []
        for dr in requests:
            _path = dr.archive.path
            check = self._check_archive(_path)
            if not check:
                rejected_dr_ids.append(dr.id)

        if rejected_dr_ids:
            return False, {
                'archive': {
                    'summary': 'Following deposit request ids are rejected '
                               'because their associated archive is not '
                               'readable',
                    'ids': rejected_dr_ids,
                }}
        return True, None

    def _check_archive(self, archive_path):
        """Check that a given archive is actually ok for reading.

        Args:
            archive_path (str): Archive to check

        Returns:
            True if archive is successfully read, False otherwise.

        """
        try:
            patoolib.test_archive(archive_path, verbosity=-1)
        except Exception:
            return False
        else:
            return True

    def _metadata_get(self, deposit):
        """Given a deposit, aggregate all metadata requests.

        Args:
            deposit (Deposit): The deposit instance to extract
            metadata from.

        Returns:
            metadata dict from the deposit.

        """
        metadata = {}
        for dr in self._deposit_requests(deposit, request_type=METADATA_TYPE):
            metadata.update(dr.metadata)
        return metadata

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
            k for k, v in alternate_fields.items() if not v]

        if mandatory_result == [] and optional_result == []:
            return True, None
        detail = []
        if mandatory_result != []:
            detail.append({
                'summary': 'Mandatory fields are missing',
                'fields': mandatory_result
            })
        if optional_result != []:
            detail.append({
                'summary': 'Mandatory alternate fields are missing',
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
            url_fields.append(field)
            if 'url' in field and client_domain in metadata[field]:
                return True, None

        return False, {
            'url': {
                'summary': "At least one url field must be compatible with the"
                           " client's domain name. The following url fields "
                           "failed the check.",
                'fields': url_fields,
            }}

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
