# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of cleaning up temporary archives.  Temporary
archives being archives which were built from multiple ones, then
streamed back to the client and referenced for removal.

"""


import click
import datetime
import logging
import os
import shutil

from django.utils import timezone

from swh.deposit.config import setup_django_for


@click.command(
    help='Remove temporary archives from the production system.')
@click.option('--platform', default='development',
              help='development or production platform')
@click.option('--timeout', default='1 hour',
              help='Timeout after which the archive is deleted')
def main(platform, timeout):
    setup_django_for(platform)

    from swh.deposit.models import TemporaryArchive

    log = logging.getLogger('swh.deposit.service.clean_temporary_directory')

    # Retrieve old archives to be removed
    now = timezone.now()
    archives = TemporaryArchive.objects.filter(
        date__lte=now - datetime.timedelta(minutes=30))

    for archive in archives:
        path = archive.path
        if os.path.exists(path):
            try:
                log.info('Removing %s...' % path)
                shutil.rmtree(path)
            except:
                log.info('Error while removing %s..., skipping' % path)
                continue

        # remove reference to the archive
        log.info('Remove reference to archive id %s' % archive.id)
        archive.delete()


if __name__ == '__main__':
    main()
