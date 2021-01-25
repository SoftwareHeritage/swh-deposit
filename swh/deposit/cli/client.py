# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from __future__ import annotations

from contextlib import contextmanager
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


@contextmanager
def trap_and_report_exceptions():
    """Trap and report exceptions (InputError, MaintenanceError) in a unified way.

    """
    from swh.deposit.client import MaintenanceError

    try:
        yield
    except InputError as e:
        logger.error("Problem during parsing options: %s", e)
        sys.exit(1)
    except MaintenanceError as e:
        logger.error(e)
        sys.exit(1)


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
    deposit_client: str,
    name: str,
    authors: List[str],
    external_id: Optional[str] = None,
    create_origin: Optional[str] = None,
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
        authors: List of author names
        create_origin: Origin concerned by the deposit

    Returns:
        metadata xml string

    """
    import xmltodict

    # generate a metadata file with the minimum required metadata
    document = {
        "atom:entry": {
            "@xmlns:atom": "http://www.w3.org/2005/Atom",
            "@xmlns:codemeta": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0",
            "atom:updated": datetime.now(tz=timezone.utc),  # mandatory, cf. docstring
            "atom:author": deposit_client,  # mandatory, cf. docstring
            "atom:title": name,  # mandatory, cf. docstring
            "codemeta:name": name,  # mandatory, cf. docstring
            "codemeta:author": [  # mandatory, cf. docstring
                {"codemeta:name": author_name} for author_name in authors
            ],
        },
    }
    if external_id:
        document["atom:entry"]["codemeta:identifier"] = external_id

    if create_origin:
        document["atom:entry"][
            "@xmlns:swh"
        ] = "https://www.softwareheritage.org/schema/2018/deposit"
        document["atom:entry"]["swh:deposit"] = {
            "swh:create_origin": {"swh:origin": {"@url": create_origin}}
        }

    logging.debug("Atom entry dict to generate as xml: %s", document)
    return xmltodict.unparse(document, pretty=True)


def _collection(client: PublicApiDepositClient) -> str:
    """Retrieve the client's collection

    """
    # retrieve user's collection
    sd_content = client.service_document()
    if "error" in sd_content:
        raise InputError("Service document retrieval: %s" % (sd_content["error"],))
    collection = sd_content["app:service"]["app:workspace"]["app:collection"][
        "sword:name"
    ]
    return collection


def client_command_parse_input(
    client,
    username: str,
    archive: Optional[str],
    metadata: Optional[str],
    collection: Optional[str],
    slug: Optional[str],
    create_origin: Optional[str],
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
            "create_origin": the origin concerned by the deposit
            "in_progress": if the deposit is partial or not
            "url": deposit's server main entry point
            "deposit_id": optional deposit identifier
            "swhid": optional deposit swhid
            "replace": whether the given deposit is to be replaced or not
    """
    if not metadata:
        if name and authors:
            metadata_path = os.path.join(temp_dir, "metadata.xml")
            logging.debug("Temporary file: %s", metadata_path)
            metadata_xml = generate_metadata(
                username, name, authors, external_id=slug, create_origin=create_origin
            )
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
    elif name or authors or create_origin:
        raise InputError(
            "Using --metadata flag is incompatible with "
            "--author and --name and --create-origin (those are used to generate one "
            "metadata file)."
        )

    if not archive and not metadata:
        raise InputError(
            "Please provide an actionable command. See --help for more information"
        )

    if metadata:
        from swh.deposit.utils import parse_xml

        metadata_raw = open(metadata, "r").read()
        metadata_dict = parse_xml(metadata_raw).get("swh:deposit", {})
        if (
            "swh:create_origin" not in metadata_dict
            and "swh:add_to_origin" not in metadata_dict
        ):
            logger.warning(
                "The metadata file provided should contain "
                '"<swh:create_origin>" or "<swh:add_to_origin>" tag',
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


def credentials_decorator(f):
    """Add default --url, --username and --password flag to cli.

    """
    f = click.option(
        "--password", required=True, help="(Mandatory) User's associated password"
    )(f)
    f = click.option("--username", required=True, help="(Mandatory) User's name")(f)
    f = click.option(
        "--url",
        default="https://deposit.softwareheritage.org",
        help=(
            "(Optional) Deposit server api endpoint. By default, "
            "https://deposit.softwareheritage.org/1"
        ),
    )(f)
    return f


def output_format_decorator(f):
    """Add --format output flag decorator to cli.

    """
    return click.option(
        "-f",
        "--format",
        "output_format",
        default="logging",
        type=click.Choice(["logging", "yaml", "json"]),
        help="Output format results.",
    )(f)


@deposit.command()
@credentials_decorator
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
)
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
)
@click.option(
    "--slug",
    help=(
        "(Deprecated) (Optional) External system information identifier. "
        "If not provided, it will be generated"
    ),
)
@click.option(
    "--create-origin",
    help=(
        "(Optional) Origin url to attach information to. To be used alongside "
        "--name and --author. This will be generated alongside the metadata to "
        "provide to the deposit server."
    ),
)
@click.option(
    "--partial/--no-partial",
    default=False,
    help=(
        "(Optional) The deposit will be partial, other deposits "
        "will have to take place to finalize it."
    ),
)
@click.option(
    "--deposit-id",
    default=None,
    help="(Optional) Update an existing partial deposit with its identifier",
)
@click.option(
    "--swhid",
    default=None,
    help="(Optional) Update existing completed deposit (status done) with new metadata",
)
@click.option(
    "--replace/--no-replace",
    default=False,
    help="(Optional) Update by replacing existing metadata to a deposit",
)
@click.option("--verbose/--no-verbose", default=False, help="Verbose mode")
@click.option("--name", help="Software name")
@click.option(
    "--author",
    multiple=True,
    help="Software author(s), this can be repeated as many times"
    " as there are authors",
)
@output_format_decorator
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
    create_origin: Optional[str],
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

    from swh.deposit.client import PublicApiDepositClient

    if archive_deposit or metadata_deposit:
        warnings.warn(
            '"archive_deposit" and "metadata_deposit" option arguments are '
            "deprecated and have no effect; simply do not provide the archive "
            "for a metadata-only deposit, and do not provide a metadata for a"
            "archive-only deposit.",
            DeprecationWarning,
        )

    if slug:
        if create_origin and slug != create_origin:
            raise InputError(
                '"--slug" flag has been deprecated in favor of "--create-origin" flag. '
                "You mentioned both with different values, please only "
                'use "--create-origin".'
            )

        warnings.warn(
            '"--slug" flag has been deprecated in favor of "--create-origin" flag. '
            'Please, start using "--create-origin" instead of "--slug"',
            DeprecationWarning,
        )

    url = _url(url)

    client = PublicApiDepositClient(url=url, auth=(username, password))
    with tempfile.TemporaryDirectory() as temp_dir:
        with trap_and_report_exceptions():
            logger.debug("Parsing cli options")
            config = client_command_parse_input(
                client,
                username,
                archive,
                metadata,
                collection,
                slug,
                create_origin,
                partial,
                deposit_id,
                swhid,
                replace,
                url,
                name,
                author,
                temp_dir,
            )

        if verbose:
            logger.info("Parsed configuration: %s", config)

        keys = [
            "archive",
            "collection",
            "in_progress",
            "metadata",
            "slug",
        ]
        if config["deposit_id"]:
            keys += ["deposit_id", "replace", "swhid"]
            data = client.deposit_update(**_subdict(config, keys))
        else:
            data = client.deposit_create(**_subdict(config, keys))

        print_result(data, output_format)


