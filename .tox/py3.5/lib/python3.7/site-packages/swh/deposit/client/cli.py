# Copyright (C) 2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""Script to demonstrate software deposit scenario to
https://deposit.sofwareheritage.org.

Use: python3 -m swh.deposit.client.cli --help

Documentation: https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html  # noqa

"""

import os
import click
import logging
import uuid


from . import PublicApiDepositClient


class InputError(ValueError):
    """Input script error

    """
    pass


def generate_slug(prefix='swh-sample'):
    """Generate a slug (sample purposes).

    """
    return '%s-%s' % (prefix, uuid.uuid4())


def parse_cli_options(username, password, archive, metadata,
                      archive_deposit, metadata_deposit,
                      collection, slug, partial, deposit_id, replace,
                      url, status):
    """Parse the cli options and make sure the combination is acceptable*.
       If not, an InputError exception is raised explaining the issue.

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


def deposit_status(config, dry_run, log):
    log.debug('Status deposit')
    client = config['client']
    collection = config['collection']
    deposit_id = config['deposit_id']
    if not dry_run:
        r = client.deposit_status(collection, deposit_id, log)
        return r
    return {}


def deposit_create(config, dry_run, log):
    """Delegate the actual deposit to the deposit client.

    """
    log.debug('Create deposit')

    client = config['client']
    collection = config['collection']
    archive_path = config['archive']
    metadata_path = config['metadata']
    slug = config['slug']
    in_progress = config['partial']
    if not dry_run:
        r = client.deposit_create(collection, slug, archive_path,
                                  metadata_path, in_progress, log)
        return r
    return {}


def deposit_update(config, dry_run, log):
    """Delegate the actual deposit to the deposit client.

    """
    log.debug('Update deposit')

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
                                  metadata_path, in_progress, replace, log)
        return r
    return {}


@click.command()
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
def main(username, password, archive=None, metadata=None,
         archive_deposit=False, metadata_deposit=False,
         collection=None, slug=None, partial=False, deposit_id=None,
         replace=False, status=False,
         url='https://deposit.softwareheritage.org/1', dry_run=True,
         verbose=False):
    """Software Heritage Deposit client - Create (or update partial)
deposit through the command line.

More documentation can be found at
https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html.

    """

    log = logging.getLogger('swh-deposit')
    log.addHandler(logging.StreamHandler())
    _loglevel = logging.DEBUG if verbose else logging.INFO
    log.setLevel(_loglevel)

    if dry_run:
        log.info("**DRY RUN**")

    config = {}

    try:
        log.debug('Parsing cli options')
        config = parse_cli_options(
            username, password, archive, metadata, archive_deposit,
            metadata_deposit, collection, slug, partial, deposit_id,
            replace, url, status)

    except InputError as e:
        msg = 'Problem during parsing options: %s' % e
        r = {
            'error': msg,
        }
        log.info(r)
        return 1

    if verbose:
        log.info("Parsed configuration: %s" % (
            config, ))

    deposit_id = config['deposit_id']

    if status and deposit_id:
        r = deposit_status(config, dry_run, log)
    elif not status and deposit_id:
        r = deposit_update(config, dry_run, log)
    elif not status and not deposit_id:
        r = deposit_create(config, dry_run, log)

    log.info(r)


if __name__ == '__main__':
    main()
