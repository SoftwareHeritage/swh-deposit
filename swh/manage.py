#!/usr/bin/env python3

# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import sys

from swh.core import config


DEFAULT_CONFIG = {
    'port': ('int', 5006),
    'host': ('str', '127.0.0.1'),
}


if __name__ == "__main__":
    # override the default host:port
    if sys.argv[1] == 'runserver':
        conf = config.load_named_config('deposit/server',
                                        default_conf=DEFAULT_CONFIG)
        extra_cmd = ['%s:%s' % (conf['host'], conf['port'])]
        cmd = sys.argv + extra_cmd
    else:
        cmd = sys.argv

    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "swh.deposit.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(cmd)
