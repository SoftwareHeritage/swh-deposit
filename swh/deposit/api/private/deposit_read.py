# Copyright (C) 2017  The Software Heritage developers
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

from ..common import SWHGetDepositAPI, SWHPrivateAPIView
from ...models import Deposit, DepositRequest


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
    if len(archive_paths) > 1:  # need to rebuild one archive
                                # from multiple ones
        os.makedirs(extraction_dir, 0o755, exist_ok=True)
        dir_path = tempfile.mkdtemp(prefix='swh.deposit-',
                                    dir=extraction_dir)
        # root folder to build an aggregated tarball
        aggregated_tarball_rootdir = os.path.join(dir_path, 'aggregate')
        os.makedirs(aggregated_tarball_rootdir, 0o755, exist_ok=True)

        # uncompress in a temporary location all archives
        for archive_path in archive_paths:
            tarball.uncompress(archive_path, aggregated_tarball_rootdir)

        # Aggregate into one big tarball the multiple smaller ones
        temp_tarpath = tarball.compress(
            aggregated_tarball_rootdir + '.zip',
            nature='zip',
            dirpath_or_files=aggregated_tarball_rootdir)

        # can already clean up temporary directory
        shutil.rmtree(aggregated_tarball_rootdir)

        try:
            yield temp_tarpath
        finally:
            shutil.rmtree(dir_path)

    else:  # only 1 archive, no need to do fancy actions (and no cleanup step)
        yield archive_paths[0]


class SWHDepositReadArchives(SWHGetDepositAPI, SWHPrivateAPIView):
    """Dedicated class to read a deposit's raw archives content.

    Only GET is supported.

    """
    ADDITIONAL_CONFIG = {
        'extraction_dir': ('str', '/tmp/swh-deposit/archive/'),
    }

    def __init__(self):
        super().__init__()
        self.extraction_dir = self.config['extraction_dir']
        if not os.path.exists(self.extraction_dir):
            os.makedirs(self.extraction_dir)

    def retrieve_archives(self, deposit_id):
        """Given a deposit identifier, returns its associated archives' path.

        Yields:
            path to deposited archives

        """
        deposit = Deposit.objects.get(pk=deposit_id)
        deposit_requests = DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types['archive']).order_by('id')

        for deposit_request in deposit_requests:
            yield deposit_request.archive.path

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
        archive_paths = list(self.retrieve_archives(deposit_id))
        with aggregate_tarballs(self.extraction_dir,
                                archive_paths) as path:
            return FileResponse(open(path, 'rb'),
                                status=status.HTTP_200_OK,
                                content_type='application/octet-stream')


class SWHDepositReadMetadata(SWHGetDepositAPI, SWHPrivateAPIView):
    """Class in charge of aggregating metadata on a deposit.

    """
    ADDITIONAL_CONFIG = {
        'provider': ('dict', {
            # 'provider_name': '',  # those are not set since read from the
            # 'provider_url': '',   # deposit's client
            'provider_type': 'deposit_client',
            'metadata': {}
        }),
        'tool': ('dict', {
            'tool_name': 'swh-deposit',
            'tool_version': '0.0.1',
            'tool_configuration': {
                'sword_version': '2'
            }
        })
    }

    def __init__(self):
        super().__init__()
        self.provider = self.config['provider']
        self.tool = self.config['tool']

    def _aggregate_metadata(self, deposit, metadata_requests):
        """Retrieve and aggregates metadata information.

        """
        metadata = {}
        for req in metadata_requests:
            metadata.update(req.metadata)

        return metadata

    def aggregate(self, deposit, requests):
        """Aggregate multiple data on deposit into one unified data dictionary.

        Args:
            deposit (Deposit): Deposit concerned by the data aggregation.
            requests ([DepositRequest]): List of associated requests which
                                         need aggregation.

        Returns:
            Dictionary of data representing the deposit to inject in swh.

        """
        data = {}

        # Retrieve tarballs/metadata information
        metadata = self._aggregate_metadata(deposit, requests)

        # Read information metadata
        data['origin'] = {
            'type': 'deposit',
            'url': os.path.join(deposit.client.url.rstrip('/'),
                                deposit.external_id),
        }

        # revision

        fullname = deposit.client.get_full_name()
        author_committer = {
            'name': deposit.client.last_name,
            'fullname': fullname,
            'email': deposit.client.email,
        }

        # metadata provider
        self.provider['provider_name'] = deposit.client.last_name
        self.provider['provider_url'] = deposit.client.url

        revision_type = 'tar'
        revision_msg = '%s: Deposit %s in collection %s' % (
            fullname, deposit.id, deposit.collection.name)
        complete_date = identifiers.normalize_timestamp(deposit.complete_date)

        data['revision'] = {
            'synthetic': True,
            'date': complete_date,
            'committer_date': complete_date,
            'author': author_committer,
            'committer': author_committer,
            'type': revision_type,
            'message': revision_msg,
            'metadata': metadata,
        }

        if deposit.parent:
            parent_revision = deposit.parent.swh_id
            data['revision']['parents'] = [parent_revision]

        data['occurrence'] = {
            'branch': 'master'
        }
        data['origin_metadata'] = {
            'provider': self.provider,
            'tool': self.tool,
            'metadata': metadata
        }

        return data

    def process_get(self, req, collection_name, deposit_id):
        deposit = Deposit.objects.get(pk=deposit_id)
        requests = DepositRequest.objects.filter(
            deposit=deposit, type=self.deposit_request_types['metadata'])

        data = self.aggregate(deposit, requests)
        d = {}
        if data:
            d = json.dumps(data)

        return status.HTTP_200_OK, d, 'application/json'
