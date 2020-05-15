# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import logging

from django.db import migrations
from typing import Any, Dict, Optional, Tuple

from swh.core import config
from swh.deposit.config import DEPOSIT_STATUS_LOAD_SUCCESS
from swh.model.hashutil import hash_to_bytes, hash_to_hex
from swh.model.identifiers import (
    parse_persistent_identifier,
    persistent_identifier,
    DIRECTORY,
    REVISION,
    SNAPSHOT,
)
from swh.storage import get_storage as get_storage_client


SWH_PROVIDER_URL = "https://www.softwareheritage.org"


logger = logging.getLogger(__name__)


swh_storage = None


def get_storage() -> Optional[Any]:
    """Instantiate a storage client

    """
    settings = os.environ.get("DJANGO_SETTINGS_MODULE")
    if settings != "swh.deposit.settings.production":  # Bypass for now
        return None

    global swh_storage

    if not swh_storage:
        config_file = os.environ.get("SWH_CONFIG_FILENAME")
        if not config_file:
            raise ValueError(
                "Production: SWH_CONFIG_FILENAME must be set to the"
                " configuration file needed!"
            )

        if not os.path.exists(config_file):
            raise ValueError(
                "Production: configuration file %s does not exist!" % (config_file,)
            )

        conf = config.load_named_config(config_file)
        if not conf:
            raise ValueError(
                "Production: configuration %s does not exist." % (config_file,)
            )

        storage_config = conf.get("storage")
        if not storage_config:
            raise ValueError(
                "Production: invalid configuration; missing 'storage' config entry."
            )

        swh_storage = get_storage_client(**storage_config)

    return swh_storage


def get_snapshot(storage, origin: str, revision_id: str) -> Optional[str]:
    """Retrieve the snapshot targeting the revision_id for the given origin.

    """
    all_visits = storage.origin_visit_get(origin)
    for visit in all_visits:
        if not visit["snapshot"]:
            continue
        detail_snapshot = storage.snapshot_get(visit["snapshot"])
        if not detail_snapshot:
            continue
        for branch_name, branch in detail_snapshot["branches"].items():
            if branch["target_type"] == "revision":
                revision = branch["target"]
                if hash_to_hex(revision) == revision_id:
                    # Found the snapshot
                    return hash_to_hex(visit["snapshot"])
    return None


def migrate_deposit_swhid_context_not_null(apps, schema_editor):
    """Migrate deposit SWHIDs to the new format.

    Migrate deposit SWHIDs to the new format. Only deposit with status done and
    swh_id_context not null are concerned.

    """
    storage = get_storage()
    if not storage:
        logging.warning("Nothing to do")
        return None

    Deposit = apps.get_model("deposit", "Deposit")
    for deposit in Deposit.objects.filter(
        status=DEPOSIT_STATUS_LOAD_SUCCESS, swh_id_context__isnull=False
    ):
        obj_dir = parse_persistent_identifier(deposit.swh_id_context)
        assert obj_dir.object_type == DIRECTORY

        obj_rev = parse_persistent_identifier(deposit.swh_anchor_id)
        assert obj_rev.object_type == REVISION

        if set(obj_dir.metadata.keys()) != {"origin"}:
            # Assuming the migration is already done for that deposit
            logger.warning(
                "Deposit id %s: Migration already done, skipping", deposit.id
            )
            continue

        # Starting migration

        dir_id = obj_dir.object_id
        origin = obj_dir.metadata["origin"]

        check_origin = storage.origin_get({"url": origin})
        if not check_origin:
            logger.warning("Deposit id %s: Origin %s not found!", deposit.id, origin)
            continue

        rev_id = obj_rev.object_id
        # Find the snapshot targeting the revision
        snp_id = get_snapshot(storage, origin, rev_id)
        if not snp_id:
            logger.warning(
                "Deposit id %s: Snapshot targeting revision %s not found!",
                deposit.id,
                rev_id,
            )
            continue

        # Reference the old values to do some checks later
        old_swh_id = deposit.swh_id
        old_swh_id_context = deposit.swh_id_context
        old_swh_anchor_id = deposit.swh_anchor_id
        old_swh_anchor_id_context = deposit.swh_anchor_id_context

        # Update
        deposit.swh_id_context = persistent_identifier(
            DIRECTORY,
            dir_id,
            metadata={
                "origin": origin,
                "visit": persistent_identifier(SNAPSHOT, snp_id),
                "anchor": persistent_identifier(REVISION, rev_id),
                "path": "/",
            },
        )

        # Ensure only deposit.swh_id_context changed
        logging.debug("deposit.id: {deposit.id}")
        logging.debug("deposit.swh_id: %s -> %s", old_swh_id, deposit.swh_id)
        assert old_swh_id == deposit.swh_id
        logging.debug(
            "deposit.swh_id_context: %s -> %s",
            old_swh_id_context,
            deposit.swh_id_context,
        )
        assert old_swh_id_context != deposit.swh_id_context
        logging.debug(
            "deposit.swh_anchor_id: %s -> %s", old_swh_anchor_id, deposit.swh_anchor_id
        )
        assert old_swh_anchor_id == deposit.swh_anchor_id
        logging.debug(
            "deposit.swh_anchor_id_context: %s -> %s",
            old_swh_anchor_id_context,
            deposit.swh_anchor_id_context,
        )
        assert old_swh_anchor_id_context == deposit.swh_anchor_id_context

        # Commit
        deposit.save()


