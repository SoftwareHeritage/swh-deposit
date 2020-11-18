# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from __future__ import annotations

from datetime import datetime, timezone
import logging

# WARNING: do not import unnecessary things here to keep cli startup time under
# control
import os
import sys
from typing import TYPE_CHECKING, Any, Collection, Dict, List, Optional
import warnings

import click

from swh.deposit.cli import deposit

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from swh.deposit.client import PublicApiDepositClient


class InputError(ValueError):
    """Input script error

    """

    pass


def generate_slug() -> str:
    """Generate a slug (sample purposes).

    """
    import uuid

    return str(uuid.uuid4())


def _url(url: str) -> str:
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


def generate_metadata(
    deposit_client: str, name: str, external_id: str, authors: List[str]
) -> str:
    """Generate sword compliant xml metadata with the minimum required metadata.

    The Atom spec, https://tools.ietf.org/html/rfc4287, says that:

    - atom:entry elements MUST contain one or more atom:author elements
    - atom:entry elements MUST contain exactly one atom:title element.
    - atom:entry elements MUST contain exactly one atom:updated element.

    However, we are also using CodeMeta, so we want some basic information to be
    mandatory.

    Therefore, we generate the following mandatory fields:
    - http://www.w3.org/2005/Atom#updated
    - http://www.w3.org/2005/Atom#author
    - http://www.w3.org/2005/Atom#title
    - https://doi.org/10.5063/SCHEMA/CODEMETA-2.0#name (yes, in addition to
      http://www.w3.org/2005/Atom#title, even if they have somewhat the same meaning)
    - https://doi.org/10.5063/SCHEMA/CODEMETA-2.0#author

    Args:
        deposit_client: Deposit client username,
        name: Software name
        external_id: External identifier (slug) or generated one
        authors: List of author names

    Returns:
        metadata xml string

    """
    import xmltodict

    # generate a metadata file with the minimum required metadata
    codemetadata = {
        "entry": {
            "@xmlns:atom": "http://www.w3.org/2005/Atom",
            "@xmlns:codemeta": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0",
            "codemeta:identifier": external_id,
            "atom:updated": datetime.now(tz=timezone.utc),  # mandatory, cf. docstring
            "atom:author": deposit_client,  # mandatory, cf. docstring
            "atom:title": name,  # mandatory, cf. docstring
            "codemeta:name": name,  # mandatory, cf. docstring
            "codemeta:author": [  # mandatory, cf. docstring
                {"codemeta:name": author_name} for author_name in authors
            ],
        },
    }
    logging.debug("Metadata dict to generate as xml: %s", codemetadata)
    return xmltodict.unparse(codemetadata, pretty=True)


def _collection(client: PublicApiDepositClient) -> str:
    """Retrieve the client's collection

    """
    # retrieve user's collection
    sd_content = client.service_document()
    if "error" in sd_content:
        raise InputError("Service document retrieval: %s" % (sd_content["error"],))
    collection = sd_content["service"]["workspace"]["collection"]["sword:name"]
    return collection


