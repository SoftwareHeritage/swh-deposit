# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of sending deposit injection as celery task or
scheduled one-shot tasks.

"""

import click
import logging

from abc import ABCMeta, abstractmethod
from celery import group

from swh.core import utils
from swh.core.config import SWHConfig
from swh.deposit.config import setup_django_for, DEPOSIT_STATUS_READY


class SWHScheduling(SWHConfig, metaclass=ABCMeta):
    """Base swh scheduling class to aggregate the schedule deposit
       injection.

    """
    CONFIG_BASE_FILENAME = 'deposit/server'

    DEFAULT_CONFIG = {
        'dry_run': ('bool', False),
    }

    def __init__(self):
        super().__init__()
        self.config = self.parse_config_file(
                additional_configs=[self.ADDITIONAL_CONFIG])
        self.log = logging.getLogger('swh.deposit.scheduling')

    @abstractmethod
    def schedule(self, deposits):
        """Schedule the new deposit injection.

        Args:
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
    }

    def __init__(self, config=None):
        super().__init__()
        from swh.scheduler import utils
        self.task_name = self.config['task_name']
        self.task = utils.get_task(self.task_name)
        if config:
            self.config.update(**config)
        self.dry_run = self.config['dry_run']

    def _convert(self, deposits):
        """Convert tuple to celery task signature.

        """
        task = self.task
        for archive_url, deposit_meta_url, deposit_update_url in deposits:
            yield task.s(archive_url=archive_url,
                         deposit_meta_url=deposit_meta_url,
                         deposit_update_url=deposit_update_url)

    def schedule(self, deposits):
        """Schedule the new deposit injection directly through celery.

        Args:
            depositdata (dict): Deposit aggregated information.

        Returns:
            None

        """
        if self.dry_run:
            return

        return group(self._convert(deposits)).delay()


class SWHScheduling(SWHScheduling):
    """Deposit injection through SWH's task scheduling interface.

    """
    ADDITIONAL_CONFIG = {}

    def __init__(self, config=None):
        super().__init__()
        from swh.scheduler.backend import SchedulerBackend
        if config:
            self.config.update(**config)
        self.dry_run = self.config['dry_run']
        self.scheduler = SchedulerBackend(**self.config)

    def _convert(self, deposits):
        """Convert tuple to one-shot scheduling tasks.

        """
        import datetime
        for archive_url, deposit_meta_url, deposit_update_url in deposits:
            yield {
                'policy': 'oneshot',
                'type': 'swh-deposit-archive-ingestion',
                'next_run': datetime.datetime.now(tz=datetime.timezone.utc),
                'arguments': {
                    'args': [],
                    'kwargs': {
                        'archive_url': archive_url,
                        'deposit_meta_url': deposit_meta_url,
                        'deposit_update_url': deposit_update_url,
                    },
                }
            }

    def schedule(self, deposits):
        """Schedule the new deposit injection through swh.scheduler's api.

        Args:
            deposits (dict): Deposit aggregated information.

        """
        if self.dry_run:
            return

        self.scheduler.create_tasks(self._convert(deposits))


def get_deposit_ready():
    """Retrieve deposit ready to be task executed.

    """
    from swh.deposit.models import Deposit
    yield from Deposit.objects.filter(status=DEPOSIT_STATUS_READY)


def prepare_task_arguments(server):
    """Convert deposit to argument for task to be executed.

    """
    from swh.deposit.config import PRIVATE_GET_RAW_CONTENT
    from swh.deposit.config import PRIVATE_GET_DEPOSIT_METADATA
    from swh.deposit.config import PRIVATE_PUT_DEPOSIT
    from django.core.urlresolvers import reverse

    for deposit in get_deposit_ready():
        args = [deposit.collection.name, deposit.id]
        archive_url = '%s%s' % (server, reverse(
            PRIVATE_GET_RAW_CONTENT, args=args))
        deposit_meta_url = '%s%s' % (server, reverse(
            PRIVATE_GET_DEPOSIT_METADATA, args=args))
        deposit_update_url = '%s%s' % (server, reverse(
            PRIVATE_PUT_DEPOSIT, args=args))

        yield archive_url, deposit_meta_url, deposit_update_url


@click.command(
    help='Schedule one-shot deposit injections')
@click.option('--platform', default='development',
              help='development or production platform')
@click.option('--scheduling-method', default='celery',
              help='Scheduling method')
@click.option('--server', default='http://127.0.0.1:5006',
              help='Deposit server')
@click.option('--batch-size', default=1000, type=click.INT,
              help='Task batch size')
@click.option('--dry-run/--no-dry-run', is_flag=True, default=False,
              help='Dry run')
def main(platform, scheduling_method, server, batch_size, dry_run):
    setup_django_for(platform)

    override_config = {}
    if dry_run:
        override_config['dry_run'] = dry_run

    if scheduling_method == 'celery':
        scheduling = SWHCeleryScheduling(override_config)
    elif scheduling_method == 'swh-scheduler':
        scheduling = SWHScheduling(override_config)
    else:
        raise ValueError(
            'Only `celery` or `swh-scheduler` values are accepted')

    for deposits in utils.grouper(prepare_task_arguments(server), batch_size):
        scheduling.schedule(deposits)


if __name__ == '__main__':
    main()
