# Copyright (C) 2015-2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import itertools
import os

from swh.core import tarball
from swh.loader.tar import utils


def archives_from_dir(path):
    """Given a path to a directory, walk such directory and yield tuple of
    tarpath, fname.

    Args:
        path: top level directory

    Returns:
        Generator of tuple tarpath, filename with tarpath a tarball.

    """
    for dirpath, dirnames, filenames in os.walk(path):
        for fname in filenames:
            tarpath = os.path.join(dirpath, fname)
            if not os.path.exists(tarpath):
                continue

            if tarball.is_tarball(tarpath):
                yield tarpath, fname


def archives_from_file(mirror_file):
    """Given a path to a file containing one tarball per line, yield a tuple of
    tarpath, fname.

    Args:
        mirror_file: path to the file containing list of tarpath.

    Returns:
        Generator of tuple tarpath, filename with tarpath a tarball.

    """
    with open(mirror_file, 'r') as f:
        for tarpath in f.readlines():
            tarpath = tarpath.strip()
            if not os.path.exists(tarpath):
                print('WARN: %s does not exist. Skipped.' % tarpath)
                continue

            if tarball.is_tarball(tarpath):
                yield tarpath, os.path.basename(tarpath)


def archives_from(path):
    """From path, list tuple of tarpath, fname.

    Args:
        path: top directory to list archives from or custom file format.

    Returns:
        Generator of tuple tarpath, filename with tarpath a tarball.

    """
    if os.path.isfile(path):
        yield from archives_from_file(path)
    elif os.path.isdir(path):
        yield from archives_from_dir(path)
    else:
        raise ValueError(
            'Input incorrect, %s must be a file or a directory.' % path)


def random_archives_from(path, block, limit=None):
    """Randomize by size block the archives.

    Returns:
        Generator of randomized tuple tarpath, filename with tarpath a tarball.

    """
    random_archives = utils.random_blocks(archives_from(path),
                                          block,
                                          fillvalue=(None, None))

    if limit:
        random_archives = itertools.islice(random_archives, limit)

    for tarpath, fname in ((t, f) for t, f in random_archives if t and f):
        yield tarpath, fname
