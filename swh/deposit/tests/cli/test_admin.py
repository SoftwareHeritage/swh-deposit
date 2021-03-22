# Copyright (C) 2019-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.deposit.cli.admin import admin as cli
from swh.deposit.config import (
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_PARTIAL,
    DEPOSIT_STATUS_VERIFIED,
)
from swh.deposit.models import DepositClient, DepositCollection
from swh.scheduler.utils import create_oneshot_task_dict


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass


def test_cli_admin_user_list_nothing(cli_runner):
    result = cli_runner.invoke(cli, ["user", "list",])

    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    assert result.output == "Empty user list\n"


def test_cli_admin_user_list_with_users(cli_runner, deposit_user):
    result = cli_runner.invoke(cli, ["user", "list",])

    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    assert result.output == f"{deposit_user.username}\n"  # only 1 user


def test_cli_admin_collection_list_nothing(cli_runner):
    result = cli_runner.invoke(cli, ["collection", "list",])

    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    assert result.output == "Empty collection list\n"


def test_cli_admin_collection_list_with_collections(cli_runner, deposit_collection):
    from swh.deposit.tests.conftest import create_deposit_collection

    new_collection = create_deposit_collection("something")

    result = cli_runner.invoke(cli, ["collection", "list",])

    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    collections = "\n".join([deposit_collection.name, new_collection.name])
    assert result.output == f"{collections}\n"


def test_cli_admin_user_exists_unknown(cli_runner):
    result = cli_runner.invoke(cli, ["user", "exists", "unknown"])

    assert result.exit_code == 1, f"Unexpected output: {result.output}"
    assert result.output == "User unknown does not exist.\n"


def test_cli_admin_user_exists(cli_runner, deposit_user):
    result = cli_runner.invoke(cli, ["user", "exists", deposit_user.username])

    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    assert result.output == f"User {deposit_user.username} exists.\n"


def test_cli_admin_create_collection(cli_runner):
    collection_name = "something"

    try:
        DepositCollection.objects.get(name=collection_name)
    except DepositCollection.DoesNotExist:
        pass

    result = cli_runner.invoke(
        cli, ["collection", "create", "--name", collection_name,]
    )
    assert result.exit_code == 0, f"Unexpected output: {result.output}"

    collection = DepositCollection.objects.get(name=collection_name)
    assert collection is not None

    assert (
        result.output
        == f"""Create collection '{collection_name}'.
Collection '{collection_name}' created.
"""
    )

    result2 = cli_runner.invoke(
        cli, ["collection", "create", "--name", collection_name,]
    )
    assert result2.exit_code == 0, f"Unexpected output: {result.output}"
    assert (
        result2.output
        == f"""Collection '{collection_name}' exists, skipping.
"""
    )


def test_cli_admin_user_create(cli_runner):
    user_name = "user"
    collection_name = user_name

    try:
        DepositClient.objects.get(username=user_name)
    except DepositClient.DoesNotExist:
        pass

    try:
        DepositCollection.objects.get(name=collection_name)
    except DepositCollection.DoesNotExist:
        pass

    result = cli_runner.invoke(
        cli, ["user", "create", "--username", user_name, "--password", "password",]
    )
    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    user = DepositClient.objects.get(username=user_name)
    assert user is not None
    collection = DepositCollection.objects.get(name=collection_name)
    assert collection is not None

    assert (
        result.output
        == f"""Create collection '{user_name}'.
Collection '{collection_name}' created.
Create user '{user_name}'.
User '{user_name}' created.
"""
    )

    assert collection.name == collection_name
    assert user.username == user_name
    first_password = user.password
    assert first_password is not None
    assert user.collections == [collection.id]
    assert user.is_active is True
    assert user.domain == ""
    assert user.provider_url == ""
    assert user.email == ""
    assert user.first_name == ""
    assert user.last_name == ""

    # create a user that already exists
    result2 = cli_runner.invoke(
        cli,
        [
            "user",
            "create",
            "--username",
            "user",
            "--password",
            "another-password",  # changing password
            "--collection",
            collection_name,  # specifying the collection this time
            "--firstname",
            "User",
            "--lastname",
            "no one",
            "--email",
            "user@org.org",
            "--provider-url",
            "http://some-provider.org",
            "--domain",
            "domain",
        ],
    )

    assert result2.exit_code == 0, f"Unexpected output: {result2.output}"
    user = DepositClient.objects.get(username=user_name)
    assert user is not None

    assert user.username == user_name
    assert user.collections == [collection.id]
    assert user.is_active is True
    second_password = user.password
    assert second_password is not None
    # For the transition period, we can choose either basic or keycloak so we need to be
    # able to still define a password (basic), so there it's updated.
    assert second_password != first_password, "Password changed"
    assert user.domain == "domain"
    assert user.provider_url == "http://some-provider.org"
    assert user.email == "user@org.org"
    assert user.first_name == "User"
    assert user.last_name == "no one"

    assert (
        result2.output
        == f"""Collection '{collection_name}' exists, skipping.
Update user '{user_name}'.
User '{user_name}' updated.
"""
    )


