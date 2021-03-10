# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# Quick note: Django migrations already depend on one another. So to migrate a schema up
# to a point, it's enough to migrate the model to the last but one migration. Then
# assert something is not there, trigger the next migration and check the last state is
# as expected. That's what's the following scenarios do.


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
