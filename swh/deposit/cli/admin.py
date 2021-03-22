# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# WARNING: do not import unnecessary things here to keep cli startup time under
# control
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from swh.deposit.cli import deposit

if TYPE_CHECKING:
    from swh.deposit.models import DepositCollection


@deposit.group("admin")
@click.option(
    "--config-file",
    "-C",
    default=None,
    type=click.Path(exists=True, dir_okay=False,),
    help="Optional extra configuration file.",
)
@click.option(
    "--platform",
    default="development",
    type=click.Choice(["development", "production"]),
    help="development or production platform",
)
@click.pass_context
def admin(ctx, config_file: str, platform: str):
    """Server administration tasks (manipulate user or collections)"""
    from swh.deposit.config import setup_django_for

    # configuration happens here
    setup_django_for(platform, config_file=config_file)


@admin.group("user")
@click.pass_context
def user(ctx):
    """Manipulate user."""
    # configuration happens here
    pass


def _create_collection(name: str) -> DepositCollection:
    """Create the collection with name if it does not exist.

    Args:
        name: collection name

    Returns:
        collection: the existing collection object

    """
    # to avoid loading too early django namespaces
    from swh.deposit.models import DepositCollection

    try:
        collection = DepositCollection.objects.get(name=name)
        click.echo(f"Collection '{name}' exists, skipping.")
    except DepositCollection.DoesNotExist:
        click.echo(f"Create collection '{name}'.")
        collection = DepositCollection.objects.create(name=name)
        click.echo(f"Collection '{name}' created.")
    return collection


@user.command("create")
@click.option("--username", required=True, help="User's name")
@click.option("--password", help="(Deprecated) Desired user password (plain).")
@click.option("--firstname", default="", help="User's first name")
@click.option("--lastname", default="", help="User's last name")
@click.option("--email", default="", help="User's email")
@click.option("--collection", help="User's collection")
@click.option("--provider-url", default="", help="Provider URL")
@click.option("--domain", default="", help="The domain")
@click.pass_context
def user_create(
    ctx,
    username: str,
    password: str,
    firstname: str,
    lastname: str,
    email: str,
    collection: str,
    provider_url: str,
    domain: str,
):
    """Create a user with some needed information (password, collection)

    If the collection does not exist, the collection is then created
    alongside.

    The password is stored encrypted using django's utilities.

    """
    # to avoid loading too early django namespaces
    from swh.deposit.models import DepositClient

    # If collection is not provided, fallback to username
    if not collection:
        collection = username
    # create the collection if it does not exist
    collection_ = _create_collection(collection)

    # user create/update
    try:
        user = DepositClient.objects.get(username=username)  # type: ignore
        click.echo(f"Update user '{username}'.")
        action_done = "updated"
    except DepositClient.DoesNotExist:
        click.echo(f"Create user '{username}'.")
        user = DepositClient(username=username)
        user.save()
        action_done = "created"

    if password:
        user.set_password(password)
    user.collections = [collection_.id]
    user.first_name = firstname
    user.last_name = lastname
    user.email = email
    user.is_active = True
    user.provider_url = provider_url
    user.domain = domain
    user.save()

    click.echo(f"User '{username}' {action_done}.")


@user.command("list")
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
        output = "Empty user list"
    else:
        output = "\n".join((user.username for user in users))
    click.echo(output)


@user.command("exists")
@click.argument("username", required=True)
@click.pass_context
def user_exists(ctx, username: str):
    """Check if user exists.
    """
    # to avoid loading too early django namespaces
    from swh.deposit.models import DepositClient

    try:
        DepositClient.objects.get(username=username)  # type: ignore
        click.echo(f"User {username} exists.")
        ctx.exit(0)
    except DepositClient.DoesNotExist:
        click.echo(f"User {username} does not exist.")
        ctx.exit(1)


@admin.group("collection")
@click.pass_context
def collection(ctx):
    """Manipulate collections."""
    pass


@collection.command("create")
@click.option("--name", required=True, help="Collection's name")
@click.pass_context
def collection_create(ctx, name):
    _create_collection(name)


@collection.command("list")
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
        output = "Empty collection list"
    else:
        output = "\n".join((col.name for col in collections))
    click.echo(output)


@admin.group("deposit")
@click.pass_context
def adm_deposit(ctx):
    """Manipulate deposit."""
    pass


@adm_deposit.command("reschedule")
@click.option("--deposit-id", required=True, help="Deposit identifier")
@click.pass_context
def adm_deposit_reschedule(ctx, deposit_id):
    """Reschedule the deposit loading

    This will:

    - check the deposit's status to something reasonable (failed or done). That
      means that the checks have passed alright but something went wrong during
      the loading (failed: loading failed, done: loading ok, still for some
      reasons as in bugs, we need to reschedule it)

    - reset the deposit's status to 'verified' (prior to any loading but after
      the checks which are fine) and removes the different archives'
      identifiers (swh-id, ...)

    - trigger back the loading task through the scheduler

    """
    # to avoid loading too early django namespaces
    from datetime import datetime

    from swh.deposit.config import (
        DEPOSIT_STATUS_LOAD_FAILURE,
        DEPOSIT_STATUS_LOAD_SUCCESS,
        DEPOSIT_STATUS_VERIFIED,
        APIConfig,
    )
    from swh.deposit.models import Deposit

    try:
        deposit = Deposit.objects.get(pk=deposit_id)
    except Deposit.DoesNotExist:
        click.echo(f"Deposit {deposit_id} does not exist.")
        ctx.exit(1)

    # Check the deposit is in a reasonable state
    accepted_statuses = [DEPOSIT_STATUS_LOAD_SUCCESS, DEPOSIT_STATUS_LOAD_FAILURE]
    if deposit.status == DEPOSIT_STATUS_VERIFIED:
        click.echo(f"Deposit {deposit_id} already set for rescheduling.")
        ctx.exit(0)

    if deposit.status not in accepted_statuses:
        click.echo(
            f"Deposit {deposit_id} cannot be rescheduled (status: {deposit.status}).\n"
            "Rescheduling deposit is only accepted for deposit with status: "
            f"{', '.join(accepted_statuses)}."
        )
        ctx.exit(1)

    task_id = deposit.load_task_id
    if not task_id:
        click.echo(
            f"Deposit {deposit_id} cannot be rescheduled. It misses the "
            "associated scheduler task id (field load_task_id)."
        )
        ctx.exit(1)

    # Reset the deposit's state
    deposit.swhid = None
    deposit.swhid_context = None
    deposit.status = DEPOSIT_STATUS_VERIFIED
    deposit.save()

    # Schedule back the deposit loading task
    scheduler = APIConfig().scheduler
    scheduler.set_status_tasks(
        [task_id], status="next_run_not_scheduled", next_run=datetime.now()
    )
