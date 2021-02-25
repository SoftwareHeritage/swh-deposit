# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib
from io import BytesIO

from django.urls import reverse_lazy as reverse
from rest_framework import status

from swh.deposit.config import COL_IRI, DEPOSIT_STATUS_REJECTED
from swh.deposit.parsers import parse_xml


def test_deposit_post_will_fail_with_401(client):
    """Without authentication, endpoint refuses access with 401 response

    """
    url = reverse(COL_IRI, args=["hal"])
    response = client.post(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_access_to_another_user_collection_is_forbidden(
    authenticated_client, deposit_another_collection, deposit_user
):
    """Access to another user collection should return a 403

    """
    coll2 = deposit_another_collection
    url = reverse(COL_IRI, args=[coll2.name])
    response = authenticated_client.post(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    msg = "Client %s cannot access collection %s" % (deposit_user.username, coll2.name,)
    assert msg in response.content.decode("utf-8")


def test_delete_on_col_iri_not_supported(authenticated_client, deposit_collection):
    """Delete on col iri should return a 405 response

    """
    url = reverse(COL_IRI, args=[deposit_collection.name])
    response = authenticated_client.delete(url)
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert "DELETE method is not supported on this endpoint" in response.content.decode(
        "utf-8"
    )


def create_deposit_with_rejection_status(authenticated_client, deposit_collection):
    url = reverse(COL_IRI, args=[deposit_collection.name])

    data = b"some data which is clearly not a zip file"
    md5sum = hashlib.md5(data).hexdigest()
    external_id = "some-external-id-1"

    # when
    response = authenticated_client.post(
        url,
        content_type="application/zip",  # as zip
        data=data,
        # + headers
        CONTENT_LENGTH=len(data),
        # other headers needs HTTP_ prefix to be taken into account
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=md5sum,
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename0",
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    actual_state = response_content["deposit_status"]
    assert actual_state == DEPOSIT_STATUS_REJECTED