def resolve_origin(deposit_id: int, provider_url: str, external_id: str) -> str:
    """Resolve the origin from provider-url and external-id

    For some edge case, only the external_id is used as there is some old inconsistency
    from testing which exists.

    """
    map_edge_case_origin: Dict[Tuple[int, str], str] = {
        (
            76,
            "hal-01588782",
        ): "https://inria.halpreprod.archives-ouvertes.fr/hal-01588782",
        (
            87,
            "hal-01588927",
        ): "https://inria.halpreprod.archives-ouvertes.fr/hal-01588927",
        (89, "hal-01588935"): "https://hal-preprod.archives-ouvertes.fr/hal-01588935",
        (
            88,
            "hal-01588928",
        ): "https://inria.halpreprod.archives-ouvertes.fr/hal-01588928",
        (
            90,
            "hal-01588942",
        ): "https://inria.halpreprod.archives-ouvertes.fr/hal-01588942",
        (143, "hal-01592430"): "https://hal-preprod.archives-ouvertes.fr/hal-01592430",
        (
            75,
            "hal-01588781",
        ): "https://inria.halpreprod.archives-ouvertes.fr/hal-01588781",
    }
    origin = map_edge_case_origin.get((deposit_id, external_id))
    if origin:
        return origin

    # Some simpler origin edge cases (mostly around the initial deposits)
    map_origin = {
        (
            SWH_PROVIDER_URL,
            "je-suis-gpl",
        ): "https://forge.softwareheritage.org/source/jesuisgpl/",
        (
            SWH_PROVIDER_URL,
            "external-id",
        ): "https://hal.archives-ouvertes.fr/external-id",
    }
    key = (provider_url, external_id)
    return map_origin.get(key, f"{provider_url.rstrip('/')}/{external_id}")


