# Copyright (C) 2018 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def merge(dicts):
    """Given an iteratof of dicts, merge them losing no information.

    """
    d = {}
    for data in dicts:
        print(data)
        d.update(data)
    return d
