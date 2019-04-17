# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import click
import logging

logger = logging.getLogger(__name__)


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--log-level', '-l', default='INFO',
              type=click.Choice(logging._nameToLevel.keys()),
              help="Log level (default to INFO)")
@click.pass_context
def cli(ctx, log_level):
    logger.setLevel(log_level)
    ctx.ensure_object(dict)


def main():
    logging.basicConfig()
    from . import deposit  # noqa
    try:
        from . import admin  # noqa
    except ImportError:  # server part is optional
        pass

    return cli(auto_envvar_prefix='SWH_DEPOSIT')


if __name__ == '__main__':
    main()
