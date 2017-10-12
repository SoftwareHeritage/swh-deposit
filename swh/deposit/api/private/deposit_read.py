# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import shutil
import tempfile

from rest_framework import status

from swh.loader.tar import tarball

from ..common import SWHGetDepositAPI, SWHPrivateAPIView
from ...models import Deposit, DepositRequest, TemporaryArchive


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
        directory_to_cleanup = dir_path
    else:  # only 1 archive, no need to do fancy actions (and no cleanup step)
        temp_tarpath = archive_paths[0]
        directory_to_cleanup = None

    return directory_to_cleanup, temp_tarpath


def stream_content(tarpath):
    """Stream a tarpath's content.

    Args:
        tarpath (path): Path to a tarball

    Raises:
        ValueError if the tarpath targets something nonexistent

    """
    if not os.path.exists(tarpath):
        raise ValueError('Development error: %s should exist' % tarpath)

    with open(tarpath, 'rb') as f:
        for chunk in f:
            yield chunk


class SWHDepositReadArchives(SWHGetDepositAPI, SWHPrivateAPIView):
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
            deposit=deposit,
            type=self.deposit_request_types['archive']).order_by('id')

        for deposit_request in deposit_requests:
            yield deposit_request.archive.path

    def cleanup(self, directory_to_cleanup):
        """Reference the temporary directory holding the archive to be cleaned
           up. This actually does not clean up but add a reference for
           a directory to be cleaned up if it exists.

        Args:
            directory_to_cleanup (str/None): A reference to a
            directory to be cleaned up

        """
        if directory_to_cleanup:
            # Add a temporary directory to be cleaned up in the db model
            # Another service is in charge of actually cleaning up
            if os.path.exists(directory_to_cleanup):
                tmp_archive = TemporaryArchive(path=directory_to_cleanup)
                tmp_archive.save()

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
        directory_to_cleanup, temp_tarpath = aggregate_tarballs(
            self.extraction_dir, archive_paths)
        stream = stream_content(temp_tarpath)
        self.cleanup(directory_to_cleanup)

        return status.HTTP_200_OK, stream, 'application/octet-stream'
