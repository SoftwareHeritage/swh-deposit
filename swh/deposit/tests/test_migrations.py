# Copyright (C) 2021-2024 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# Quick note: Django migrations already depend on one another. So to migrate a schema up
# to a point, it's enough to migrate the model to the last but one migration. Then
# assert something is not there, trigger the next migration and check the last state is
# as expected. That's what's the following scenarios do.

from datetime import datetime, timezone

from swh.deposit.config import DEPOSIT_STATUS_LOAD_SUCCESS, DEPOSIT_STATUS_PARTIAL
from swh.deposit.models import DEPOSIT_CODE, DEPOSIT_METADATA_ONLY
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
    new_state = migrator.apply_tested_migration(
        ("deposit", "0024_deposit_software_version_and_release_notes")
    )
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


def test_migration_24_adds_release_data_fields(migrator):
    fields = ["software_version", "release_notes"]

    old_state = migrator.apply_initial_migration(
        ("deposit", "0023_alter_deposit_status_detail_alter_deposit_type_and_more")
    )
    old_deposit = old_state.apps.get_model("deposit", "Deposit")
    for field in fields:
        assert not hasattr(old_deposit, field)

    new_state = migrator.apply_tested_migration(
        ("deposit", "0024_deposit_software_version_and_release_notes")
    )
    new_deposit = new_state.apps.get_model("deposit", "Deposit")
    for field in fields:
        assert hasattr(new_deposit, field)


def test_migration_25_populates_release_data_fields(migrator):
    metadata = """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom"
                xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
            <codemeta:softwareVersion>v0.1.1</codemeta:softwareVersion>
            <codemeta:releaseNotes>CHANGELOG</codemeta:releaseNotes>
        </entry>"""

    # Before the data migration
    old_state = migrator.apply_initial_migration(
        ("deposit", "0024_deposit_software_version_and_release_notes")
    )
    Deposit = old_state.apps.get_model("deposit", "Deposit")
    DepositRequest = old_state.apps.get_model("deposit", "DepositRequest")
    DepositCollection = old_state.apps.get_model("deposit", "DepositCollection")
    DepositClient = old_state.apps.get_model("deposit", "DepositClient")

    collection = DepositCollection.objects.create(name="hello")
    client = DepositClient.objects.create(username="name", collections=[collection.id])

    # this deposit will be updated by the migration (done + code, with metadata)
    deposit_done = Deposit.objects.create(
        client=client,
        collection=collection,
        origin_url="http://test.localhost",
        status=DEPOSIT_STATUS_LOAD_SUCCESS,
        type=DEPOSIT_CODE,
    )

    DepositRequest.objects.create(deposit=deposit_done, raw_metadata=metadata)
    # this deposit will not be updated (not done)
    deposit_partial = Deposit.objects.create(
        client=client,
        collection=collection,
        origin_url="http://test.localhost",
        status=DEPOSIT_STATUS_PARTIAL,
        type=DEPOSIT_CODE,
    )
    DepositRequest.objects.create(deposit=deposit_partial, raw_metadata=metadata)
    # this deposit will not be updated by the migration (no metadata)
    deposit_no_meta = Deposit.objects.create(
        client=client,
        collection=collection,
        origin_url="http://test.localhost",
        status=DEPOSIT_STATUS_LOAD_SUCCESS,
        type=DEPOSIT_CODE,
    )
    DepositRequest.objects.create(deposit=deposit_no_meta)
    # this deposit will not be updated (not code)
    deposit_not_code = Deposit.objects.create(
        client=client,
        collection=collection,
        origin_url="http://test.localhost",
        status=DEPOSIT_STATUS_LOAD_SUCCESS,
        type=DEPOSIT_METADATA_ONLY,
    )
    DepositRequest.objects.create(deposit=deposit_not_code, raw_metadata=metadata)

    # Default release data values
    for deposit in [deposit_done, deposit_partial, deposit_no_meta, deposit_not_code]:
        assert deposit_done.software_version == ""
        assert deposit_done.release_notes == ""

    # After the data migration
    new_state = migrator.apply_tested_migration(("deposit", "0025_set_release_data"))
    Deposit = new_state.apps.get_model("deposit", "Deposit")

    new_deposit_done = Deposit.objects.get(pk=deposit_done.id)
    assert new_deposit_done.software_version == "v0.1.1"
    assert new_deposit_done.release_notes == "CHANGELOG"

    new_deposit_partial = Deposit.objects.get(pk=deposit_partial.id)
    assert new_deposit_partial.software_version == ""
    assert new_deposit_partial.release_notes == ""

    new_deposit_no_meta = Deposit.objects.get(pk=deposit_no_meta.id)
    assert new_deposit_no_meta.software_version == ""
    assert new_deposit_no_meta.release_notes == ""

    new_deposit_not_code = Deposit.objects.get(pk=deposit_not_code.id)
    assert new_deposit_not_code.software_version == ""
    assert new_deposit_not_code.release_notes == ""
