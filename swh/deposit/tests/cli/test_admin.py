# Copyright (C) 2019-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.deposit.cli.admin import admin as cli
from swh.deposit.models import DepositClient, DepositCollection


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
    assert second_password != first_password, "Password should have changed"
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
