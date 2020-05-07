# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch


def test_check_deposit_ready(swh_config, requests_mock_datadir, deposit_checker):
    """Check on a valid 'deposited' deposit should result in 'verified'

    """
    actual_result = deposit_checker.check(collection="test", deposit_id=1)
    assert actual_result == {"status": "eventful"}


def test_check_deposit_rejected(swh_config, requests_mock_datadir, deposit_checker):
    """Check on invalid 'deposited' deposit should result in 'rejected'

    """
    actual_result = deposit_checker.check(collection="test", deposit_id=2)
    assert actual_result == {"status": "failed"}


@patch("swh.deposit.client.requests.get")
def test_check_deposit_rejected_exception(mock_requests, swh_config, deposit_checker):
    """Check on invalid 'deposited' deposit should result in 'rejected'

    """
    mock_requests.side_effect = ValueError("simulated problem when checking")
    actual_result = deposit_checker.check(collection="test", deposit_id=3)
    assert actual_result == {"status": "failed"}
