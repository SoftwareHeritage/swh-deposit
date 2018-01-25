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


def parse_cli_options(archive, username, password, metadata,
                      binary_deposit, metadata_deposit,
                      collection, slug, partial, deposit_id, replace, url):
    """Parse the cli options and make sure the combination is acceptable.
       If not, an InputError exception is raised explaining the issue.

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

    """
    if binary_deposit and metadata_deposit:
        # too many flags use, remove redundant ones (-> multipart deposit)
        binary_deposit = False
        metadata_deposit = False

    if not os.path.exists(archive):
        raise InputError('Software Archive %s must exist!' % archive)

    if not metadata:
        metadata = '%s.metadata.xml' % archive

    if not binary_deposit and not os.path.exists(metadata):
        raise InputError('Software Archive metadata %s must exist!' % metadata)

    client = PublicApiDepositClient({
        'url': url,
        'auth': {
            'username': username,
            'password': password
        },
    })

        # retrieve user's collection
        sd_content = client.service_document()
        if 'error' in sd_content:
            raise InputError(sd_content['error'])
        collection = sd_content['collection'].replace('/', '')

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
    }


def make_deposit(config, dry_run, log):
    """Delegate the actual deposit to the deposit client.

    """
    log.debug('New deposit execution')

    client = config['client']
    collection = config['collection']
    archive_path = config['archive']
    metadata_path = config['metadata']
    slug = config['slug']
    in_progress = config['partial']
    client = config['client']
    if not dry_run:
        r = client.deposit(collection, archive_path, slug,
                           metadata_path, in_progress, log)
        return r
    return {}


@click.command(help='Software Heritage Deposit client')
@click.argument('archive', required=1)
@click.option('--username', required=1,
              help="(Mandatory) User's name")
@click.option('--password', required=1,
              help="(Mandatory) User's associated password")
@click.option('--metadata',
              help="(Optional) Path to xml metadata file. If not provided, this will use a file named <archive>.metadata.xml")  # noqa
@click.option('--binary-deposit/--no-binary-deposit', default=False,
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
@click.option('--url', default='http://localhost:5006/1',
              help="(Optional) Deposit server api endpoint. By default, https://deposit.softwareheritage.org/1")  # noqa
@click.option('--dry-run/--no-dry-run', default=False,
              help='(Optional) No-op deposit')
@click.option('--verbose/--no-verbose', default=False,
              help='Verbose mode')
def main(archive, username, password,
         metadata=None, binary_deposit=False, metadata_deposit=False,
         collection=None, slug=None, partial=False,
         deposit_id=None, replace=False,
         url='https://deposit.softwareheritage.org/1',
         dry_run=True, verbose=False):

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
            archive, username, password, metadata, binary_deposit,
            metadata_deposit, collection, slug, partial, deposit_id, url)

    except InputError as e:
        log.error('Problem during parsing options: %s' % e)
        return 1

    if verbose:
        log.info("Parsed configuration: %s" % (
            config, ))

    r = make_deposit(config, dry_run, log)
    if r:
        log.info(r)


if __name__ == '__main__':
    main()
