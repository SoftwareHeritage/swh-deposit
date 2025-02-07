# Copyright (C) 2019-2025  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os

from django.utils import timezone
import pytest

from swh.deposit.config import DEPOSIT_STATUS_VERIFIED


@pytest.fixture
def datadir(request):
    """Override default datadir to target main test datadir"""
    return os.path.join(os.path.dirname(str(request.fspath)), "../data")


@pytest.fixture
def ready_deposit_verified(partial_deposit_with_metadata):
    """Returns a verified deposit."""
    deposit = partial_deposit_with_metadata
    deposit.status = DEPOSIT_STATUS_VERIFIED
    deposit.complete_date = timezone.now()
    deposit.save()
    return deposit
