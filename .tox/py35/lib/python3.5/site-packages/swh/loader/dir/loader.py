# Copyright (C) 2015-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import uuid

from swh.loader.core import loader
from swh.model.identifiers import (release_identifier, revision_identifier,
                                   snapshot_identifier, identifier_to_bytes)
from swh.model.from_disk import Directory

from . import converters


def revision_from(directory_hash, revision):
    full_rev = dict(revision)
    full_rev['directory'] = directory_hash
    full_rev = converters.commit_to_revision(full_rev)
    full_rev['id'] = identifier_to_bytes(revision_identifier(full_rev))
    return full_rev


def release_from(revision_hash, release):
    full_rel = dict(release)
    full_rel['target'] = revision_hash
    full_rel['target_type'] = 'revision'
    full_rel = converters.annotated_tag_to_release(full_rel)
    full_rel['id'] = identifier_to_bytes(release_identifier(full_rel))
    return full_rel


def snapshot_from(revision_hash, branch):
    """Build a snapshot from an origin, a visit, a revision, and a branch.

    """
    if isinstance(branch, str):
        branch = branch.encode('utf-8')

    snapshot = {
        'id': None,
        'branches': {
            branch: {
                'target': revision_hash,
                'target_type': 'revision',
            }
        }
    }
    snap_id = identifier_to_bytes(snapshot_identifier(snapshot))
    snapshot['id'] = snap_id
    return snapshot


class DirLoader(loader.SWHLoader):
    """A bulk loader for a directory."""
    CONFIG_BASE_FILENAME = 'loader/dir'

    def __init__(self, logging_class='swh.loader.dir.DirLoader',
                 config=None):
        super().__init__(logging_class=logging_class, config=config)

    def list_objs(self, *,
                  dir_path, revision, release, branch_name):
        """List all objects from dir_path.

        Args:
            dir_path (str): the directory to list
            revision (dict): revision dictionary representation
            release (dict): release dictionary representation
            branch_name (str): branch name

        Returns:
            dict: a mapping from object types ('content', 'directory',
            'revision', 'release', 'snapshot') with a dictionary
            mapping each object's id to the object

        """
        log_id = str(uuid.uuid4())
        sdir_path = dir_path.decode('utf-8')

        log_data = {
            'swh_type': 'dir_list_objs_end',
            'swh_repo': sdir_path,
            'swh_id': log_id,
        }

        self.log.debug("Started listing {swh_repo}".format(**log_data),
                       extra=log_data)

        directory = Directory.from_disk(path=dir_path, save_path=True)
        objects = directory.collect()

        full_rev = revision_from(directory.hash, revision)
        rev_id = full_rev['id']
        objects['revision'] = {
            rev_id: full_rev
        }

        objects['release'] = {}
        if release and 'name' in release:
            full_rel = release_from(rev_id, release)
            objects['release'][full_rel['id']] = full_rel

        snapshot = snapshot_from(rev_id, branch_name)
        objects['snapshot'] = {
            snapshot['id']: snapshot
        }

        log_data.update({
            'swh_num_%s' % key: len(values)
            for key, values in objects.items()
        })

        self.log.debug(("Done listing the objects in {swh_repo}: "
                        "{swh_num_content} contents, "
                        "{swh_num_directory} directories, "
                        "{swh_num_revision} revisions, "
                        "{swh_num_release} releases, "
                        "{swh_num_snapshot} snapshot").format(**log_data),
                       extra=log_data)

        return objects

    def load(self, *, dir_path, origin, visit_date, revision, release,
             branch_name=None):
        """Load the content of the directory to the archive.

        Args:
            dir_path: root of the directory to import
            origin (dict): an origin dictionary as returned by
              :func:`swh.storage.storage.Storage.origin_get_one`
            visit_date (str): the date the origin was visited (as an
              isoformatted string)
            revision (dict): a revision as passed to
              :func:`swh.storage.storage.Storage.revision_add`, excluding the
              `id` and `directory` keys (computed from the directory)
            release (dict): a release as passed to
              :func:`swh.storage.storage.Storage.release_add`, excluding the
              `id`, `target` and `target_type` keys (computed from the
              revision)'
            branch_name (str): the optional branch_name to use for snapshot

        """
        # Yes, this is entirely redundant, but it allows us to document the
        # arguments and the entry point.
        return super().load(dir_path=dir_path, origin=origin,
                            visit_date=visit_date, revision=revision,
                            release=release, branch_name=branch_name)

    def prepare_origin_visit(self, *, origin, visit_date=None, **kwargs):
        self.origin = origin
        self.visit_date = visit_date

    def prepare(self, *, dir_path, origin, revision, release, visit_date=None,
                branch_name=None):
        """Prepare the loader for directory loading.

        Args: identical to :func:`load`.

        """
        self.dir_path = dir_path
        self.revision = revision
        self.release = release

        branch = branch_name if branch_name else os.path.basename(dir_path)
        self.branch_name = branch

        if not os.path.exists(self.dir_path):
            warn_msg = 'Skipping inexistent directory %s' % self.dir_path
            self.log.error(warn_msg,
                           extra={
                               'swh_type': 'dir_repo_list_refs',
                               'swh_repo': self.dir_path,
                               'swh_num_refs': 0,
                           })
            raise ValueError(warn_msg)

        if isinstance(self.dir_path, str):
            self.dir_path = os.fsencode(self.dir_path)

    def cleanup(self):
        """Nothing to clean up.

        """
        pass

    def fetch_data(self):
        """Walk the directory, load all objects with their hashes.

        Sets self.objects reference with results.

        """
        self.objects = self.list_objs(dir_path=self.dir_path,
                                      revision=self.revision,
                                      release=self.release,
                                      branch_name=self.branch_name)

    def store_data(self):
        objects = self.objects
        self.maybe_load_contents(objects['content'].values())
        self.maybe_load_directories(objects['directory'].values())
        self.maybe_load_revisions(objects['revision'].values())
        self.maybe_load_releases(objects['release'].values())
        snapshot = list(objects['snapshot'].values())[0]
        self.maybe_load_snapshot(snapshot)


if __name__ == '__main__':
    import click
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(process)d %(message)s'
    )

    @click.command()
    @click.option('--dir-path', required=1, help='Directory path to load')
    @click.option('--origin-url', required=1,
                  help='Origin url for that directory')
    @click.option('--visit-date', default=None,
                  help='Visit date time override')
    def main(dir_path, origin_url, visit_date):
        """Loading directory tryout"""
        import datetime
        origin = {'url': origin_url, 'type': 'dir'}
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
            'message': 'swh-loader-dir: synthetic revision message',
            'metadata': {},
            'synthetic': True,
        }
        DirLoader().load(dir_path=dir_path, origin=origin,
                         visit_date=visit_date, revision=revision,
                         release=None)

    main()