def migrate_deposit_swhid_context_null(apps, schema_editor):
    """Migrate deposit SWHIDs to the new format.

    Migrate deposit whose swh_id_context is not set (initial deposits not migrated at
    the time). Only deposit with status done and swh_id_context null are concerned.

    Note: Those deposits have their swh_id being the SWHPIDs of the revision! So we can
    align them as well.

    """
    storage = get_storage()
    if not storage:
        logging.warning("Nothing to do")
        return None
    Deposit = apps.get_model("deposit", "Deposit")
    for deposit in Deposit.objects.filter(
        status=DEPOSIT_STATUS_LOAD_SUCCESS, swh_id_context__isnull=True
    ):
        obj_rev = parse_persistent_identifier(deposit.swh_id)
        if obj_rev.object_type == DIRECTORY:
            # Assuming the migration is already done for that deposit
            logger.warning(
                "Deposit id %s: Migration already done, skipping", deposit.id
            )
            continue

        # Ensuring Migration not done
        assert obj_rev.object_type == REVISION

        assert deposit.swh_id is not None
        assert deposit.swh_id_context is None
        assert deposit.swh_anchor_id is None
        assert deposit.swh_anchor_id_context is None

        rev_id = obj_rev.object_id
        revisions = list(storage.revision_get([hash_to_bytes(rev_id)]))
        if not revisions:
            logger.warning("Deposit id %s: Revision %s not found!", deposit.id, rev_id)
            continue
        revision = revisions[0]

        provider_url = deposit.client.provider_url
        external_id = deposit.external_id

        origin = resolve_origin(deposit.id, provider_url, external_id)
        check_origin = storage.origin_get({"url": origin})
        if not check_origin:
            logger.warning("Deposit id %s: Origin %s not found!", deposit.id, origin)
            continue

        dir_id = hash_to_hex(revision["directory"])

        # Reference the old values to do some checks later
        old_swh_id = deposit.swh_id
        old_swh_id_context = deposit.swh_id_context
        old_swh_anchor_id = deposit.swh_anchor_id
        old_swh_anchor_id_context = deposit.swh_anchor_id_context

        # retrieve the snapshot from the archive
        snp_id = get_snapshot(storage, origin, rev_id)
        if not snp_id:
            logger.warning(
                "Deposit id %s: Snapshot targeting revision %s not found!",
                deposit.id,
                rev_id,
            )
            continue

        # New SWHIDs ids
        deposit.swh_id = persistent_identifier(DIRECTORY, dir_id)
        deposit.swh_id_context = persistent_identifier(
            DIRECTORY,
            dir_id,
            metadata={
                "origin": origin,
                "visit": persistent_identifier(SNAPSHOT, snp_id),
                "anchor": persistent_identifier(REVISION, rev_id),
                "path": "/",
            },
        )
        # Realign the remaining deposit SWHIDs fields
        deposit.swh_anchor_id = persistent_identifier(REVISION, rev_id)
        deposit.swh_anchor_id_context = persistent_identifier(
            REVISION, rev_id, metadata={"origin": origin,}
        )

        # Ensure only deposit.swh_id_context changed
        logging.debug("deposit.id: {deposit.id}")
        logging.debug("deposit.swh_id: %s -> %s", old_swh_id, deposit.swh_id)

        assert old_swh_id != deposit.swh_id
        logging.debug(
            "deposit.swh_id_context: %s -> %s",
            old_swh_id_context,
            deposit.swh_id_context,
        )
        assert old_swh_id_context != deposit.swh_id_context
        assert deposit.swh_id_context is not None
        logging.debug(
            "deposit.swh_anchor_id: %s -> %s", old_swh_anchor_id, deposit.swh_anchor_id
        )
        assert deposit.swh_anchor_id == old_swh_id
        assert deposit.swh_anchor_id is not None
        logging.debug(
            "deposit.swh_anchor_id_context: %s -> %s",
            old_swh_anchor_id_context,
            deposit.swh_anchor_id_context,
        )
        assert deposit.swh_anchor_id_context is not None

        deposit.save()


class Migration(migrations.Migration):
    dependencies = [
        ("deposit", "0017_auto_20190925_0906"),
    ]

    operations = [
        # Migrate and make the operations possibly reversible
        # https://docs.djangoproject.com/en/3.0/ref/migration-operations/#django.db.migrations.operations.RunPython.noop  # noqa
        migrations.RunPython(
            migrate_deposit_swhid_context_not_null,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            migrate_deposit_swhid_context_null, reverse_code=migrations.RunPython.noop
        ),
    ]
