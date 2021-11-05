# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
from typing import Dict, Optional

from swh.deposit.client import PrivateApiDepositClient
from swh.model.hashutil import hash_to_bytes, hash_to_hex
from swh.model.model import SnapshotBranch, TargetType
from swh.storage.algos.snapshot import snapshot_get_all_branches

CLIENT_TEST_CONFIG = {
    "url": "http://nowhere:9000/",
    "auth": {},  # no authentication in test scenario
}


class SWHDepositTestClient(PrivateApiDepositClient):
    """Deposit test client to permit overriding the default request
       client.

    """

    def __init__(self, client, config):
        super().__init__(config=config)
        self.client = client

    def archive_get(self, archive_update_url, archive_path, log=None):
        r = self.client.get(archive_update_url)
        with open(archive_path, "wb") as f:
            for chunk in r.streaming_content:
                f.write(chunk)

        return archive_path

    def metadata_get(self, metadata_url, log=None):
        r = self.client.get(metadata_url)
        return json.loads(r.content.decode("utf-8"))

    def status_update(
        self,
        update_status_url,
        status,
        release_id=None,
        directory_id=None,
        origin_url=None,
    ):
        payload = {"status": status}
        if release_id:
            payload["release_id"] = release_id
        if directory_id:
            payload["directory_id"] = directory_id
        if origin_url:
            payload["origin_url"] = origin_url
        self.client.put(
            update_status_url, content_type="application/json", data=json.dumps(payload)
        )

    def check(self, check_url):
        r = self.client.get(check_url)
        data = json.loads(r.content.decode("utf-8"))
        return data["status"]


def get_stats(storage) -> Dict:
    """Adaptation utils to unify the stats counters across storage
       implementation.

    """
    storage.refresh_stat_counters()
    stats = storage.stat_counters()

    keys = [
        "content",
        "directory",
        "origin",
        "origin_visit",
        "person",
        "release",
        "revision",
        "skipped_content",
        "snapshot",
    ]
    return {k: stats.get(k) for k in keys}


def decode_target(branch: Optional[SnapshotBranch]) -> Optional[Dict]:
    """Test helper to ease readability in test

    """
    if not branch:
        return None
    target_type = branch.target_type

    if target_type == TargetType.ALIAS:
        decoded_target = branch.target.decode("utf-8")
    else:
        decoded_target = hash_to_hex(branch.target)

    return {"target": decoded_target, "target_type": target_type}


def check_snapshot(expected_snapshot, storage):
    """Check for snapshot match.

    Provide the hashes as hexadecimal, the conversion is done
    within the method.

    Args:
        expected_snapshot (dict): full snapshot with hex ids
        storage (Storage): expected storage

    """
    expected_snapshot_id = expected_snapshot["id"]
    expected_branches = expected_snapshot["branches"]
    snap = snapshot_get_all_branches(hash_to_bytes(expected_snapshot_id))
    if snap is None:
        # display known snapshots instead if possible
        if hasattr(storage, "_snapshots"):  # in-mem storage
            from pprint import pprint

            for snap_id, (_snap, _) in storage._snapshots.items():
                snapd = _snap.to_dict()
                snapd["id"] = hash_to_hex(snapd["id"])
                branches = {
                    branch.decode("utf-8"): decode_target(target)
                    for branch, target in snapd["branches"].items()
                }
                snapd["branches"] = branches
                pprint(snapd)
        raise AssertionError("Snapshot is not found")

    branches = {
        branch.decode("utf-8"): decode_target(branch)
        for branch_name, branch in snap["branches"].items()
    }
    assert expected_branches == branches
