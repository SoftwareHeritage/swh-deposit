# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import click

from swh.deposit.config import setup_django_for
from swh.deposit.models import DepositClient, DepositCollection


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--platform', default='development',
              help='development or production platform')
@click.pass_context
def cli(ctx, platform):
    setup_django_for(platform)


@cli.group('user')
@click.pass_context
def user(ctx):
    """Manipulate user."""
    pass


@user.command('create')
@click.option('--username', required=True, help="User's name")
@click.option('--password', required=True,
              help="Desired user's password (plain).")
@click.option('--firstname', default='', help="User's first name")
@click.option('--lastname', default='', help="User's last name")
@click.option('--email', default='', help="User's email")
@click.option('--collection', help="User's collection")
def create_user(username, password, firstname, lastname, email, collection):
    """Create a user with some needed information (password, collection)

    If the collection does not exist, the creation process is stopped.

    The password is stored encrypted using django's utilies.

    """

    try:
        collection = DepositCollection.objects.get(name=collection)
    except DepositCollection.DoesNotExist:
        raise ValueError(
            'Collection %s does not exist, skipping' % collection)

    # user create/update
    try:
        user = DepositClient.objects.get(username=username)
        click.echo_via_pager('User %s exists, updating information.' % user)
        user.set_password(password)
    except DepositClient.DoesNotExist:
        click.echo_via_pager('Create new user %s' % username)
        user = DepositClient.objects.create_user(
            username=username,
            password=password)

    user.collections = [collection.id]
    user.first_name = firstname
    user.last_name = lastname
    user.email = email
    user.is_active = True
    user.save()

    click.echo_via_pager('Information registered for user %s' % user)


def main():
    return cli(auto_envvar_prefix='SWH_DEPOSIT')


if __name__ == '__main__':
    main()
