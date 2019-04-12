# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import click

from swh.deposit.config import setup_django_for
from swh.deposit.cli import cli


@cli.group('admin')
@click.option('--config-file', '-C', default=None,
              type=click.Path(exists=True, dir_okay=False,),
              help="Optional extra configuration file.")
@click.option('--platform', default='development',
              type=click.Choice(['development', 'production']),
              help='development or production platform')
@click.pass_context
def admin(ctx, config_file, platform):
    """Server administration tasks (manipulate user or collections)"""
    # configuration happens here
    setup_django_for(platform, config_file=config_file)


@admin.group('user')
@click.pass_context
def user(ctx):
    """Manipulate user."""
    # configuration happens here
    pass


def _create_collection(name):
    """Create the collection with name if it does not exist.

    Args:
        name (str): collection's name

    Returns:
        collection (DepositCollection): the existing collection object
                                        (created or not)

    """
    # to avoid loading too early django namespaces
    from swh.deposit.models import DepositCollection

    try:
        collection = DepositCollection.objects.get(name=name)
        click.echo('Collection %s exists, nothing to do.' % name)
    except DepositCollection.DoesNotExist:
        click.echo('Create new collection %s' % name)
        collection = DepositCollection.objects.create(name=name)
        click.echo('Collection %s created' % name)
    return collection


@user.command('create')
@click.option('--username', required=True, help="User's name")
@click.option('--password', required=True,
              help="Desired user's password (plain).")
@click.option('--firstname', default='', help="User's first name")
@click.option('--lastname', default='', help="User's last name")
@click.option('--email', default='', help="User's email")
@click.option('--collection', help="User's collection")
@click.option('--provider-url', default='', help="Provider URL")
@click.option('--domain', help="The domain")
@click.pass_context
def user_create(ctx, username, password, firstname, lastname, email,
                collection, provider_url, domain):
    """Create a user with some needed information (password, collection)

    If the collection does not exist, the collection is then created
    alongside.

    The password is stored encrypted using django's utilies.

    """
    # to avoid loading too early django namespaces
    from swh.deposit.models import DepositClient

    # If collection is not provided, fallback to username
    if not collection:
        collection = username
    click.echo('collection: %s' % collection)
    # create the collection if it does not exist
    collection = _create_collection(collection)

    # user create/update
    try:
        user = DepositClient.objects.get(username=username)
        click.echo('User %s exists, updating information.' % user)
        user.set_password(password)
    except DepositClient.DoesNotExist:
        click.echo('Create new user %s' % username)
        user = DepositClient.objects.create_user(
            username=username,
            password=password)

    user.collections = [collection.id]
    user.first_name = firstname
    user.last_name = lastname
    user.email = email
    user.is_active = True
    user.provider_url = provider_url
    user.domain = domain
    user.save()

    click.echo('Information registered for user %s' % user)


@user.command('list')
@click.pass_context
def user_list(ctx):
    """List existing users.

       This entrypoint is not paginated yet as there is not a lot of
       entry.

    """
    # to avoid loading too early django namespaces
    from swh.deposit.models import DepositClient
    users = DepositClient.objects.all()
    if not users:
        output = 'Empty user list'
    else:
        output = '\n'.join((user.username for user in users))
    click.echo(output)


@user.command('exists')
@click.argument('username', required=True)
@click.pass_context
def user_exists(ctx, username):
    """Check if user exists.
    """
    # to avoid loading too early django namespaces
    from swh.deposit.models import DepositClient
    try:
        DepositClient.objects.get(username=username)
        click.echo('User %s exists.' % username)
        ctx.exit(0)
    except DepositClient.DoesNotExist:
        click.echo('User %s does not exists.' % username)
        ctx.exit(1)


@admin.group('collection')
@click.pass_context
def collection(ctx):
    """Manipulate collections."""
    pass


@collection.command('create')
@click.option('--name', required=True, help="Collection's name")
@click.pass_context
def collection_create(ctx, name):
    _create_collection(name)


@collection.command('list')
@click.pass_context
def collection_list(ctx):
    """List existing collections.

       This entrypoint is not paginated yet as there is not a lot of
       entry.

    """
    # to avoid loading too early django namespaces
    from swh.deposit.models import DepositCollection
    collections = DepositCollection.objects.all()
    if not collections:
        output = 'Empty collection list'
    else:
        output = '\n'.join((col.name for col in collections))
    click.echo(output)
