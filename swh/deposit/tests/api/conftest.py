# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib
import pytest

from django.urls import reverse

from swh.deposit.config import (
    DEPOSIT_STATUS_DEPOSITED,
    COL_IRI,
    DEPOSIT_STATUS_VERIFIED,
)
from swh.deposit.models import Deposit
from swh.deposit.parsers import parse_xml

from swh.deposit.api.private.deposit_check import SWHChecksDeposit


@pytest.fixture
def ready_deposit_ok(partial_deposit_with_metadata):
    """Returns a deposit ready for checks (it will pass the checks).

    """
    deposit = partial_deposit_with_metadata
    deposit.status = DEPOSIT_STATUS_DEPOSITED
    deposit.save()
    return deposit


@pytest.fixture
def ready_deposit_verified(partial_deposit_with_metadata):
    """Returns a deposit ready for checks (it will pass the checks).

    """
    deposit = partial_deposit_with_metadata
    deposit.status = DEPOSIT_STATUS_VERIFIED
    deposit.save()
    return deposit


@pytest.fixture
def ready_deposit_only_metadata(partial_deposit_only_metadata):
    """Deposit in status ready that will fail the checks (because missing
       archive).

    """
    deposit = partial_deposit_only_metadata
    deposit.status = DEPOSIT_STATUS_DEPOSITED
    deposit.save()
    return deposit


@pytest.fixture
def ready_deposit_invalid_archive(authenticated_client, deposit_collection):
    url = reverse(COL_IRI, args=[deposit_collection.name])

    data = b"some data which is clearly not a zip file"
    md5sum = hashlib.md5(data).hexdigest()

    # when
    response = authenticated_client.post(
        url,
        content_type="application/zip",  # as zip
        data=data,
        # + headers
        CONTENT_LENGTH=len(data),
        # other headers needs HTTP_ prefix to be taken into account
        HTTP_SLUG="external-id-invalid",
        HTTP_CONTENT_MD5=md5sum,
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename0",
    )

    response_content = parse_xml(response.content)
    deposit_id = int(response_content["deposit_id"])
    deposit = Deposit.objects.get(pk=deposit_id)
    deposit.status = DEPOSIT_STATUS_DEPOSITED
    deposit.save()
    return deposit


@pytest.fixture
def swh_checks_deposit():
    return SWHChecksDeposit()
