# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import shutil
import tempfile

from rest_framework import status

from swh.loader.tar import tarball
from .common import SWHGetDepositAPI
from ..models import Deposit, DepositRequest


def aggregate_tarballs(extraction_dir, archive_paths):
    """Aggregate multiple tarballs into one and returns this new archive's
       path.

    Args:
        extraction_dir (path): Path to use for the tarballs computation
        archive_paths ([str]): Deposit's archive paths

    Returns:
        Tuple (cleanup flag, archive path (aggregated or not))

    """
    if len(archive_paths) > 1:  # need to rebuild one archive
                                # from multiple ones
        os.makedirs(extraction_dir, 0o755, exist_ok=True)
        dir_path = tempfile.mkdtemp(prefix='swh.deposit.scheduler-',
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

        # clean up temporary uncompressed tarball's on-disk content
        shutil.rmtree(aggregated_tarball_rootdir)
        # need to cleanup the temporary tarball when we are done
        cleanup_step = True
    else:  # only 1 archive, no need to do fancy actions (and no cleanup step)
        cleanup_step = False
        temp_tarpath = archive_paths[0]

    print('cleanup_step: %s' % cleanup_step)
    print('temp: %s' % temp_tarpath)
    return cleanup_step, temp_tarpath


def stream_content(tarpath):
    """Stream a tarpath's content.

    Args:
        tarpath (path): Path to a tarball

    Raises:
        ValueError if the tarpath targets something inexisting.

    """
    if not os.path.exists(tarpath):
        raise ValueError('Development error: %s should exist' % tarpath)

    with open(tarpath, 'rb') as f:
        for chunk in f:
            yield chunk


class SWHDepositReadArchives(SWHGetDepositAPI):
    """Dedicated class to read a deposit's raw archives content.

    Only GET is supported.

    """
    ADDITIONAL_CONFIG = {
        'extraction_dir': ('str', '/tmp/swh-deposit/archive/')
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
            deposit=deposit, type=self.deposit_request_types['archive']).order_by('id')  # noqa

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
        cleanup_step, temp_tarpath = aggregate_tarballs(
            self.extraction_dir, archive_paths)
        stream = stream_content(temp_tarpath)

        # FIXME: Find proper way to clean up when consumption is done
        # if cleanup_step:
        #     shutil.rmtree(os.path.dirname(temp_tarpath))

        return status.HTTP_200_OK, stream, 'application/octet-stream'
