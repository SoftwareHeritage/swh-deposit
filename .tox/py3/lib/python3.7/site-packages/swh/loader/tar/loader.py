# Copyright (C) 2015-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


import os
import tempfile
import shutil

from swh.core import tarball
from swh.loader.core.loader import SWHLoader
from swh.loader.dir import loader
from swh.loader.tar import utils
from swh.model import hashutil


class TarLoader(loader.DirLoader):
    """Tarball loader implementation.

    This is a subclass of the :class:DirLoader as the main goal of
    this class is to first uncompress a tarball, then provide the
    uncompressed directory/tree to be loaded by the DirLoader.

    This will:

    - creates an origin (if it does not exist)
    - creates a fetch_history entry
    - creates an origin_visit
    - uncompress locally the tarball in a temporary location
    - process the content of the tarballs to persist on swh storage
    - clean up the temporary location
    - write an entry in fetch_history to mark the loading tarball end (success
      or failure)
    """
    CONFIG_BASE_FILENAME = 'loader/tar'

    ADDITIONAL_CONFIG = {
        'extraction_dir': ('string', '/tmp')
    }

    def __init__(self, logging_class='swh.loader.tar.TarLoader', config=None):
        super().__init__(logging_class=logging_class, config=config)
        self.dir_path = None

    def load(self, *, tar_path, origin, visit_date, revision,
             branch_name=None):
        """Load a tarball in `tarpath` in the Software Heritage Archive.

        Args:
            tar_path: tarball to import
            origin (dict): an origin dictionary as returned by
              :func:`swh.storage.storage.Storage.origin_get_one`
            visit_date (str): the date the origin was visited (as an
              isoformatted string)
            revision (dict): a revision as passed to
              :func:`swh.storage.storage.Storage.revision_add`, excluding the
              `id` and `directory` keys (computed from the directory)
            branch_name (str): the optional branch_name to use for snapshot

        """
        # Shortcut super() as we use different arguments than the DirLoader.
        return SWHLoader.load(self, tar_path=tar_path, origin=origin,
                              visit_date=visit_date, revision=revision,
                              branch_name=branch_name)

    def prepare_origin_visit(self, *, origin, visit_date=None, **kwargs):
        self.origin = origin
        if 'type' not in self.origin:  # let the type flow if present
            self.origin['type'] = 'tar'
        self.visit_date = visit_date

    def prepare(self, *, tar_path, origin, revision, visit_date=None,
                branch_name=None):
        """1. Uncompress the tarball in a temporary directory.
           2. Compute some metadata to update the revision.

        """
        # Prepare the extraction path
        extraction_dir = self.config['extraction_dir']
        os.makedirs(extraction_dir, 0o755, exist_ok=True)
        self.dir_path = tempfile.mkdtemp(prefix='swh.loader.tar-',
                                         dir=extraction_dir)

        # add checksums in revision

        self.log.info('Uncompress %s to %s' % (tar_path, self.dir_path))
        nature = tarball.uncompress(tar_path, self.dir_path)

        if 'metadata' not in revision:
            artifact = utils.convert_to_hex(hashutil.hash_path(tar_path))
            artifact['name'] = os.path.basename(tar_path)
            artifact['archive_type'] = nature
            artifact['length'] = os.path.getsize(tar_path)
            revision['metadata'] = {
                'original_artifact': [artifact],
            }

        branch = branch_name if branch_name else os.path.basename(tar_path)

        super().prepare(dir_path=self.dir_path,
                        origin=origin,
                        visit_date=visit_date,
                        revision=revision,
                        release=None,
                        branch_name=branch)

    def cleanup(self):
        """Clean up temporary directory where we uncompress the tarball.

        """
        if self.dir_path and os.path.exists(self.dir_path):
            shutil.rmtree(self.dir_path)


if __name__ == '__main__':
    import click
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(process)d %(message)s'
    )

    @click.command()
    @click.option('--archive-path', required=1, help='Archive path to load')
    @click.option('--origin-url', required=1, help='Origin url to associate')
    @click.option('--visit-date', default=None,
                  help='Visit date time override')
    def main(archive_path, origin_url, visit_date):
        """Loading archive tryout."""
        import datetime
        origin = {'url': origin_url, 'type': 'tar'}
        commit_time = int(datetime.datetime.now(
            tz=datetime.timezone.utc).timestamp())
        swh_person = {
            'name': 'Software Heritage',
            'fullname': 'Software Heritage',
            'email': 'robot@softwareheritage.org'
        }
        revision = {
            'date': {'timestamp': commit_time, 'offset': 0},
            'committer_date': {'timestamp': commit_time, 'offset': 0},
            'author': swh_person,
            'committer': swh_person,
            'type': 'tar',
            'message': 'swh-loader-tar: synthetic revision message',
            'metadata': {},
            'synthetic': True,
        }
        TarLoader().load(tar_path=archive_path, origin=origin,
                         visit_date=visit_date, revision=revision,
                         branch_name='master')

    main()
