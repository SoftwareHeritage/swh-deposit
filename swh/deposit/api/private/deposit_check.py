# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import zipfile

from rest_framework import status


from ..common import SWHGetDepositAPI, SWHPrivateAPIView
from ...config import DEPOSIT_STATUS_READY, DEPOSIT_STATUS_REJECTED
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
            True if all archives are ok, False otherwise.

        """
        requests = list(self._deposit_requests(
            deposit, request_type=ARCHIVE_TYPE))
        if len(requests) == 0:  # no associated archive is refused
            return False

        for dr in requests:
            check = self._check_archive(dr.archive)
            if not check:
                return False
        return True

    def _check_archive(self, archive):
        """Check that a given archive is actually ok for reading.

        Args:
            archive (File): Archive to check

        Returns:
            True if archive is successfully read, False otherwise.

        """
        try:
            zf = zipfile.ZipFile(archive.path)
            zf.infolist()
        except Exception as e:
            return False
        else:
            return True

    def _check_deposit_metadata(self, deposit):
        """Given a deposit, check each deposit request of type metadata,
           by aggregating all metadata requests one bundle.

        Args:
            The deposit to check metadata for.

        Returns:
            True if the deposit's associated metadata are ok, False otherwise.

        """
        metadata = {}
        for dr in self._deposit_requests(deposit, request_type=METADATA_TYPE):
            metadata.update(dr.metadata)
        return self._check_metadata(metadata)

    def _check_metadata(self, metadata):
        """Check to execute on all metadata and keeps metadata_url for url validation.

        Args:
            metadata (): Metadata to actually check

        Returns:
            True if metadata is ok, False otherwise.

        """
        required_fields = (('url',),
                           ('external_identifier',),
                           ('name', 'title'),
                           ('author',))

        result = all(any(name in field
                         for field in metadata
                         for name in possible_names)
                     for possible_names in required_fields)
        urls = []
        for field in metadata:
            if 'url' in field:
                urls.append(metadata[field])
        self.metadata_url = urls
        return result

    def _check_url(self, client_url, metadata_urls):
        validatation = any(client_url in url
                           for url in metadata_urls)
        return validatation

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
        client_url = deposit.client.url
        self.metadata_url = None         # created in _check_metadata
        problems = []
        # will check each deposit's associated request (both of type
        # archive and metadata) for errors
        archives_status = self._check_deposit_archives(deposit)
        if not archives_status:
            problems.append('archive(s)')

        metadata_status = self._check_deposit_metadata(deposit)
        if not metadata_status:
            problems.append('metadata')

        url_status = self._check_url(client_url, self.metadata_url)
        if not url_status:
            problems.append('url')

        deposit_status = archives_status and metadata_status and url_status

        # if any problems arose, the deposit is rejected
        if not deposit_status:
            deposit.status = DEPOSIT_STATUS_REJECTED
        else:
            deposit.status = DEPOSIT_STATUS_READY
        deposit.save()

        return (status.HTTP_200_OK,
                json.dumps({
                    'status': deposit.status,
                    'details': 'Some %s failed the checks.' % (
                        ' and '.join(problems), ),
                }),
                'application/json')
