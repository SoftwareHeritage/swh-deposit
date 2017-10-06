# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of scheduling deposit injection one-shot task to swh.

"""

import click
import logging

from abc import ABCMeta, abstractmethod

from swh.core.config import SWHConfig
from swh.deposit.config import setup_django_for
from swh.model import hashutil


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

    def __init__(self):
        super().__init__()
        self.config = self.parse_config_file(
                additional_configs=[self.ADDITIONAL_CONFIG])
        self.log = logging.getLogger('swh.deposit.scheduling')

    def _aggregate_metadata(self, deposit, metadata_requests):
        """Retrieve and aggregates metadata information.

        """
        metadata = {}
        for req in metadata_requests:
            metadata.update(req.metadata)

        return metadata

    def aggregate(self, deposit, deposit_archive_url, requests):
        """Aggregate multiple data on deposit into one unified data dictionary.

        Args:
            deposit (Deposit): Deposit concerned by the data aggregation.
            deposit_archive_url (str): Url to retrieve a tarball from
                                       the deposit instance
            requests ([DepositRequest]): List of associated requests which
                                         need aggregation.

        Returns:
            Dictionary of data representing the deposit to inject in swh.

        """
        data = {}
        metadata_requests = []

        # Retrieve tarballs/metadata information
        metadata = self._aggregate_metadata(deposit, metadata_requests)

        data['deposit_archive_url'] = deposit_archive_url

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
        'task_name': ('str', 'swh.deposit.tasks.LoadDepositArchive'),
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
        deposit_archive_url = deposit_data['deposit_archive_url']
        origin = deposit_data['origin']
        visit_date = None  # default to Now
        revision = deposit_data['revision']

        if not self.dry_run:
            return self.task.delay(
                deposit_archive_url=deposit_archive_url,
                origin=origin,
                visit_date=visit_date,
                revision=revision)

        print(deposit_archive_url, origin, visit_date, revision)


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
@click.option('--scheduling-method', default='celery',
              help='Scheduling method')
@click.option('--server', default='http://127.0.0.1:5006',
              help='Deposit server')
def main(platform, scheduling_method, server):
    setup_django_for(platform)

    from swh.deposit.models import Deposit, DepositRequest, DepositRequestType

    if scheduling_method == 'celery':
        scheduling = SWHCeleryScheduling()
    elif scheduling_method == 'swh-scheduler':
        scheduling = SWHScheduling()
    else:
        raise ValueError(
            'Only `celery` or `swh-scheduler` values are accepted')

    from swh.deposit.config import DEPOSIT_RAW_CONTENT
    from django.core.urlresolvers import reverse

    _request_types = DepositRequestType.objects.all()
    deposit_request_types = {
        type.name: type for type in _request_types
    }

    deposits = Deposit.objects.filter(status='ready')
    for deposit in deposits:
        deposit_archive_url = '%s%s' % (server, reverse(
            DEPOSIT_RAW_CONTENT,
            args=[deposit.collection.name, deposit.id]))

        requests = DepositRequest.objects.filter(
            deposit=deposit, type=deposit_request_types['metadata'])

        deposit_data = scheduling.aggregate(
            deposit, deposit_archive_url, requests)

        scheduling.schedule(deposit_data)


if __name__ == '__main__':
    main()
