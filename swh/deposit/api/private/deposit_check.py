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

    def deposit_requests(self, deposit):
        """Given a deposit, yields its associated deposit_request

        Yields:
            deposit request

        """
        deposit_requests = DepositRequest.objects.filter(
            deposit=deposit).order_by('id')

        for deposit_request in deposit_requests:
            yield deposit_request

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

    def _check_metadata(self, metadata):
        """Check to execute on metadata.

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
        return result

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
        all_metadata = {}
        # will check each deposit request for the deposit
        for dr in self.deposit_requests(deposit):
            if dr.type.name == ARCHIVE_TYPE:
                archives_status = self._check_archive(dr.archive)
            elif dr.type.name == METADATA_TYPE:
                # aggregating all metadata requests for check on complete set
                all_metadata.update(dr.metadata)
            if not archives_status:
                break

        metadatas_status = self._check_metadata(all_metadata)
        deposit_status = archives_status and metadatas_status
        # if problem in any deposit requests, the deposit is rejected
        if not deposit_status:
            deposit.status = DEPOSIT_STATUS_REJECTED
        else:
            deposit.status = DEPOSIT_STATUS_READY

        deposit.save()

        return (status.HTTP_200_OK,
                json.dumps({
                    'status': deposit.status
                }),
                'application/json')
