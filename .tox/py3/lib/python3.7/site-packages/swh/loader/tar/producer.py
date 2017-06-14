# Copyright (C) 2015-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import click
import dateutil.parser

from swh.scheduler.utils import get_task

from swh.core import config
from swh.loader.tar import build, file


TASK_QUEUE = 'swh.loader.tar.tasks.LoadTarRepository'


def produce_archive_messages_from(
        conf, root_dir, visit_date, mirror_file=None, dry_run=False):
    """From root_dir, produce archive tarball messages to celery.

    Will print error message when some computation arise on archive
    and continue.

    Args:
        conf: dictionary holding static metadata
        root_dir: top directory to list archives from.
        visit_date: override origin's visit date of information
        mirror_file: a filtering file of tarballs to load
        dry_run: will compute but not send messages

    Returns:
        Number of messages generated

    """

    limit = conf.get('limit')
    block = int(conf['block_messages'])
    count = 0

    path_source_tarballs = mirror_file if mirror_file else root_dir

    visit_date = dateutil.parser.parse(visit_date)
    if not dry_run:
        task = get_task(TASK_QUEUE)

    for tarpath, _ in file.random_archives_from(
            path_source_tarballs, block, limit):
        try:
            origin = build.compute_origin(
                conf['url_scheme'], conf['type'], root_dir, tarpath)
            revision = build.compute_revision(tarpath)

            if not dry_run:
                task.delay(tar_path=tarpath, origin=origin,
                           visit_date=visit_date,
                           revision=revision)

            count += 1
        except ValueError:
            print('Problem with the following archive: %s' % tarpath)

    return count


@click.command()
@click.option('--config-file', required=1,
              help='Configuration file path')
@click.option('--dry-run/--no-dry-run', default=False,
              help='Dry run (print repo only)')
@click.option('--limit', default=None,
              help='Number of origins limit to send')
def main(config_file, dry_run, limit):
    """Tarball producer of local fs tarballs.

    """
    conf = config.read(config_file)
    url_scheme = conf['url_scheme']
    mirror_dir = conf['mirror_root_directory']

    # remove trailing / in configuration (to ease ulterior computation)
    if url_scheme[-1] == '/':
        conf['url_scheme'] = url_scheme[0:-1]

    if mirror_dir[-1] == '/':
        conf['mirror_root_directory'] = mirror_dir[0:-1]

    if limit:
        conf['limit'] = int(limit)

    nb_tarballs = produce_archive_messages_from(
        conf=conf,
        root_dir=conf['mirror_root_directory'],
        visit_date=conf['date'],
        mirror_file=conf.get('mirror_subset_archives'),
        dry_run=dry_run)

    print('%s tarball(s) sent to worker.' % nb_tarballs)


if __name__ == '__main__':
    main()
