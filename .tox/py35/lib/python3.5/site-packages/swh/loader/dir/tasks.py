# Copyright (C) 2015-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.loader.dir.loader import DirLoader
from swh.scheduler.task import Task


class LoadDirRepository(Task):
    """Import a directory to Software Heritage

    """
    task_queue = 'swh_loader_dir'

    def run_task(self, *, dir_path, origin, visit_date, revision, release,
                 branch_name=None):
        """Import a directory dir_path with origin at visit_date time.
        Providing the revision, release, and occurrences.

        """
        loader = DirLoader()
        loader.log = self.log
        return loader.load(dir_path=dir_path, origin=origin,
                           visit_date=visit_date, revision=revision,
                           release=release, branch_name=branch_name)