def test_cli_admin_reschedule_unknown_deposit(cli_runner):
    """Rescheduling unknown deposit should report failure

    """
    unknown_deposit_id = 666

    from swh.deposit.models import Deposit

    try:
        Deposit.objects.get(id=unknown_deposit_id)
    except Deposit.DoesNotExist:
        pass

    result = cli_runner.invoke(
        cli, ["deposit", "reschedule", "--deposit-id", unknown_deposit_id]
    )

    assert result.output == f"Deposit {unknown_deposit_id} does not exist.\n"
    assert result.exit_code == 1


def test_cli_admin_reschedule_verified_deposit(cli_runner, complete_deposit):
    """Rescheduling verified deposit should do nothing but report

    """
    deposit = complete_deposit
    deposit.status = "verified"
    deposit.save()

    result = cli_runner.invoke(
        cli, ["deposit", "reschedule", "--deposit-id", deposit.id]
    )

    assert result.output == f"Deposit {deposit.id} already set for rescheduling.\n"
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "status_to_check", [DEPOSIT_STATUS_PARTIAL, DEPOSIT_STATUS_DEPOSITED]
)
def test_cli_admin_reschedule_unaccepted_deposit_status(
    status_to_check, cli_runner, complete_deposit
):
    """Rescheduling verified deposit should do nothing but report

    """
    deposit = complete_deposit
    deposit.status = status_to_check  # not accepted status will fail the check
    deposit.save()

    result = cli_runner.invoke(
        cli, ["deposit", "reschedule", "--deposit-id", deposit.id]
    )

    assert result.output == (
        f"Deposit {deposit.id} cannot be rescheduled (status: {deposit.status}).\n"
        "Rescheduling deposit is only accepted for deposit with status: done, failed.\n"
    )
    assert result.exit_code == 1


def test_cli_admin_reschedule_missing_task_id(cli_runner, complete_deposit):
    """Rescheduling deposit with no load_task_id cannot work.

    """
    deposit = complete_deposit
    deposit.load_task_id = ""  # drop the load-task-id so it fails the check
    deposit.save()

    result = cli_runner.invoke(
        cli, ["deposit", "reschedule", "--deposit-id", deposit.id]
    )

    assert result.output == (
        f"Deposit {deposit.id} cannot be rescheduled. It misses the "
        "associated scheduler task id (field load_task_id).\n"
    )
    assert result.exit_code == 1


def test_cli_admin_reschedule_nominal(cli_runner, complete_deposit, swh_scheduler):
    """Rescheduling deposit with no load_task_id cannot work.

    """
    deposit = complete_deposit

    from swh.deposit.models import Deposit

    # create a task to keep a reference on it
    task = create_oneshot_task_dict(
        "load-deposit", url=deposit.origin_url, deposit_id=deposit.id, retries_left=3
    )
    scheduled_task = swh_scheduler.create_tasks([task])[0]
    # disable it
    swh_scheduler.set_status_tasks([scheduled_task["id"]], status="disabled")

    # Now update the deposit state with some swhid and relevant load_task_id
    deposit = complete_deposit
    deposit.load_task_id = scheduled_task["id"]
    deposit.swhid = "swh:1:dir:02ed6084fb0e8384ac58980e07548a547431cf74"
    deposit.swhid_context = f"{deposit.swhid};origin=https://url/external-id"
    deposit.save()

    # Reschedule it
    result = cli_runner.invoke(
        cli, ["deposit", "reschedule", "--deposit-id", deposit.id]
    )
    assert result.exit_code == 0

    # Now, ensure the deposit and the associated task are in the right shape
    deposit = Deposit.objects.get(id=deposit.id)

    # got reset to a state which allows rescheduling
    assert deposit.id
    assert deposit.swhid is None
    assert deposit.swhid_context is None
    assert deposit.status == DEPOSIT_STATUS_VERIFIED

    task = swh_scheduler.search_tasks(task_id=deposit.load_task_id)[0]
    assert task["status"] == "next_run_not_scheduled"
