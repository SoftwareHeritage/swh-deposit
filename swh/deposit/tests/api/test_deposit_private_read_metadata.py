# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.urls import reverse_lazy as reverse
from rest_framework import status

from swh.deposit import __version__, utils
from swh.deposit.config import PRIVATE_GET_DEPOSIT_METADATA, SE_IRI, SWH_PERSON
from swh.deposit.models import Deposit
from swh.deposit.parsers import parse_xml

PRIVATE_GET_DEPOSIT_METADATA_NC = PRIVATE_GET_DEPOSIT_METADATA + "-nc"


def private_get_raw_url_endpoints(collection, deposit):
    """There are 2 endpoints to check (one with collection, one without)"""
    deposit_id = deposit if isinstance(deposit, int) else deposit.id
    return [
        reverse(PRIVATE_GET_DEPOSIT_METADATA, args=[collection.name, deposit_id]),
        reverse(PRIVATE_GET_DEPOSIT_METADATA_NC, args=[deposit_id]),
    ]


def update_deposit_with_metadata(authenticated_client, collection, deposit, metadata):
    # update deposit's metadata
    response = authenticated_client.post(
        reverse(SE_IRI, args=[collection.name, deposit.id]),
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
    deposit.origin_url = f"https://hal-test.archives-ouvertes.fr/{deposit.external_id}"
    deposit.save()

    metadata_xml_atoms = [
        atom_dataset[atom_key] for atom_key in ["entry-data2", "entry-data3"]
    ]
    metadata_xml_raws = [parse_xml(xml) for xml in metadata_xml_atoms]
    for atom_xml in metadata_xml_atoms:
        deposit = update_deposit_with_metadata(
            authenticated_client, deposit_collection, deposit, atom_xml,
        )

    for url in private_get_raw_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response._headers["content-type"][1] == "application/json"
        actual_data = response.json()
        assert actual_data == {
            "origin": {
                "type": "deposit",
                "url": "https://hal-test.archives-ouvertes.fr/some-external-id",
            },
            "metadata_raw": metadata_xml_atoms,
            "metadata_dict": utils.merge(*metadata_xml_raws),
            "provider": {
                "metadata": {},
                "provider_name": "",
                "provider_type": "deposit_client",
                "provider_url": "https://hal-test.archives-ouvertes.fr/",
            },
            "tool": {
                "configuration": {"sword_version": "2"},
                "name": "swh-deposit",
                "version": __version__,
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


def test_read_metadata_revision_with_parent(
    authenticated_client, deposit_collection, partial_deposit, atom_dataset
):
    """Private read metadata to a deposit (with parent) returns metadata

    """
    deposit = partial_deposit
    deposit.external_id = "some-external-id"
    deposit.origin_url = f"https://hal-test.archives-ouvertes.fr/{deposit.external_id}"
    deposit.save()
    metadata_xml_atoms = [
        atom_dataset[atom_key] for atom_key in ["entry-data2", "entry-data3"]
    ]
    metadata_xml_raws = [parse_xml(xml) for xml in metadata_xml_atoms]
    for atom_xml in metadata_xml_atoms:
        deposit = update_deposit_with_metadata(
            authenticated_client, deposit_collection, deposit, atom_xml,
        )

    rev_id = "da78a9d4cf1d5d29873693fd496142e3a18c20fa"
    swhid = "swh:1:rev:%s" % rev_id
    fake_parent = Deposit(
        swhid=swhid, client=deposit.client, collection=deposit.collection
    )
    fake_parent.save()
    deposit.parent = fake_parent
    deposit.save()

    for url in private_get_raw_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response._headers["content-type"][1] == "application/json"
        actual_data = response.json()
        assert actual_data == {
            "origin": {
                "type": "deposit",
                "url": "https://hal-test.archives-ouvertes.fr/some-external-id",
            },
            "metadata_raw": metadata_xml_atoms,
            "metadata_dict": utils.merge(*metadata_xml_raws),
            "provider": {
                "metadata": {},
                "provider_name": "",
                "provider_type": "deposit_client",
                "provider_url": "https://hal-test.archives-ouvertes.fr/",
            },
            "tool": {
                "configuration": {"sword_version": "2"},
                "name": "swh-deposit",
                "version": __version__,
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


def test_read_metadata_3(
    authenticated_client, deposit_collection, partial_deposit, atom_dataset
):
    """date(Created|Published) provided, uses author/committer date

    """
    deposit = partial_deposit
    deposit.external_id = "hal-01243065"
    deposit.origin_url = f"https://hal-test.archives-ouvertes.fr/{deposit.external_id}"
    deposit.save()

    # add metadata to the deposit with datePublished and dateCreated
    codemeta_entry_data = (
        atom_dataset["metadata"]
        % """
  <codemeta:dateCreated>2015-04-06T17:08:47+02:00</codemeta:dateCreated>
  <codemeta:datePublished>2017-05-03T16:08:47+02:00</codemeta:datePublished>
"""
    )
    metadata_xml_atoms = [
        atom_dataset["entry-data2"],
        atom_dataset["entry-data3"],
        codemeta_entry_data,
    ]
    metadata_xml_raws = [parse_xml(xml) for xml in metadata_xml_atoms]
    for atom_xml in metadata_xml_atoms:
        update_deposit_with_metadata(
            authenticated_client, deposit_collection, deposit, atom_xml,
        )

    for url in private_get_raw_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response._headers["content-type"][1] == "application/json"
        actual_data = response.json()
        assert actual_data == {
            "origin": {
                "type": "deposit",
                "url": "https://hal-test.archives-ouvertes.fr/hal-01243065",
            },
            "metadata_raw": metadata_xml_atoms,
            "metadata_dict": utils.merge(*metadata_xml_raws),
            "provider": {
                "metadata": {},
                "provider_name": "",
                "provider_type": "deposit_client",
                "provider_url": "https://hal-test.archives-ouvertes.fr/",
            },
            "tool": {
                "configuration": {"sword_version": "2"},
                "name": "swh-deposit",
                "version": __version__,
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
        actual_data = response.json()

        assert actual_data == {
            "origin": {"type": "deposit", "url": None,},
            "metadata_raw": [codemeta_entry_data],
            "metadata_dict": parse_xml(codemeta_entry_data),
            "provider": {
                "metadata": {},
                "provider_name": "",
                "provider_type": "deposit_client",
                "provider_url": "https://hal-test.archives-ouvertes.fr/",
            },
            "tool": {
                "configuration": {"sword_version": "2"},
                "name": "swh-deposit",
                "version": __version__,
            },
            "deposit": {
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
            },
        }


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
        actual_data = response.json()

        assert actual_data == {
            "origin": {
                "type": "deposit",
                "url": "https://hal-test.archives-ouvertes.fr/hal-01243065",
            },
            "metadata_raw": [codemeta_entry_data],
            "metadata_dict": parse_xml(codemeta_entry_data),
            "provider": {
                "metadata": {},
                "provider_name": "",
                "provider_type": "deposit_client",
                "provider_url": "https://hal-test.archives-ouvertes.fr/",
            },
            "tool": {
                "configuration": {"sword_version": "2"},
                "name": "swh-deposit",
                "version": __version__,
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
                    "offset": 120,
                    "timestamp": {"microseconds": 0, "seconds": 1428332927},
                },
                "client": deposit_collection.name,
                "id": deposit.id,
                "collection": deposit_collection.name,
                "revision_parents": [],
            },
        }


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
        msg = "Deposit %s does not exist" % unknown_id
        assert msg in response.content.decode("utf-8")
