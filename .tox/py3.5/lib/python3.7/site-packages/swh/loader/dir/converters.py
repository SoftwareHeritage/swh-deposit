# Copyright (C) 2015-2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import datetime

from swh.model import hashutil


def to_datetime(ts):
    """Convert a timestamp to utc datetime.

    """
    return datetime.datetime.utcfromtimestamp(ts).replace(
        tzinfo=datetime.timezone.utc)


def format_to_minutes(offset_str):
    """Convert a git string timezone format string (e.g  +0200, -0310) to minutes.

    Args:
        offset_str: a string representing an offset.

    Returns:
        A positive or negative number of minutes of such input

    """
    sign = offset_str[0]
    hours = int(offset_str[1:3])
    minutes = int(offset_str[3:]) + (hours * 60)
    return minutes if sign == '+' else -1 * minutes


def commit_to_revision(commit, log=None):
    """Format a commit as a revision.

    """
    new_commit = commit.copy()
    new_commit.update({
        'author': {
            'name': commit['author']['name'].encode('utf-8'),
            'fullname': commit['author']['fullname'].encode('utf-8'),
            'email': commit['author']['email'].encode('utf-8'),
        },
        'committer': {
            'name': commit['committer']['name'].encode('utf-8'),
            'fullname': commit['committer']['fullname'].encode('utf-8'),
            'email': commit['committer']['email'].encode('utf-8'),
        },
        'message': commit['message'].encode('utf-8'),
        'synthetic': True,
    })

    if 'parents' in new_commit:
        new_commit['parents'] = [hashutil.hash_to_bytes(h)
                                 for h in new_commit['parents']]
    else:
        new_commit['parents'] = []

    return new_commit


def annotated_tag_to_release(release, log=None):
    """Format a swh release.

    """
    new_release = release.copy()
    new_release.update({
        'name': release['name'].encode('utf-8'),
        'author': {
            'name': release['author']['name'].encode('utf-8'),
            'fullname': release['author']['fullname'].encode('utf-8'),
            'email': release['author']['email'].encode('utf-8'),
        },
        'message': release['message'].encode('utf-8'),
        'synthetic': True
    })
    return new_release
