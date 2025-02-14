# Copyright (C) 2020-2025 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from importlib.metadata import PackageNotFoundError, distribution

try:
    __version__ = distribution("swh-deposit").version
except PackageNotFoundError:
    __version__ = "devel"
