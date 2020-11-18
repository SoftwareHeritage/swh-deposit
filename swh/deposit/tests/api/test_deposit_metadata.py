# Copyright (C) 2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from io import BytesIO

import attr
from django.urls import reverse
import pytest
from rest_framework import status

from swh.deposit.config import COL_IRI, DEPOSIT_STATUS_LOAD_SUCCESS, APIConfig
from swh.deposit.models import Deposit
from swh.deposit.parsers import parse_xml
from swh.deposit.utils import compute_metadata_context
from swh.model.identifiers import SWHID, parse_swhid
from swh.model.model import (
    MetadataAuthority,
    MetadataAuthorityType,
    MetadataFetcher,
    MetadataTargetType,
    RawExtrinsicMetadata,
)
from swh.storage.interface import PagedResult


def test_deposit_metadata_invalid(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting invalid swhid reference is bad request returned to client

    """
    invalid_swhid = "swh:1:dir :31b5c8cc985d190b5a7ef4878128ebfdc2358f49"
    xml_data = atom_dataset["entry-data-with-swhid"].format(swhid=invalid_swhid)

    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=xml_data,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"Invalid SWHID reference" in response.content


def test_deposit_metadata_fails_functional_checks(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting functionally invalid metadata swhid is bad request returned to client

    """
    swhid = "swh:1:dir:31b5c8cc985d190b5a7ef4878128ebfdc2358f49"
    invalid_xml_data = atom_dataset[
        "entry-data-with-swhid-fail-metadata-functional-checks"
    ].format(swhid=swhid)

    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=invalid_xml_data,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"Functional metadata checks failure" in response.content


@pytest.mark.parametrize(
    "swhid,target_type",
    [
        (
            "swh:1:cnt:01b5c8cc985d190b5a7ef4878128ebfdc2358f49",
            MetadataTargetType.CONTENT,
        ),
        (
            "swh:1:dir:11b5c8cc985d190b5a7ef4878128ebfdc2358f49",
            MetadataTargetType.DIRECTORY,
        ),
        (
            "swh:1:rev:21b5c8cc985d190b5a7ef4878128ebfdc2358f49",
            MetadataTargetType.REVISION,
        ),
        (
            "swh:1:rel:31b5c8cc985d190b5a7ef4878128ebfdc2358f49",
            MetadataTargetType.RELEASE,
        ),
        (
            "swh:1:snp:41b5c8cc985d190b5a7ef4878128ebfdc2358f49",
            MetadataTargetType.SNAPSHOT,
        ),
        (
            "swh:1:cnt:51b5c8cc985d190b5a7ef4878128ebfdc2358f49;origin=h://g.c/o/repo",
            MetadataTargetType.CONTENT,
        ),
        (
            "swh:1:dir:c4993c872593e960dc84e4430dbbfbc34fd706d0;origin=https://inria.halpreprod.archives-ouvertes.fr/hal-01243573;visit=swh:1:snp:0175049fc45055a3824a1675ac06e3711619a55a;anchor=swh:1:rev:b5f505b005435fa5c4fa4c279792bd7b17167c04;path=/",  # noqa
            MetadataTargetType.DIRECTORY,
        ),
        (
            "swh:1:rev:71b5c8cc985d190b5a7ef4878128ebfdc2358f49;origin=h://g.c/o/repo",
            MetadataTargetType.REVISION,
        ),
        (
            "swh:1:rel:81b5c8cc985d190b5a7ef4878128ebfdc2358f49;origin=h://g.c/o/repo",
            MetadataTargetType.RELEASE,
        ),
        (
            "swh:1:snp:91b5c8cc985d190b5a7ef4878128ebfdc2358f49;origin=h://g.c/o/repo",
            MetadataTargetType.SNAPSHOT,
        ),
    ],
)
def test_deposit_metadata_swhid(
    swhid,
    target_type,
    authenticated_client,
    deposit_collection,
    atom_dataset,
    swh_storage,
):
    """Posting a swhid reference is stored on raw extrinsic metadata storage

    """
    swhid_reference = parse_swhid(swhid)
    swhid_core = attr.evolve(swhid_reference, metadata={})

    xml_data = atom_dataset["entry-data-with-swhid"].format(swhid=swhid)
    deposit_client = authenticated_client.deposit_client

    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=xml_data,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))

    # Ensure the deposit is finalized
    deposit_id = int(response_content["deposit_id"])
    deposit = Deposit.objects.get(pk=deposit_id)
    assert isinstance(swhid_core, SWHID)
    assert deposit.swhid == str(swhid_core)
    assert deposit.swhid_context == str(swhid_reference)
    assert deposit.complete_date == deposit.reception_date
    assert deposit.complete_date is not None
    assert deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS

    # Ensure metadata stored in the metadata storage is consistent
    metadata_authority = MetadataAuthority(
        type=MetadataAuthorityType.DEPOSIT_CLIENT,
        url=deposit_client.provider_url,
        metadata={"name": deposit_client.last_name},
    )

    actual_authority = swh_storage.metadata_authority_get(
        MetadataAuthorityType.DEPOSIT_CLIENT, url=deposit_client.provider_url
    )
    assert actual_authority == metadata_authority

    config = APIConfig()
    metadata_fetcher = MetadataFetcher(
        name=config.tool["name"],
        version=config.tool["version"],
        metadata=config.tool["configuration"],
    )

    actual_fetcher = swh_storage.metadata_fetcher_get(
        config.tool["name"], config.tool["version"]
    )
    assert actual_fetcher == metadata_fetcher

    page_results = swh_storage.raw_extrinsic_metadata_get(
        target_type, swhid_core, metadata_authority
    )
    discovery_date = page_results.results[0].discovery_date

    assert len(page_results.results) == 1
    assert page_results.next_page_token is None

    object_type, metadata_context = compute_metadata_context(swhid_reference)
    assert page_results == PagedResult(
        results=[
            RawExtrinsicMetadata(
                type=object_type,
                target=swhid_core,
                discovery_date=discovery_date,
                authority=attr.evolve(metadata_authority, metadata=None),
                fetcher=attr.evolve(metadata_fetcher, metadata=None),
                format="sword-v2-atom-codemeta",
                metadata=xml_data.encode(),
                **metadata_context,
            )
        ],
        next_page_token=None,
    )
    assert deposit.complete_date == discovery_date


