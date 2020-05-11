# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import logging
import sys
import tempfile
import uuid
import json
import yaml

import click
import xmltodict

from swh.deposit.client import PublicApiDepositClient, MaintenanceError
from swh.deposit.cli import deposit


logger = logging.getLogger(__name__)


class InputError(ValueError):
    """Input script error

    """

    pass


def generate_slug():
    """Generate a slug (sample purposes).

    """
    return str(uuid.uuid4())


def _url(url):
    """Force the /1 api version at the end of the url (avoiding confusing
       issues without it).

    Args:
        url (str): api url used by cli users

    Returns:
        Top level api url to actually request

    """
    if not url.endswith("/1"):
        url = "%s/1" % url
    return url


def generate_metadata_file(name, external_id, authors, temp_dir):
    """Generate a temporary metadata file with the minimum required metadata

    This generates a xml file in a temporary location and returns the
    path to that file.

    This is up to the client of that function to clean up the
    temporary file.

    Args:
        name (str): Software's name
        external_id (str): External identifier (slug) or generated one
        authors (List[str]): List of author names

    Returns:
        Filepath to the metadata generated file

    """
    path = os.path.join(temp_dir, "metadata.xml")
    # generate a metadata file with the minimum required metadata
    codemetadata = {
        "entry": {
            "@xmlns": "http://www.w3.org/2005/Atom",
            "@xmlns:codemeta": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0",
            "codemeta:name": name,
            "codemeta:identifier": external_id,
            "codemeta:author": [
                {"codemeta:name": author_name} for author_name in authors
            ],
        },
    }

    logging.debug("Temporary file: %s", path)
    logging.debug("Metadata dict to generate as xml: %s", codemetadata)
    s = xmltodict.unparse(codemetadata, pretty=True)
    logging.debug("Metadata dict as xml generated: %s", s)
    with open(path, "w") as fp:
        fp.write(s)
    return path


def _client(url, username, password):
    """Instantiate a client to access the deposit api server

    Args:
        url (str): Deposit api server
        username (str): User
        password (str): User's password

    """
    client = PublicApiDepositClient(
        {"url": url, "auth": {"username": username, "password": password},}
    )
    return client


def _collection(client):
    """Retrieve the client's collection

    """
    # retrieve user's collection
    sd_content = client.service_document()
    if "error" in sd_content:
        raise InputError("Service document retrieval: %s" % (sd_content["error"],))
    collection = sd_content["service"]["workspace"]["collection"]["sword:name"]
    return collection


