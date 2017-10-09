# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of scheduling deposit injection one-shot task to swh.

"""

import click
import os
import logging

from abc import ABCMeta, abstractmethod

from swh.core.config import SWHConfig
from swh.deposit.config import setup_django_for
from swh.model import hashutil
from swh.objstorage import get_objstorage


def previous_revision_id(swh_id):
    """Compute the parent's revision id (if any) from the swh_id.

    Args:
        swh_id (id): SWH Identifier from a previous deposit.

    Returns:
        None if no parent revision is detected.
        The revision id's hash if any.

    """
    if swh_id:
        return swh_id.split('-')[2]
    return None


class SWHScheduling(SWHConfig, metaclass=ABCMeta):
    """Base swh scheduling class to aggregate the schedule deposit
       injection.

    """
    CONFIG_BASE_FILENAME = 'deposit/server'
    DEFAULT_CONFIG = {
        'objstorage': ('dict', {
            'cls': 'remote',
            'args': {
                'url': 'http://localhost:5002',
            }
        }),
        'extraction_dir': ('str', '/srv/storage/space/tmp/')
    }

    def __init__(self):
        super().__init__()
        self.config = self.parse_config_file(
                additional_configs=[self.ADDITIONAL_CONFIG])
        self.log = logging.getLogger('swh.deposit.scheduling')
        self.objstorage = get_objstorage(**self.config['objstorage'])

    def _aggregate_tarballs(self, deposit, archive_requests):
        """Retrieve and aggregates tarballs information.

        """
        import shutil
        import tempfile
        from swh.loader.tar import tarball

        # root directory to manipulate tarballs
        extraction_dir = self.config['extraction_dir']

        os.makedirs(extraction_dir, 0o755, exist_ok=True)
        dir_path = tempfile.mkdtemp(prefix='swh.deposit.scheduler-',
                                    dir=extraction_dir)

        if len(archive_requests) > 1:  # need to rebuild one archive
            # from multiple ones
            # root folder to build an aggregated tarball
            aggregated_tarball_rootdir = os.path.join(dir_path, 'aggregate')
            os.makedirs(aggregated_tarball_rootdir, 0o755, exist_ok=True)

            for archive_request in archive_requests:
                archive = archive_request.metadata['archive']
                archive_name = archive['name']
                archive_id = archive['id']

                # write in a temporary location the tarball
                temp_tarball = os.path.join(dir_path, archive_name)

                # build the temporary tarball
                with open(temp_tarball, 'wb') as f:
                    for chunk in self.objstorage.get_stream(archive_id):
                        f.write(chunk)

                # to uncompress it in another temporary tarball directory
                tarball.uncompress(temp_tarball, aggregated_tarball_rootdir)

                # clean up the temporary compressed tarball
                os.remove(temp_tarball)

            # Aggregate into one big tarball the multiple smaller ones
            temp_tarball = tarball.compress(
                aggregated_tarball_rootdir + '.zip',
                nature='zip',
                dirpath_or_files=aggregated_tarball_rootdir)

            # clean up the temporary uncompressed tarball
            shutil.rmtree(aggregated_tarball_rootdir)

        else:  # we only need to retrieve the archive from the
            # objstorage
            archive = archive_requests[0].metadata['archive']
            archive_name = archive['name']
            archive_id = archive['id']

            # write in a temporary location the tarball
            temp_tarball = os.path.join(dir_path, archive_name)

            # build the temporary tarball
            with open(temp_tarball, 'wb') as f:
                for chunk in self.objstorage.get_stream(archive_id):
                    f.write(chunk)

        # FIXME: 1. Need to clean up the temporary space
        # FIXME: 2. In case of multiple archives, the archive name
        # elected here is the last one

        print('temporary tarball', temp_tarball)

        data = {
            'tarpath': temp_tarball,
            'name': archive_name,
        }
        return data

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

        metadata_requests = []
        archive_requests = []
        for req in requests:
            if req.type.name == 'archive':
                archive_requests.append(req)
            elif req.type.name == 'metadata':
                metadata_requests.append(req)
            else:
                raise ValueError('Unknown request type %s' % req.type)

        # Retrieve tarballs/metadata information
        archive_data = self._aggregate_tarballs(deposit, archive_requests)
        metadata = self._aggregate_metadata(deposit, metadata_requests)

        data['tarpath'] = archive_data['tarpath']

        # Read information metadata
        data['origin'] = {
            'type': deposit.collection.name,
            'url': deposit.external_id,
        }

        # revision

        fullname = deposit.client.get_full_name()
        author_committer = {
            'name': deposit.client.last_name,
            'fullname': fullname,
            'email': deposit.client.email,
        }

        revision_type = 'tar'
        revision_msg = '%s: Deposit %s in collection %s' % (
            fullname, deposit.id, deposit.collection.name)
        complete_date = deposit.complete_date

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

        parent_revision = previous_revision_id(deposit.swh_id)
        if parent_revision:
            data['revision'] = {
                'parents': [hashutil.hash_to_bytes(parent_revision)]
            }

        data['occurrence'] = {
            'branch': archive_data['name'],
        }

        return data

    @abstractmethod
    def schedule(self, deposit, data):
        """Schedule the new deposit injection.

        Args:
            deposit (Deposit): Deposit concerned by the data aggregation.
            data (dict): Deposit aggregated data

        Returns:
            None

        """
        pass


class SWHCeleryScheduling(SWHScheduling):
    """Deposit injection as Celery task scheduling.

    """
    ADDITIONAL_CONFIG = {
        'task_name': ('str', 'swh.loader.tar.tasks.LoadTarRepository'),
        'dry_run': ('bool', False),
    }

    def __init__(self):
        super().__init__()
        from swh.scheduler import utils
        self.task_name = self.config['task_name']
        self.task = utils.get_task(self.task_name)
        self.dry_run = self.config['dry_run']

    def schedule(self, deposit_data):
        """Schedule the new deposit injection directly through celery.

        Args:
            deposit_data (dict): Deposit aggregated information.

        Returns:
            None

        """
        tarpath = deposit_data['tarpath']
        origin = deposit_data['origin']
        visit_date = None  # default to Now
        revision = deposit_data['revision']
        occurrence = deposit_data['occurrence']

        if not self.dry_run:
            return self.task.delay(
                tarpath, origin, visit_date, revision, [occurrence])

        print(tarpath, origin, visit_date, revision, [occurrence])


class SWHScheduling(SWHConfig):
    """Deposit injection as SWH's task scheduling interface.

    """
    ADDITIONAL_CONFIG = {
        'scheduling_db': ('str', 'dbname=swh-scheduler-dev'),
    }

    def __init__(self):
        super().__init__()
        from swh.scheduler.backend import SchedulerBackend
        self.scheduler = SchedulerBackend(self.config)

    def schedule(self, deposit, data):
        """Schedule the new deposit injection through swh.scheduler's one-shot
        task api.

        Args:
            deposit (Deposit): Deposit concerned by the data aggregation.
            data (dict): Deposit aggregated data

        Returns:
            None

        """
        pass


@click.command(
    help='Schedule one-shot deposit injections')
@click.option('--platform', default='development',
              help='development or production platform')
def main(platform):
    setup_django_for(platform)

    from swh.deposit.models import Deposit, DepositRequest

    scheduling = SWHCeleryScheduling()

    deposits = Deposit.objects.filter(status='ready')
    for deposit in deposits:
        requests = DepositRequest.objects.filter(deposit_id=deposit.id)

        deposit_data = scheduling.aggregate(deposit, requests)
        scheduling.schedule(deposit_data)


if __name__ == '__main__':
    main()
