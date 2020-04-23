# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.urls import reverse
from rest_framework import status

from swh.deposit.models import Deposit
from swh.deposit.config import PRIVATE_GET_DEPOSIT_METADATA, SWH_PERSON, EDIT_SE_IRI


PRIVATE_GET_DEPOSIT_METADATA_NC = PRIVATE_GET_DEPOSIT_METADATA + "-nc"


def private_get_raw_url_endpoints(collection, deposit):
    """There are 2 endpoints to check (one with collection, one without)"""
    deposit_id = deposit if isinstance(deposit, int) else deposit.id
    return [
        reverse(PRIVATE_GET_DEPOSIT_METADATA, args=[collection.name, deposit_id]),
        reverse(PRIVATE_GET_DEPOSIT_METADATA_NC, args=[deposit_id]),
    ]


def update_deposit(authenticated_client, collection, deposit, atom_dataset):
    for atom_data in ["entry-data2", "entry-data3"]:
        update_deposit_with_metadata(
            authenticated_client, collection, deposit, atom_dataset[atom_data]
        )
    return deposit


def update_deposit_with_metadata(authenticated_client, collection, deposit, metadata):
    # update deposit's metadata
    response = authenticated_client.post(
        reverse(EDIT_SE_IRI, args=[collection.name, deposit.id]),
        content_type="application/atom+xml;type=entry",
        data=metadata,
        HTTP_SLUG=deposit.external_id,
        HTTP_IN_PROGRESS=True,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return deposit


def test_read_metadata(
    authenticated_client, deposit_collection, partial_deposit, atom_dataset
):
    """Private metadata read api to existing deposit should return metadata

    """
    deposit = partial_deposit
    deposit.external_id = "some-external-id"
    deposit.save()
    deposit = update_deposit(
        authenticated_client, deposit_collection, deposit, atom_dataset
    )

    for url in private_get_raw_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response._headers["content-type"][1] == "application/json"
        data = response.json()

        expected_meta = {
            "origin": {
                "type": "deposit",
                "url": "https://hal-test.archives-ouvertes.fr/some-external-id",
            },
            "origin_metadata": {
                "metadata": {
                    "@xmlns": ["http://www.w3.org/2005/Atom"],
                    "author": ["some awesome author", "another one", "no one"],
                    "codemeta:dateCreated": "2017-10-07T15:17:08Z",
                    "external_identifier": "some-external-id",
                    "url": "https://hal-test.archives-ouvertes.fr/some-external-id",  # noqa
                },
                "provider": {
                    "metadata": {},
                    "provider_name": "",
                    "provider_type": "deposit_client",
                    "provider_url": "https://hal-test.archives-ouvertes.fr/",
                },
                "tool": {
                    "configuration": {"sword_version": "2"},
                    "name": "swh-deposit",
                    "version": "0.0.1",
                },
            },
            "deposit": {
                "author": SWH_PERSON,
                "committer": SWH_PERSON,
                "committer_date": {
                    "negative_utc": False,
                    "offset": 0,
                    "timestamp": {"microseconds": 0, "seconds": 1507389428},
                },
                "author_date": {
                    "negative_utc": False,
                    "offset": 0,
                    "timestamp": {"microseconds": 0, "seconds": 1507389428},
                },
                "client": "test",
                "id": deposit.id,
                "collection": "test",
                "revision_parents": [],
            },
        }

        assert data == expected_meta


def test_read_metadata_revision_with_parent(
    authenticated_client, deposit_collection, partial_deposit, atom_dataset
):
    """Private read metadata to a deposit (with parent) returns metadata

    """
    deposit = partial_deposit
    deposit.external_id = "some-external-id"
    deposit.save()
    deposit = update_deposit(
        authenticated_client, deposit_collection, deposit, atom_dataset
    )
    rev_id = "da78a9d4cf1d5d29873693fd496142e3a18c20fa"
    swh_id = "swh:1:rev:%s" % rev_id
    fake_parent = Deposit(
        swh_id=swh_id, client=deposit.client, collection=deposit.collection
    )
    fake_parent.save()
    deposit.parent = fake_parent
    deposit.save()

    for url in private_get_raw_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response._headers["content-type"][1] == "application/json"
        data = response.json()

        expected_meta = {
            "origin": {
                "type": "deposit",
                "url": "https://hal-test.archives-ouvertes.fr/some-external-id",
            },
            "origin_metadata": {
                "metadata": {
                    "@xmlns": ["http://www.w3.org/2005/Atom"],
                    "author": ["some awesome author", "another one", "no one"],
                    "codemeta:dateCreated": "2017-10-07T15:17:08Z",
                    "external_identifier": "some-external-id",
                    "url": "https://hal-test.archives-ouvertes.fr/some-external-id",  # noqa
                },
                "provider": {
                    "metadata": {},
                    "provider_name": "",
                    "provider_type": "deposit_client",
                    "provider_url": "https://hal-test.archives-ouvertes.fr/",
                },
                "tool": {
                    "configuration": {"sword_version": "2"},
                    "name": "swh-deposit",
                    "version": "0.0.1",
                },
            },
            "deposit": {
                "author": SWH_PERSON,
                "committer": SWH_PERSON,
                "committer_date": {
                    "negative_utc": False,
                    "offset": 0,
                    "timestamp": {"microseconds": 0, "seconds": 1507389428},
                },
                "author_date": {
                    "negative_utc": False,
                    "offset": 0,
                    "timestamp": {"microseconds": 0, "seconds": 1507389428},
                },
                "client": "test",
                "id": deposit.id,
                "collection": "test",
                "revision_parents": [rev_id],
            },
        }

        assert data == expected_meta


def test_read_metadata_3(
    authenticated_client, deposit_collection, partial_deposit, atom_dataset
):
    """date(Created|Published) provided, uses author/committer date

    """
    deposit = partial_deposit
    deposit.external_id = "hal-01243065"
    deposit.save()
    deposit = update_deposit(
        authenticated_client, deposit_collection, deposit, atom_dataset
    )
    # add metadata to the deposit with datePublished and dateCreated
    codemeta_entry_data = (
        atom_dataset["metadata"]
        % """
  <codemeta:dateCreated>2015-04-06T17:08:47+02:00</codemeta:dateCreated>
  <codemeta:datePublished>2017-05-03T16:08:47+02:00</codemeta:datePublished>
"""
    )
    update_deposit_with_metadata(
        authenticated_client, deposit_collection, deposit, codemeta_entry_data
    )

    for url in private_get_raw_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response._headers["content-type"][1] == "application/json"
        data = response.json()

        metadata = {
            "@xmlns": ["http://www.w3.org/2005/Atom"],
            "@xmlns:codemeta": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0",
            "author": [
                "some awesome author",
                "another one",
                "no one",
                {"email": "hal@ccsd.cnrs.fr", "name": "HAL"},
            ],
            "client": "hal",
            "codemeta:applicationCategory": "test",
            "codemeta:author": {"codemeta:name": "Morane Gruenpeter"},
            "codemeta:dateCreated": [
                "2017-10-07T15:17:08Z",
                "2015-04-06T17:08:47+02:00",
            ],
            "codemeta:datePublished": "2017-05-03T16:08:47+02:00",
            "codemeta:description": "this is the description",
            "codemeta:developmentStatus": "stable",
            "codemeta:keywords": "DSP programming",
            "codemeta:license": [
                {"codemeta:name": "GNU General Public License v3.0 only"},
                {
                    "codemeta:name": "CeCILL "
                    "Free "
                    "Software "
                    "License "
                    "Agreement "
                    "v1.1"
                },
            ],
            "codemeta:programmingLanguage": ["php", "python", "C"],
            "codemeta:runtimePlatform": "phpstorm",
            "codemeta:url": "https://hal-test.archives-ouvertes.fr/hal-01243065",  # noqa
            "codemeta:version": "1",
            "external_identifier": ["some-external-id", "hal-01243065"],
            "id": "hal-01243065",
            "title": "Composing a Web of Audio " "Applications",
            "url": "https://hal-test.archives-ouvertes.fr/some-external-id",
        }
        expected_meta = {
            "origin": {
                "type": "deposit",
                "url": "https://hal-test.archives-ouvertes.fr/hal-01243065",
            },
            "origin_metadata": {
                "metadata": metadata,
                "provider": {
                    "metadata": {},
                    "provider_name": "",
                    "provider_type": "deposit_client",
                    "provider_url": "https://hal-test.archives-ouvertes.fr/",
                },
                "tool": {
                    "configuration": {"sword_version": "2"},
                    "name": "swh-deposit",
                    "version": "0.0.1",
                },
            },
            "deposit": {
                "author": SWH_PERSON,
                "committer": SWH_PERSON,
                "committer_date": {
                    "negative_utc": False,
                    "offset": 120,
                    "timestamp": {"microseconds": 0, "seconds": 1493820527},
                },
                "author_date": {
                    "negative_utc": False,
                    "offset": 0,
                    "timestamp": {"microseconds": 0, "seconds": 1507389428},
                },
                "client": deposit_collection.name,
                "id": deposit.id,
                "collection": deposit_collection.name,
                "revision_parents": [],
            },
        }
        assert data == expected_meta


def test_read_metadata_4(
    authenticated_client, deposit_collection, atom_dataset, partial_deposit
):
    """dateCreated/datePublished not provided, revision uses complete_date

    """
    deposit = partial_deposit
    codemeta_entry_data = atom_dataset["metadata"] % ""
    deposit = update_deposit_with_metadata(
        authenticated_client, deposit_collection, deposit, codemeta_entry_data
    )

    # will use the deposit completed date as fallback date
    deposit.complete_date = "2016-04-06"
    deposit.save()

    for url in private_get_raw_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response._headers["content-type"][1] == "application/json"
        data = response.json()

        metadata = {
            "@xmlns": "http://www.w3.org/2005/Atom",
            "@xmlns:codemeta": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0",
            "author": {"email": "hal@ccsd.cnrs.fr", "name": "HAL"},
            "client": "hal",
            "codemeta:applicationCategory": "test",
            "codemeta:author": {"codemeta:name": "Morane " "Gruenpeter"},
            "codemeta:description": "this is the " "description",
            "codemeta:developmentStatus": "stable",
            "codemeta:keywords": "DSP programming",
            "codemeta:license": [
                {
                    "codemeta:name": "GNU "
                    "General "
                    "Public "
                    "License "
                    "v3.0 "
                    "only"
                },
                {
                    "codemeta:name": "CeCILL "
                    "Free "
                    "Software "
                    "License "
                    "Agreement "
                    "v1.1"
                },
            ],
            "codemeta:programmingLanguage": ["php", "python", "C"],
            "codemeta:runtimePlatform": "phpstorm",
            "codemeta:url": "https://hal-test.archives-ouvertes.fr/hal-01243065",
            "codemeta:version": "1",
            "external_identifier": "hal-01243065",
            "id": "hal-01243065",
            "title": "Composing a Web of Audio " "Applications",
        }

        expected_origin = {
            "type": "deposit",
            "url": "https://hal-test.archives-ouvertes.fr/%s" % (deposit.external_id),
        }

        expected_origin_metadata = {
            "metadata": metadata,
            "provider": {
                "metadata": {},
                "provider_name": "",
                "provider_type": "deposit_client",
                "provider_url": "https://hal-test.archives-ouvertes.fr/",
            },
            "tool": {
                "configuration": {"sword_version": "2"},
                "name": "swh-deposit",
                "version": "0.0.1",
            },
        }

        expected_deposit_info = {
            "author": SWH_PERSON,
            "committer": SWH_PERSON,
            "committer_date": {
                "negative_utc": False,
                "offset": 0,
                "timestamp": {"microseconds": 0, "seconds": 1459900800},
            },
            "author_date": {
                "negative_utc": False,
                "offset": 0,
                "timestamp": {"microseconds": 0, "seconds": 1459900800},
            },
            "client": deposit_collection.name,
            "id": deposit.id,
            "collection": deposit_collection.name,
            "revision_parents": [],
        }

        expected_meta = {
            "origin": expected_origin,
            "origin_metadata": expected_origin_metadata,
            "deposit": expected_deposit_info,
        }

        assert data == expected_meta


def test_read_metadata_5(
    authenticated_client, deposit_collection, partial_deposit, atom_dataset
):
    """dateCreated/datePublished provided, revision uses author/committer
       date

    If multiple dateCreated provided, the first occurrence (of
    dateCreated) is selected.  If multiple datePublished provided,
    the first occurrence (of datePublished) is selected.

    """
    deposit = partial_deposit
    # add metadata to the deposit with multiple datePublished/dateCreated
    codemeta_entry_data = (
        atom_dataset["metadata"]
        % """
  <codemeta:dateCreated>2015-04-06T17:08:47+02:00</codemeta:dateCreated>
  <codemeta:datePublished>2017-05-03T16:08:47+02:00</codemeta:datePublished>
  <codemeta:dateCreated>2016-04-06T17:08:47+02:00</codemeta:dateCreated>
  <codemeta:datePublished>2018-05-03T16:08:47+02:00</codemeta:datePublished>
"""
    )
    deposit = update_deposit_with_metadata(
        authenticated_client, deposit_collection, deposit, codemeta_entry_data
    )

    for url in private_get_raw_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response._headers["content-type"][1] == "application/json"
        data = response.json()

        expected_origin = {
            "type": "deposit",
            "url": "https://hal-test.archives-ouvertes.fr/external-id-partial",
        }

        metadata = {
            "@xmlns": "http://www.w3.org/2005/Atom",
            "@xmlns:codemeta": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0",
            "author": {"email": "hal@ccsd.cnrs.fr", "name": "HAL"},
            "client": "hal",
            "codemeta:applicationCategory": "test",
            "codemeta:author": {"codemeta:name": "Morane " "Gruenpeter"},
            "codemeta:dateCreated": [
                "2015-04-06T17:08:47+02:00",
                "2016-04-06T17:08:47+02:00",
            ],
            "codemeta:datePublished": [
                "2017-05-03T16:08:47+02:00",
                "2018-05-03T16:08:47+02:00",
            ],
            "codemeta:description": "this is the description",
            "codemeta:developmentStatus": "stable",
            "codemeta:keywords": "DSP programming",
            "codemeta:license": [
                {
                    "codemeta:name": "GNU "
                    "General "
                    "Public "
                    "License "
                    "v3.0 "
                    "only"
                },
                {
                    "codemeta:name": "CeCILL "
                    "Free "
                    "Software "
                    "License "
                    "Agreement "
                    "v1.1"
                },
            ],
            "codemeta:programmingLanguage": ["php", "python", "C"],
            "codemeta:runtimePlatform": "phpstorm",
            "codemeta:url": "https://hal-test.archives-ouvertes.fr/hal-01243065",  # noqa
            "codemeta:version": "1",
            "external_identifier": "hal-01243065",
            "id": "hal-01243065",
            "title": "Composing a Web of Audio " "Applications",
        }

        expected_origin_metadata = {
            "metadata": metadata,
            "provider": {
                "metadata": {},
                "provider_name": "",
                "provider_type": "deposit_client",
                "provider_url": "https://hal-test.archives-ouvertes.fr/",
            },
            "tool": {
                "configuration": {"sword_version": "2"},
                "name": "swh-deposit",
                "version": "0.0.1",
            },
        }

        expected_deposit_info = {
            "author": SWH_PERSON,
            "committer": SWH_PERSON,
            "committer_date": {
                "negative_utc": False,
                "offset": 120,
                "timestamp": {"microseconds": 0, "seconds": 1493820527},
            },
            "author_date": {
                "negative_utc": False,
                "offset": 120,
                "timestamp": {"microseconds": 0, "seconds": 1428332927},
            },
            "client": deposit_collection.name,
            "id": deposit.id,
            "collection": deposit_collection.name,
            "revision_parents": [],
        }

        expected_meta = {
            "origin": expected_origin,
            "origin_metadata": expected_origin_metadata,
            "deposit": expected_deposit_info,
        }

        assert data == expected_meta


def test_access_to_nonexisting_deposit_returns_404_response(
    authenticated_client, deposit_collection,
):
    """Read unknown collection should return a 404 response

    """
    unknown_id = 999
    try:
        Deposit.objects.get(pk=unknown_id)
    except Deposit.DoesNotExist:
        assert True

    for url in private_get_raw_url_endpoints(deposit_collection, unknown_id):
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        msg = "Deposit with id %s does not exist" % unknown_id
        assert msg in response.content.decode("utf-8")
