# Copyright (C) 2015-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.task import Task

from swh.loader.tar.loader import TarLoader


class LoadTarRepository(Task):
    """Import a directory to Software Heritage

    """
    task_queue = 'swh_loader_tar'

    def run_task(self, *, tar_path, origin, visit_date, revision,
                 branch_name=None):
        """Import a tarball into swh.

        Args: see :func:`TarLoader.load`.
        """
        loader = TarLoader()
        loader.log = self.log
        return loader.load(tar_path=tar_path, origin=origin,
                           visit_date=visit_date, revision=revision,
                           branch_name=branch_name)
