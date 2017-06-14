# Copyright (C) 2015-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os

from swh.core import utils


# Static setup
EPOCH = 0
UTC_OFFSET = 0
SWH_PERSON = {
    'name': 'Software Heritage',
    'fullname': 'Software Heritage',
    'email': 'robot@softwareheritage.org'
}
REVISION_MESSAGE = 'synthetic revision message'
REVISION_TYPE = 'tar'


def compute_origin(url_scheme, url_type, root_dirpath, tarpath):
    """Compute the origin.

    Args:
        - url_scheme: scheme to build the origin's url
        - url_type: origin's type
        - root_dirpath: the top level root directory path
        - tarpath: file's absolute path

    Returns:
        Dictionary origin with keys:
       - url: origin's url
       - type: origin's type

    """
    relative_path = utils.commonname(root_dirpath, tarpath)
    return {
        'url': ''.join([url_scheme,
                        os.path.dirname(relative_path)]),
        'type': url_type,
    }


def _time_from_path(tarpath):
    """Compute the modification time from the tarpath.

    Args:
        tarpath (str|bytes): Full path to the archive to extract the
        date from.

    Returns:
        dict representing a timestamp with keys seconds and microseconds keys.

    """
    mtime = os.lstat(tarpath).st_mtime
    if isinstance(mtime, float):
        normalized_time = list(map(int, str(mtime).split('.')))
    else:  # assuming int
        normalized_time = [mtime, 0]

    return {
        'seconds': normalized_time[0],
        'microseconds': normalized_time[1]
    }


def compute_revision(tarpath):
    """Compute a revision.

    Args:
        tarpath: absolute path to the tarball

    Returns:
        Revision as dict:
        - date (dict): the modification timestamp as returned by
                       _time_from_path function
        - committer_date: the modification timestamp as returned by
                       _time_from_path function
        - author: cf. SWH_PERSON
        - committer: cf. SWH_PERSON
        - type: cf. REVISION_TYPE
        - message: cf. REVISION_MESSAGE

    """
    ts = _time_from_path(tarpath)
    return {
        'date': {
            'timestamp': ts,
            'offset': UTC_OFFSET,
        },
        'committer_date': {
            'timestamp': ts,
            'offset': UTC_OFFSET,
        },
        'author': SWH_PERSON,
        'committer': SWH_PERSON,
        'type': REVISION_TYPE,
        'message': REVISION_MESSAGE,
    }
