# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of sending deposit loading/checking as either
celery task or scheduled one-shot tasks.

"""

import click
import logging

from abc import ABCMeta, abstractmethod
from celery import group

from swh.core import utils
from swh.core.config import SWHConfig
from swh.deposit.config import setup_django_for, DEPOSIT_STATUS_VERIFIED
from swh.deposit.config import DEPOSIT_STATUS_DEPOSITED
from swh.scheduler.utils import get_task, create_oneshot_task_dict


class SWHScheduling(SWHConfig, metaclass=ABCMeta):
    """Base swh scheduling class to aggregate the schedule deposit
       loading.

    """
    CONFIG_BASE_FILENAME = 'deposit/server'

    DEFAULT_CONFIG = {
        'dry_run': ('bool', False),
    }

    ADDITIONAL_CONFIG = {}

    def __init__(self):
        super().__init__()
        self.config = self.parse_config_file(
                additional_configs=[self.ADDITIONAL_CONFIG])
        self.log = logging.getLogger('swh.deposit.scheduling')

    @abstractmethod
    def schedule(self, deposits):
        """Schedule the new deposit loading.

        Args:
            data (dict): Deposit aggregated data

        Returns:
            None

        """
        pass


class SWHCeleryScheduling(SWHScheduling):
    """Deposit loading as Celery task scheduling.

    """
    def __init__(self, config=None):
        super().__init__()
        if config:
            self.config.update(**config)
        self.dry_run = self.config['dry_run']
        self.check = self.config['check']
        if self.check:
            task_name = 'swh.deposit.loader.tasks.ChecksDepositTsk'
        else:
            task_name = 'swh.deposit.loader.tasks.LoadDepositArchiveTsk'
        self.task = get_task(task_name)

    def _convert(self, deposits):
        """Convert tuple to celery task signature.

        """
        task = self.task
        for archive_url, meta_url, update_url, check_url in deposits:
            if self.check:
                yield task.s(deposit_check_url=check_url)
            else:
                yield task.s(archive_url=archive_url,
                             deposit_meta_url=meta_url,
                             deposit_update_url=update_url)

    def schedule(self, deposits):
        """Schedule the new deposit loading directly through celery.

        Args:
            depositdata (dict): Deposit aggregated information.

        Returns:
            None

        """
        if self.dry_run:
            return

        return group(self._convert(deposits)).delay()


class SWHSchedulerScheduling(SWHScheduling):
    """Deposit loading through SWH's task scheduling interface.

    """
    ADDITIONAL_CONFIG = {
        'scheduler': ('dict', {
            'cls': 'remote',
            'args': {
                'url': 'http://localhost:5008',
            }
        })
    }

    def __init__(self, config=None):
        super().__init__()
        from swh.scheduler import get_scheduler
        if config:
            self.config.update(**config)
        self.dry_run = self.config['dry_run']
        self.scheduler = get_scheduler(**self.config['scheduler'])
        self.check = self.config['check']

    def _convert(self, deposits):
        """Convert tuple to one-shot scheduling tasks.

        """
        for archive_url, meta_url, update_url, check_url in deposits:
            if self.check:
                task = create_oneshot_task_dict(
                    'swh-deposit-archive-checks',
                    deposit_check_url=check_url)
            else:
                task = create_oneshot_task_dict(
                    'swh-deposit-archive-loading',
                    archive_url=archive_url,
                    deposit_meta_url=meta_url,
                    deposit_update_url=update_url)

            yield task

    def schedule(self, deposits):
        """Schedule the new deposit loading through swh.scheduler's api.

        Args:
            deposits (dict): Deposit aggregated information.

        """
        if self.dry_run:
            return

        self.scheduler.create_tasks(self._convert(deposits))


def get_deposit_by(status):
    """Filter deposit given a specific status.

    """
    from swh.deposit.models import Deposit
    yield from Deposit.objects.filter(status=status)


def prepare_task_arguments(check):
    """Convert deposit to argument for task to be executed.

    """
    from swh.deposit.config import PRIVATE_GET_RAW_CONTENT
    from swh.deposit.config import PRIVATE_GET_DEPOSIT_METADATA
    from swh.deposit.config import PRIVATE_PUT_DEPOSIT
    from swh.deposit.config import PRIVATE_CHECK_DEPOSIT
    from django.core.urlresolvers import reverse

    if check:
        status = DEPOSIT_STATUS_DEPOSITED
    else:
        status = DEPOSIT_STATUS_VERIFIED

    for deposit in get_deposit_by(status):
        args = [deposit.collection.name, deposit.id]
        archive_url = reverse(PRIVATE_GET_RAW_CONTENT, args=args)
        meta_url = reverse(PRIVATE_GET_DEPOSIT_METADATA, args=args)
        update_url = reverse(PRIVATE_PUT_DEPOSIT, args=args)
        check_url = reverse(PRIVATE_CHECK_DEPOSIT, args=args)
        yield archive_url, meta_url, update_url, check_url


@click.command(
    help='Schedule one-shot deposit loadings')
@click.option('--platform', default='development',
              help='development or production platform')
@click.option('--scheduling-method', default='celery',
              help='Scheduling method')
@click.option('--batch-size', default=1000, type=click.INT,
              help='Task batch size')
@click.option('--dry-run/--no-dry-run', is_flag=True, default=False,
              help='Dry run')
@click.option('--check', is_flag=True, default=False)
def main(platform, scheduling_method, batch_size, dry_run, check):
    setup_django_for(platform)

    override_config = {}
    if dry_run:
        override_config['dry_run'] = dry_run
    override_config['check'] = check

    if scheduling_method == 'celery':
        scheduling = SWHCeleryScheduling(override_config)
    elif scheduling_method == 'swh-scheduler':
        scheduling = SWHSchedulerScheduling(override_config)
    else:
        raise ValueError(
            'Only `celery` or `swh-scheduler` values are accepted')

    for deposits in utils.grouper(prepare_task_arguments(check), batch_size):
        scheduling.schedule(deposits)


if __name__ == '__main__':
    main()
