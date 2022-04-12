# Copyright (C) 2021-2022 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# Quick note: Django migrations already depend on one another. So to migrate a schema up
# to a point, it's enough to migrate the model to the last but one migration. Then
# assert something is not there, trigger the next migration and check the last state is
# as expected. That's what's the following scenarios do.

from datetime import datetime, timezone

from swh.deposit.config import DEPOSIT_STATUS_LOAD_SUCCESS
from swh.model.hashutil import hash_to_bytes
from swh.model.swhids import CoreSWHID, ObjectType, QualifiedSWHID


def now() -> datetime:
    return datetime.now(tz=timezone.utc)


def test_migrations_20_rename_swhid_column_in_deposit_model(migrator):
    """Ensures the 20 migration renames appropriately the swh_id* Deposit columns"""

    old_state = migrator.apply_initial_migration(("deposit", "0019_auto_20200519_1035"))
    old_deposit = old_state.apps.get_model("deposit", "Deposit")

    assert hasattr(old_deposit, "swh_id") is True
    assert hasattr(old_deposit, "swhid") is False
    assert hasattr(old_deposit, "swh_id_context") is True
    assert hasattr(old_deposit, "swhid_context") is False

    new_state = migrator.apply_tested_migration(
        ("deposit", "0021_deposit_origin_url_20201124_1438")
    )
    new_deposit = new_state.apps.get_model("deposit", "Deposit")

    assert hasattr(new_deposit, "swh_id") is False
    assert hasattr(new_deposit, "swhid") is True
    assert hasattr(new_deposit, "swh_id_context") is False
    assert hasattr(new_deposit, "swhid_context") is True


def test_migrations_21_add_origin_url_column_to_deposit_model(migrator):
    """Ensures the 21 migration adds the origin_url field to the Deposit table"""

    old_state = migrator.apply_initial_migration(("deposit", "0020_auto_20200929_0855"))
    old_deposit = old_state.apps.get_model("deposit", "Deposit")

    assert hasattr(old_deposit, "origin_url") is False

    new_state = migrator.apply_tested_migration(
        ("deposit", "0021_deposit_origin_url_20201124_1438")
    )
    new_deposit = new_state.apps.get_model("deposit", "Deposit")

    assert hasattr(new_deposit, "origin_url") is True


def test_migrations_22_add_deposit_type_column_model_and_data(migrator):
    """22 migration should add the type column and migrate old values with new type"""
    from swh.deposit.models import (
        DEPOSIT_CODE,
        DEPOSIT_METADATA_ONLY,
        Deposit,
        DepositClient,
        DepositCollection,
    )

    old_state = migrator.apply_initial_migration(
        ("deposit", "0021_deposit_origin_url_20201124_1438")
    )
    old_deposit = old_state.apps.get_model("deposit", "Deposit")

    collection = DepositCollection.objects.create(name="hello")

    client = DepositClient.objects.create(username="name", collections=[collection.id])

    # Create old deposits to make sure they are migrated properly
    deposit1 = old_deposit.objects.create(
        status="partial", client_id=client.id, collection_id=collection.id
    )
    deposit2 = old_deposit.objects.create(
        status="verified", client_id=client.id, collection_id=collection.id
    )

    origin = "https://hal.archives-ouvertes.fr/hal-01727745"
    directory_id = "42a13fc721c8716ff695d0d62fc851d641f3a12b"
    release_id = hash_to_bytes("548b3c0a2bb43e1fca191e24b5803ff6b3bc7c10")
    snapshot_id = hash_to_bytes("e5e82d064a9c3df7464223042e0c55d72ccff7f0")

    date_now = now()
    # metadata deposit
    deposit3 = old_deposit.objects.create(
        status=DEPOSIT_STATUS_LOAD_SUCCESS,
        client_id=client.id,
        collection_id=collection.id,
        swhid=CoreSWHID(
            object_type=ObjectType.DIRECTORY,
            object_id=hash_to_bytes(directory_id),
        ),
        swhid_context=QualifiedSWHID(
            object_type=ObjectType.DIRECTORY,
            object_id=hash_to_bytes(directory_id),
            origin=origin,
            visit=CoreSWHID(object_type=ObjectType.SNAPSHOT, object_id=snapshot_id),
            anchor=CoreSWHID(object_type=ObjectType.RELEASE, object_id=release_id),
            path=b"/",
        ),
    )
    # work around (complete date is installed on creation)
    deposit3.complete_date = date_now
    deposit3.reception_date = date_now
    deposit3.save()

    assert hasattr(old_deposit, "type") is False

    # Migrate to the latest schema
    new_state = migrator.apply_tested_migration(("deposit", "0022_auto_20220223_1542"))
    new_deposit = new_state.apps.get_model("deposit", "Deposit")

    assert hasattr(new_deposit, "type") is True

    assert Deposit().type == DEPOSIT_CODE

    all_deposits = Deposit.objects.all()
    assert len(all_deposits) == 3
    for deposit in all_deposits:
        if deposit.id in (deposit1.id, deposit2.id):
            assert deposit.type == DEPOSIT_CODE
        else:
            assert deposit.id == deposit3.id and deposit.type == DEPOSIT_METADATA_ONLY