def client_command_parse_input(
    username,
    password,
    archive,
    metadata,
    archive_deposit,
    metadata_deposit,
    collection,
    slug,
    partial,
    deposit_id,
    replace,
    url,
    name,
    authors,
    temp_dir,
):
    """Parse the client subcommand options and make sure the combination
       is acceptable*.  If not, an InputError exception is raised
       explaining the issue.

       By acceptable, we mean:

           - A multipart deposit (create or update) requires:

             - an existing software archive
             - an existing metadata file or author(s) and name provided in
               params

           - A binary deposit (create/update) requires an existing software
             archive

           - A metadata deposit (create/update) requires an existing metadata
             file or author(s) and name provided in params

           - A deposit update requires a deposit_id

        This will not prevent all failure cases though. The remaining
        errors are already dealt with by the underlying api client.

    Raises:
        InputError explaining the user input related issue
        MaintenanceError explaining the api status

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
    if archive_deposit and metadata_deposit:
        # too many flags use, remove redundant ones (-> multipart deposit)
        archive_deposit = False
        metadata_deposit = False

    if not slug:  # generate one as this is mandatory
        slug = generate_slug()

    if not metadata:
        if name and authors:
            metadata = generate_metadata_file(name, slug, authors, temp_dir)
        elif not archive_deposit and not partial and not deposit_id:
            # If we meet all the following conditions:
            # * there is not an archive-only deposit
            # * it is not part of a multipart deposit (either create/update
            #   or finish)
            # * it misses either name or authors
            raise InputError(
                "Either a metadata file (--metadata) or both --author and "
                "--name must be provided, unless this is an archive-only "
                "deposit."
            )
        elif name or authors:
            # If we are generating metadata, then all mandatory metadata
            # must be present
            raise InputError(
                "Either a metadata file (--metadata) or both --author and "
                "--name must be provided."
            )
        else:
            # TODO: this is a multipart deposit, we might want to check that
            # metadata are deposited at some point
            pass
    elif name or authors:
        raise InputError(
            "Using a metadata file (--metadata) is incompatible with "
            "--author and --name, which are used to generate one."
        )

    if metadata_deposit:
        archive = None

    if archive_deposit:
        metadata = None

    if metadata_deposit and not metadata:
        raise InputError(
            "Metadata deposit must be provided for metadata "
            "deposit (either a filepath or --name and --author)"
        )

    if not archive and not metadata and partial:
        raise InputError(
            "Please provide an actionable command. See --help for more " "information"
        )

    if replace and not deposit_id:
        raise InputError("To update an existing deposit, you must provide its id")

    client = _client(url, username, password)

    if not collection:
        collection = _collection(client)

    return {
        "archive": archive,
        "username": username,
        "password": password,
        "metadata": metadata,
        "collection": collection,
        "slug": slug,
        "in_progress": partial,
        "client": client,
        "url": url,
        "deposit_id": deposit_id,
        "replace": replace,
    }


def _subdict(d, keys):
    "return a dict from d with only given keys"
    return {k: v for k, v in d.items() if k in keys}


def deposit_create(config, logger):
    """Delegate the actual deposit to the deposit client.

    """
    logger.debug("Create deposit")

    client = config["client"]
    keys = ("collection", "archive", "metadata", "slug", "in_progress")
    return client.deposit_create(**_subdict(config, keys))


def deposit_update(config, logger):
    """Delegate the actual deposit to the deposit client.

    """
    logger.debug("Update deposit")

    client = config["client"]
    keys = (
        "collection",
        "deposit_id",
        "archive",
        "metadata",
        "slug",
        "in_progress",
        "replace",
    )
    return client.deposit_update(**_subdict(config, keys))


@deposit.command()
@click.option("--username", required=True, help="(Mandatory) User's name")
@click.option(
    "--password", required=True, help="(Mandatory) User's associated password"
)
@click.option(
    "--archive",
    type=click.Path(exists=True),
    help="(Optional) Software archive to deposit",
)
@click.option(
    "--metadata",
    type=click.Path(exists=True),
    help=(
        "(Optional) Path to xml metadata file. If not provided, "
        "this will use a file named <archive>.metadata.xml"
    ),
)  # noqa
@click.option(
    "--archive-deposit/--no-archive-deposit",
    default=False,
    help="(Optional) Software archive only deposit",
)
@click.option(
    "--metadata-deposit/--no-metadata-deposit",
    default=False,
    help="(Optional) Metadata only deposit",
)
@click.option(
    "--collection",
    help="(Optional) User's collection. If not provided, this will be fetched.",
)  # noqa
@click.option(
    "--slug",
    help=(
        "(Optional) External system information identifier. "
        "If not provided, it will be generated"
    ),
)  # noqa
@click.option(
    "--partial/--no-partial",
    default=False,
    help=(
        "(Optional) The deposit will be partial, other deposits "
        "will have to take place to finalize it."
    ),
)  # noqa
@click.option(
    "--deposit-id",
    default=None,
    help="(Optional) Update an existing partial deposit with its identifier",
)  # noqa
@click.option(
    "--replace/--no-replace",
    default=False,
    help="(Optional) Update by replacing existing metadata to a deposit",
)  # noqa
@click.option(
    "--url",
    default="https://deposit.softwareheritage.org",
    help=(
        "(Optional) Deposit server api endpoint. By default, "
        "https://deposit.softwareheritage.org/1"
    ),
)  # noqa
@click.option("--verbose/--no-verbose", default=False, help="Verbose mode")
@click.option("--name", help="Software name")
@click.option(
    "--author",
    multiple=True,
    help="Software author(s), this can be repeated as many times"
    " as there are authors",
)
@click.option(
    "-f",
    "--format",
    "output_format",
    default="logging",
    type=click.Choice(["logging", "yaml", "json"]),
    help="Output format results.",
)
@click.pass_context
def upload(
    ctx,
    username,
    password,
    archive=None,
    metadata=None,
    archive_deposit=False,
    metadata_deposit=False,
    collection=None,
    slug=None,
    partial=False,
    deposit_id=None,
    replace=False,
    url="https://deposit.softwareheritage.org",
    verbose=False,
    name=None,
    author=None,
    output_format=None,
):
    """Software Heritage Public Deposit Client

    Create/Update deposit through the command line.

More documentation can be found at
https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html.

    """
    url = _url(url)
    config = {}

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            logger.debug("Parsing cli options")
            config = client_command_parse_input(
                username,
                password,
                archive,
                metadata,
                archive_deposit,
                metadata_deposit,
                collection,
                slug,
                partial,
                deposit_id,
                replace,
                url,
                name,
                author,
                temp_dir,
            )
        except InputError as e:
            logger.error("Problem during parsing options: %s", e)
            sys.exit(1)
        except MaintenanceError as e:
            logger.error(e)
            sys.exit(1)

        if verbose:
            logger.info("Parsed configuration: %s" % (config,))

        deposit_id = config["deposit_id"]

        if deposit_id:
            r = deposit_update(config, logger)
        else:
            r = deposit_create(config, logger)
        print_result(r, output_format)


@deposit.command()
@click.option(
    "--url",
    default="https://deposit.softwareheritage.org",
    help="(Optional) Deposit server api endpoint. By default, "
    "https://deposit.softwareheritage.org/1",
)
@click.option("--username", required=True, help="(Mandatory) User's name")
@click.option(
    "--password", required=True, help="(Mandatory) User's associated password"
)
@click.option("--deposit-id", default=None, required=True, help="Deposit identifier.")
@click.option(
    "-f",
    "--format",
    "output_format",
    default="logging",
    type=click.Choice(["logging", "yaml", "json"]),
    help="Output format results.",
)
@click.pass_context
def status(ctx, url, username, password, deposit_id, output_format):
    """Deposit's status

    """
    url = _url(url)
    logger.debug("Status deposit")
    try:
        client = _client(url, username, password)
        collection = _collection(client)
    except InputError as e:
        logger.error("Problem during parsing options: %s", e)
        sys.exit(1)
    except MaintenanceError as e:
        logger.error(e)
        sys.exit(1)

    print_result(
        client.deposit_status(collection=collection, deposit_id=deposit_id),
        output_format,
    )


def print_result(data, output_format):
    if output_format == "json":
        click.echo(json.dumps(data))
    elif output_format == "yaml":
        click.echo(yaml.dump(data))
    else:
        logger.info(data)