@pytest.mark.parametrize(
    "url", ["https://gitlab.org/user/repo", "https://whatever.else/repo",]
)
def test_deposit_metadata_origin(
    url, authenticated_client, deposit_collection, atom_dataset, swh_storage,
):
    """Posting a swhid reference is stored on raw extrinsic metadata storage

    """
    xml_data = atom_dataset["entry-data-with-origin"].format(url=url)
    deposit_client = authenticated_client.deposit_client
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=xml_data,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    # Ensure the deposit is finalized
    deposit_id = int(response_content["deposit_id"])
    deposit = Deposit.objects.get(pk=deposit_id)
    # we got not swhid as input so we cannot have those
    assert deposit.swhid is None
    assert deposit.swhid_context is None
    assert deposit.complete_date == deposit.reception_date
    assert deposit.complete_date is not None
    assert deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS

    # Ensure metadata stored in the metadata storage is consistent
    metadata_authority = MetadataAuthority(
        type=MetadataAuthorityType.DEPOSIT_CLIENT,
        url=deposit_client.provider_url,
        metadata={"name": deposit_client.last_name},
    )

    actual_authority = swh_storage.metadata_authority_get(
        MetadataAuthorityType.DEPOSIT_CLIENT, url=deposit_client.provider_url
    )
    assert actual_authority == metadata_authority

    config = APIConfig()
    metadata_fetcher = MetadataFetcher(
        name=config.tool["name"],
        version=config.tool["version"],
        metadata=config.tool["configuration"],
    )

    actual_fetcher = swh_storage.metadata_fetcher_get(
        config.tool["name"], config.tool["version"]
    )
    assert actual_fetcher == metadata_fetcher

    page_results = swh_storage.raw_extrinsic_metadata_get(
        MetadataTargetType.ORIGIN, url, metadata_authority
    )
    discovery_date = page_results.results[0].discovery_date

    assert len(page_results.results) == 1
    assert page_results.next_page_token is None

    assert page_results == PagedResult(
        results=[
            RawExtrinsicMetadata(
                type=MetadataTargetType.ORIGIN,
                target=url,
                discovery_date=discovery_date,
                authority=attr.evolve(metadata_authority, metadata=None),
                fetcher=attr.evolve(metadata_fetcher, metadata=None),
                format="sword-v2-atom-codemeta",
                metadata=xml_data.encode(),
            )
        ],
        next_page_token=None,
    )
    assert deposit.complete_date == discovery_date
