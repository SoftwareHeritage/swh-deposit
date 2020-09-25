# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

# WARNING: do not import unnecessary things here to keep cli startup time under
# control
import click

from swh.core.cli import CONTEXT_SETTINGS
from swh.core.cli import swh as swh_cli_group

logger = logging.getLogger(__name__)


@swh_cli_group.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
def deposit(ctx):
    """Deposit main command
    """
    ctx.ensure_object(dict)
    log_level = ctx.obj.get("log_level", logging.INFO)
    logger.setLevel(log_level)


def main():
    logging.basicConfig()
    return deposit(auto_envvar_prefix="SWH_DEPOSIT")


# These import statements MUST be executed after defining the 'deposit' group
# since the subcommands in these are defined using this 'deposit' group.
from . import client  # noqa

try:
    from . import admin  # noqa
except ImportError:  # server part is optional
    logger.debug("admin subcommand not loaded")


if __name__ == "__main__":
    main()
