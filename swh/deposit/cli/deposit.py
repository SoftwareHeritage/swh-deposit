# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
import os
import uuid

import click

from swh.deposit.client import PublicApiDepositClient
from swh.deposit.cli import cli


logger = logging.getLogger(__name__)


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
        collection = sd_content[
            'service']['workspace']['collection']['sword:name']

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
        'in_progress': partial,
        'client': client,
        'url': url,
        'deposit_id': deposit_id,
        'replace': replace,
    }


def _subdict(d, keys):
    'return a dict from d with only given keys'
    return {k: v for k, v in d.items() if k in keys}


def deposit_status(config, logger):
    logger.debug('Status deposit')
    keys = ('collection', 'deposit_id')
    client = config['client']
    return client.deposit_status(
        **_subdict(config, keys))


def deposit_create(config, logger):
    """Delegate the actual deposit to the deposit client.

    """
    logger.debug('Create deposit')

    client = config['client']
    keys = ('collection', 'archive', 'metadata', 'slug', 'in_progress')
    return client.deposit_create(
        **_subdict(config, keys))


def deposit_update(config, logger):
    """Delegate the actual deposit to the deposit client.

    """
    logger.debug('Update deposit')

    client = config['client']
    keys = ('collection', 'deposit_id', 'archive', 'metadata',
            'slug', 'in_progress', 'replace')
    return client.deposit_update(
        **_subdict(config, keys))


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
@click.option('--verbose/--no-verbose', default=False,
              help='Verbose mode')
@click.pass_context
def deposit(ctx,
            username, password, archive=None, metadata=None,
            archive_deposit=False, metadata_deposit=False,
            collection=None, slug=None, partial=False, deposit_id=None,
            replace=False, status=False,
            url='https://deposit.softwareheritage.org/1',
            verbose=False):
    """Software Heritage Public Deposit Client

    Create/Update deposit through the command line or access its
    status.

More documentation can be found at
https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html.

    """
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
        r = deposit_status(config, logger)
    elif not status and deposit_id:
        r = deposit_update(config, logger)
    elif not status and not deposit_id:
        r = deposit_create(config, logger)

    logger.info(r)