def client_command_parse_input(
    client,
    username: str,
    archive: Optional[str],
    metadata: Optional[str],
    collection: Optional[str],
    slug: Optional[str],
    partial: bool,
    deposit_id: Optional[int],
    swhid: Optional[str],
    replace: bool,
    url: str,
    name: Optional[str],
    authors: List[str],
    temp_dir: str,
) -> Dict[str, Any]:
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

            "archive": the software archive to deposit
            "username": username
            "metadata": the metadata file to deposit
            "collection": the user's collection under which to put the deposit
            "slug": the slug or external id identifying the deposit to make
            "in_progress": if the deposit is partial or not
            "url": deposit's server main entry point
            "deposit_id": optional deposit identifier
            "swhid": optional deposit swhid
            "replace": whether the given deposit is to be replaced or not
    """

    if not slug:  # generate one as this is mandatory
        slug = generate_slug()

    if not metadata:
        if name and authors:
            metadata_path = os.path.join(temp_dir, "metadata.xml")
            logging.debug("Temporary file: %s", metadata_path)
            metadata_xml = generate_metadata(username, name, slug, authors)
            logging.debug("Metadata xml generated: %s", metadata_xml)
            with open(metadata_path, "w") as f:
                f.write(metadata_xml)
            metadata = metadata_path
        elif archive is not None and not partial and not deposit_id:
            # If we meet all the following conditions:
            # * this is not an archive-only deposit request
            # * it is not part of a multipart deposit (either create/update
            #   or finish)
            # * it misses either name or authors
            raise InputError(
                "For metadata deposit request, either a metadata file with "
                "--metadata or both --author and --name must be provided. "
            )
        elif name or authors:
            # If we are generating metadata, then all mandatory metadata
            # must be present
            raise InputError(
                "For metadata deposit request, either a metadata file with "
                "--metadata or both --author and --name must be provided."
            )
        else:
            # TODO: this is a multipart deposit, we might want to check that
            # metadata are deposited at some point
            pass
    elif name or authors:
        raise InputError(
            "Using --metadata flag is incompatible with both "
            "--author and --name (Those are used to generate one metadata file)."
        )

    if not archive and not metadata:
        raise InputError(
            "Please provide an actionable command. See --help for more information"
        )

    if replace and not deposit_id:
        raise InputError("To update an existing deposit, you must provide its id")

    if not collection:
        collection = _collection(client)

    return {
        "archive": archive,
        "username": username,
        "metadata": metadata,
        "collection": collection,
        "slug": slug,
        "in_progress": partial,
        "url": url,
        "deposit_id": deposit_id,
        "swhid": swhid,
        "replace": replace,
    }


def _subdict(d: Dict[str, Any], keys: Collection[str]) -> Dict[str, Any]:
    "return a dict from d with only given keys"
    return {k: v for k, v in d.items() if k in keys}


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
    help="Deprecated (ignored)",
)
@click.option(
    "--metadata-deposit/--no-metadata-deposit",
    default=False,
    help="Deprecated (ignored)",
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
    "--swhid",
    default=None,
    help="(Optional) Update existing completed deposit (status done) with new metadata",
)
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
    username: str,
    password: str,
    archive: Optional[str],
    metadata: Optional[str],
    archive_deposit: bool,
    metadata_deposit: bool,
    collection: Optional[str],
    slug: Optional[str],
    partial: bool,
    deposit_id: Optional[int],
    swhid: Optional[str],
    replace: bool,
    url: str,
    verbose: bool,
    name: Optional[str],
    author: List[str],
    output_format: Optional[str],
):
    """Software Heritage Public Deposit Client

    Create/Update deposit through the command line.

More documentation can be found at
https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html.

    """
    import tempfile

    from swh.deposit.client import MaintenanceError, PublicApiDepositClient

    if archive_deposit or metadata_deposit:
        warnings.warn(
            '"archive_deposit" and "metadata_deposit" option arguments are '
            "deprecated and have no effect; simply do not provide the archive "
            "for a metadata-only deposit, and do not provide a metadata for a"
            "archive-only deposit.",
            DeprecationWarning,
        )

    url = _url(url)

    client = PublicApiDepositClient(url=url, auth=(username, password))
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            logger.debug("Parsing cli options")
            config = client_command_parse_input(
                client,
                username,
                archive,
                metadata,
                collection,
                slug,
                partial,
                deposit_id,
                swhid,
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
            logger.info("Parsed configuration: %s", config)

        keys = ["archive", "collection", "in_progress", "metadata", "slug"]
        if config["deposit_id"]:
            keys += ["deposit_id", "replace", "swhid"]
            data = client.deposit_update(**_subdict(config, keys))
        else:
            data = client.deposit_create(**_subdict(config, keys))

        print_result(data, output_format)


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
    from swh.deposit.client import MaintenanceError, PublicApiDepositClient

    url = _url(url)
    logger.debug("Status deposit")
    try:
        client = PublicApiDepositClient(url=url, auth=(username, password))
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


def print_result(data: Dict[str, Any], output_format: Optional[str]) -> None:
    """Display the result data into a dedicated output format.

    """
    import json

    import yaml

    if output_format == "json":
        click.echo(json.dumps(data))
    elif output_format == "yaml":
        click.echo(yaml.dump(data))
    else:
        logger.info(data)
