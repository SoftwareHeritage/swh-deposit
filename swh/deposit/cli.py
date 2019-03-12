# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import click
import os
import logging
import uuid

from swh.deposit.config import setup_django_for
try:
    from swh.deposit.client import PublicApiDepositClient
except ImportError:
    logging.warn("Optional client subcommand unavailable. "
                 "Install swh.deposit.client to be able to use it.")


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--config-file', '-C', default=None,
              type=click.Path(exists=True, dir_okay=False,),
              help="Optional extra configuration file.")
@click.option('--platform', default='development',
              type=click.Choice(['development', 'production']),
              help='development or production platform')
@click.option('--verbose/--no-verbose', default=False,
              help='Verbose mode')
@click.pass_context
def cli(ctx, config_file, platform, verbose):
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.StreamHandler())
    _loglevel = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(_loglevel)

    ctx.ensure_object(dict)

    # configuration happens here
    setup_django_for(platform, config_file=config_file)

    ctx.obj = {'loglevel': _loglevel}


@cli.group('user')
@click.pass_context
def user(ctx):
    """Manipulate user."""
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
@click.pass_context
def user_create(ctx, username, password, firstname, lastname, email,
                collection):
    """Create a user with some needed information (password, collection)

    If the collection does not exist, the collection is then created
    alongside.

    The password is stored encrypted using django's utilies.

    """
    # to avoid loading too early django namespaces
    from swh.deposit.models import DepositClient

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


@cli.group('collection')
@click.pass_context
def collection(ctx):
    """Manipulate collection."""
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


class InputError(ValueError):
    """Input script error

    """
    pass


def generate_slug(prefix='swh-sample'):
    """Generate a slug (sample purposes).

    """
    return '%s-%s' % (prefix, uuid.uuid4())


def client_command_parse_input(
        username, password, archive, metadata,
        archive_deposit, metadata_deposit,
        collection, slug, partial, deposit_id, replace,
        url, status):
    """Parse the client subcommand options and make sure the combination
       is acceptable*.  If not, an InputError exception is raised
       explaining the issue.

       By acceptable, we mean:

           - A multipart deposit (create or update) needs both an
             existing software archive and an existing metadata file

           - A binary deposit (create/update) needs an existing
             software archive

           - A metadata deposit (create/update) needs an existing
             metadata file

           - A deposit update needs a deposit_id to be provided

        This won't prevent all failure cases though. The remaining
        errors are already dealt with the underlying api client.

    Raises:
        InputError explaining the issue

    Returns:
        dict with the following keys:

            'archive': the software archive to deposit
            'username': username
            'password': associated password
            'metadata': the metadata file to deposit
            'collection': the username's associated client
            'slug': the slug or external id identifying the deposit to make
            'partial': if the deposit is partial or not
            'client': instantiated class
            'url': deposit's server main entry point
            'deposit_type': deposit's type (binary, multipart, metadata)
            'deposit_id': optional deposit identifier

    """
    if status and not deposit_id:
        raise InputError("Deposit id must be provided for status check")

    if status and deposit_id:  # status is higher priority over deposit
        archive_deposit = False
        metadata_deposit = False
        archive = None
        metadata = None

    if archive_deposit and metadata_deposit:
        # too many flags use, remove redundant ones (-> multipart deposit)
        archive_deposit = False
        metadata_deposit = False

    if archive and not os.path.exists(archive):
        raise InputError('Software Archive %s must exist!' % archive)

    if archive and not metadata:
        metadata = '%s.metadata.xml' % archive

    if metadata_deposit:
        archive = None

    if archive_deposit:
        metadata = None

    if metadata_deposit and not metadata:
        raise InputError(
            "Metadata deposit filepath must be provided for metadata deposit")

    if metadata and not os.path.exists(metadata):
        raise InputError('Software Archive metadata %s must exist!' % metadata)

    if not status and not archive and not metadata:
        raise InputError(
            'Please provide an actionable command. See --help for more '
            'information.')

    if replace and not deposit_id:
        raise InputError(
            'To update an existing deposit, you must provide its id')

    client = PublicApiDepositClient({
        'url': url,
        'auth': {
            'username': username,
            'password': password
        },
    })

    if not collection:
        # retrieve user's collection
        sd_content = client.service_document()
        if 'error' in sd_content:
            raise InputError('Service document retrieval: %s' % (
                sd_content['error'], ))
        collection = sd_content['collection']

    if not slug:
        # generate slug
        slug = generate_slug()

    return {
        'archive': archive,
        'username': username,
        'password': password,
        'metadata': metadata,
        'collection': collection,
        'slug': slug,
        'partial': partial,
        'client': client,
        'url': url,
        'deposit_id': deposit_id,
        'replace': replace,
    }