@deposit.command()
@credentials_decorator
@click.option("--deposit-id", default=None, required=True, help="Deposit identifier.")
@output_format_decorator
@click.pass_context
def status(ctx, url, username, password, deposit_id, output_format):
    """Deposit's status

    """
    from swh.deposit.client import PublicApiDepositClient

    url = _url(url)
    logger.debug("Status deposit")
    with trap_and_report_exceptions():
        client = PublicApiDepositClient(url=url, auth=(username, password))
        collection = _collection(client)

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


@deposit.command("metadata-only")
@credentials_decorator
@click.option(
    "--metadata",
    "metadata_path",
    type=click.Path(exists=True),
    required=True,
    help="Path to xml metadata file",
)
@output_format_decorator
@click.pass_context
def metadata_only(ctx, url, username, password, metadata_path, output_format):
    """Deposit metadata only upload

    """
    from swh.deposit.client import PublicApiDepositClient
    from swh.deposit.utils import parse_swh_reference, parse_xml

    # Parse to check for a swhid presence within the metadata file
    with open(metadata_path, "r") as f:
        metadata_raw = f.read()
    actual_swhid = parse_swh_reference(parse_xml(metadata_raw))

    if not actual_swhid:
        raise InputError("A SWHID must be provided for a metadata-only deposit")

    with trap_and_report_exceptions():
        client = PublicApiDepositClient(url=_url(url), auth=(username, password))
        collection = _collection(client)
        result = client.deposit_metadata_only(collection, metadata_path)

    print_result(result, output_format)
