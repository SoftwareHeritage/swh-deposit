# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import click
import logging


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--verbose/--no-verbose', default=False,
              help='Verbose mode')
@click.pass_context
def cli(ctx, verbose):
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.StreamHandler())
    _loglevel = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(_loglevel)

    ctx.ensure_object(dict)
    ctx.obj = {'loglevel': _loglevel,
               'logger': logger}


def main():
    from . import deposit  # noqa
    try:
        from . import server  # noqa
    except ImportError:  # server part is optional
        pass

    return cli(auto_envvar_prefix='SWH_DEPOSIT')


if __name__ == '__main__':
    main()