def deposit_status(config, dry_run, logger):
    logger.debug('Status deposit')
    client = config['client']
    collection = config['collection']
    deposit_id = config['deposit_id']
    if not dry_run:
        r = client.deposit_status(collection, deposit_id, logger)
        return r
    return {}


def deposit_create(config, dry_run, logger):
    """Delegate the actual deposit to the deposit client.

    """
    logger.debug('Create deposit')

    client = config['client']
    collection = config['collection']
    archive_path = config['archive']
    metadata_path = config['metadata']
    slug = config['slug']
    in_progress = config['partial']
    if not dry_run:
        r = client.deposit_create(collection, slug, archive_path,
                                  metadata_path, in_progress, logger)
        return r
    return {}


def deposit_update(config, dry_run, logger):
    """Delegate the actual deposit to the deposit client.

    """
    logger.debug('Update deposit')

    client = config['client']
    collection = config['collection']
    deposit_id = config['deposit_id']
    archive_path = config['archive']
    metadata_path = config['metadata']
    slug = config['slug']
    in_progress = config['partial']
    replace = config['replace']
    if not dry_run:
        r = client.deposit_update(collection, deposit_id, slug, archive_path,
                                  metadata_path, in_progress, replace, logger)
        return r
    return {}


@cli.command()
@click.option('--username', required=1,
              help="(Mandatory) User's name")
@click.option('--password', required=1,
              help="(Mandatory) User's associated password")
@click.option('--archive',
              help='(Optional) Software archive to deposit')
@click.option('--metadata',
              help="(Optional) Path to xml metadata file. If not provided, this will use a file named <archive>.metadata.xml")  # noqa
@click.option('--archive-deposit/--no-archive-deposit', default=False,
              help='(Optional) Software archive only deposit')
@click.option('--metadata-deposit/--no-metadata-deposit', default=False,
              help='(Optional) Metadata only deposit')
@click.option('--collection',
              help="(Optional) User's collection. If not provided, this will be fetched.")  # noqa
@click.option('--slug',
              help="""(Optional) External system information identifier. If not provided, it will be generated""")  # noqa
@click.option('--partial/--no-partial', default=False,
              help='(Optional) The deposit will be partial, other deposits will have to take place to finalize it.')  # noqa
@click.option('--deposit-id', default=None,
              help='(Optional) Update an existing partial deposit with its identifier')  # noqa
@click.option('--replace/--no-replace', default=False,
              help='(Optional) Update by replacing existing metadata to a deposit')  # noqa
@click.option('--url', default='https://deposit.softwareheritage.org/1',
              help="(Optional) Deposit server api endpoint. By default, https://deposit.softwareheritage.org/1")  # noqa
@click.option('--status/--no-status', default=False,
              help="(Optional) Deposit's status")
@click.option('--dry-run/--no-dry-run', default=False,
              help='(Optional) No-op deposit')
@click.option('--verbose/--no-verbose', default=False,
              help='Verbose mode')
@click.pass_context
def client(ctx,
           username, password, archive=None, metadata=None,
           archive_deposit=False, metadata_deposit=False,
           collection=None, slug=None, partial=False, deposit_id=None,
           replace=False, status=False,
           url='https://deposit.softwareheritage.org/1', dry_run=True,
           verbose=False):
    """Software Heritage Public Deposit Client

    Create/Update deposit through the command line or access its
    status.

More documentation can be found at
https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html.

    """
    logger = logging.getLogger(__name__)

    if dry_run:
        logger.info("**DRY RUN**")

    config = {}

    try:
        logger.debug('Parsing cli options')
        config = client_command_parse_input(
            username, password, archive, metadata, archive_deposit,
            metadata_deposit, collection, slug, partial, deposit_id,
            replace, url, status)

    except InputError as e:
        msg = 'Problem during parsing options: %s' % e
        r = {
            'error': msg,
        }
        logger.info(r)
        return 1

    if verbose:
        logger.info("Parsed configuration: %s" % (
            config, ))

    deposit_id = config['deposit_id']

    if status and deposit_id:
        r = deposit_status(config, dry_run, logger)
    elif not status and deposit_id:
        r = deposit_update(config, dry_run, logger)
    elif not status and not deposit_id:
        r = deposit_create(config, dry_run, logger)

    logger.info(r)


def main():
    return cli(auto_envvar_prefix='SWH_DEPOSIT')


if __name__ == '__main__':
    main()
