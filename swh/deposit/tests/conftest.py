# Copyright (C) 2019-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import base64
from copy import deepcopy
from functools import partial
from io import BytesIO
import os
import re
from typing import TYPE_CHECKING, Dict, Mapping

from django.test.utils import setup_databases  # type: ignore
from django.urls import reverse_lazy as reverse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pytest
from rest_framework import status
from rest_framework.test import APIClient
import yaml

from swh.auth.pytest_plugin import keycloak_mock_factory
from swh.core.config import read
from swh.core.pytest_plugin import get_response_cb
from swh.deposit.auth import DEPOSIT_PERMISSION
from swh.deposit.config import (
    COL_IRI,
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_LOAD_FAILURE,
    DEPOSIT_STATUS_LOAD_SUCCESS,
    DEPOSIT_STATUS_PARTIAL,
    DEPOSIT_STATUS_REJECTED,
    DEPOSIT_STATUS_VERIFIED,
    SE_IRI,
    setup_django_for,
)
from swh.deposit.parsers import parse_xml
from swh.deposit.tests.common import (
    create_arborescence_archive,
    post_archive,
    post_atom,
)
from swh.model.hashutil import hash_to_bytes
from swh.model.swhids import CoreSWHID, ObjectType, QualifiedSWHID
from swh.scheduler import get_scheduler

if TYPE_CHECKING:
    from swh.deposit.models import Deposit, DepositClient, DepositCollection


# mypy is asked to ignore the import statement above because setup_databases
# is not part of the d.t.utils.__all__ variable.

USERNAME = "test"
EMAIL = "test@example.org"
COLLECTION = "test"

TEST_USER = {
    "username": USERNAME,
    "password": "pass",
    "email": EMAIL,
    "provider_url": "https://hal-test.archives-ouvertes.fr/",
    "domain": "archives-ouvertes.fr/",
    "collection": {"name": COLLECTION},
}

USER_INFO = {
    "name": USERNAME,
    "email": EMAIL,
    "email_verified": False,
    "family_name": "",
    "given_name": "",
    "groups": [],
    "preferred_username": USERNAME,
    "sub": "ffffffff-bbbb-4444-aaaa-14f61e6b7200",
}

USERNAME2 = "test2"
EMAIL2 = "test@example.org"
COLLECTION2 = "another-collection"

TEST_USER2 = {
    "username": USERNAME2,
    "password": "",
    "email": EMAIL2,
    "provider_url": "https://hal-test.archives-ouvertes.example/",
    "domain": "archives-ouvertes.example/",
    "collection": {"name": COLLECTION2},
}

KEYCLOAK_SERVER_URL = "https://auth.swh.org/SWHTest"
KEYCLOAK_REALM_NAME = "SWHTest"
CLIENT_ID = "swh-deposit"


keycloak_mock_auth_success = keycloak_mock_factory(
    server_url=KEYCLOAK_SERVER_URL,
    realm_name=KEYCLOAK_REALM_NAME,
    client_id=CLIENT_ID,
    auth_success=True,
    user_info=USER_INFO,
    client_permissions=[DEPOSIT_PERMISSION],
)


keycloak_mock_auth_failure = keycloak_mock_factory(
    server_url=KEYCLOAK_SERVER_URL,
    realm_name=KEYCLOAK_REALM_NAME,
    client_id=CLIENT_ID,
    auth_success=False,
)


def pytest_configure():
    setup_django_for("testing")


@pytest.fixture
def requests_mock_datadir(datadir, requests_mock_datadir):
    """Override default behavior to deal with put/post methods

    """
    cb = partial(get_response_cb, datadir=datadir)
    requests_mock_datadir.put(re.compile("https://"), body=cb)
    requests_mock_datadir.post(re.compile("https://"), body=cb)
    return requests_mock_datadir


@pytest.fixture
def common_deposit_config(swh_scheduler_config, swh_storage_backend_config):
    return {
        "max_upload_size": 500,
        "extraction_dir": "/tmp/swh-deposit/test/extraction-dir",
        "checks": False,
        "scheduler": {"cls": "local", **swh_scheduler_config,},
        "storage": swh_storage_backend_config,
        "storage_metadata": swh_storage_backend_config,
        "swh_authority_url": "http://deposit.softwareheritage.example/",
    }


@pytest.fixture()
def deposit_config(common_deposit_config):
    return {
        **common_deposit_config,
        "authentication_provider": "keycloak",
        "keycloak": {
            "server_url": KEYCLOAK_SERVER_URL,
            "realm_name": KEYCLOAK_REALM_NAME,
        },
    }


@pytest.fixture()
def deposit_config_path(tmp_path, monkeypatch, deposit_config):
    conf_path = os.path.join(tmp_path, "deposit.yml")
    with open(conf_path, "w") as f:
        f.write(yaml.dump(deposit_config))
    monkeypatch.setenv("SWH_CONFIG_FILENAME", conf_path)
    return conf_path


@pytest.fixture(autouse=True)
def deposit_autoconfig(deposit_config_path):
    """Enforce config for deposit classes inherited from APIConfig."""
    cfg = read(deposit_config_path)

    if "scheduler" in cfg:
        # scheduler setup: require the check-deposit and load-deposit tasks
        scheduler = get_scheduler(**cfg["scheduler"])
        task_types = [
            {
                "type": "check-deposit",
                "backend_name": "swh.deposit.loader.tasks.ChecksDepositTsk",
                "description": "Check deposit metadata/archive before loading",
                "num_retries": 3,
            },
            {
                "type": "load-deposit",
                "backend_name": "swh.loader.package.deposit.tasks.LoadDeposit",
                "description": "Loading deposit archive into swh archive",
                "num_retries": 3,
            },
        ]
        for task_type in task_types:
            scheduler.create_task_type(task_type)


@pytest.fixture(scope="session")
def django_db_setup(request, django_db_blocker, postgresql_proc):
    from django.conf import settings

    settings.DATABASES["default"].update(
        {
            ("ENGINE", "django.db.backends.postgresql"),
            ("NAME", "tests"),
            ("USER", postgresql_proc.user),  # noqa
            ("HOST", postgresql_proc.host),  # noqa
            ("PORT", postgresql_proc.port),  # noqa
        }
    )
    with django_db_blocker.unblock():
        setup_databases(
            verbosity=request.config.option.verbose, interactive=False, keepdb=False
        )


def execute_sql(sql):
    """Execute sql to postgres db"""
    with psycopg2.connect(database="postgres") as conn:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(sql)


@pytest.fixture(autouse=True, scope="session")
def swh_proxy():
    """Automatically inject this fixture in all tests to ensure no outside
       connection takes place.

    """
    os.environ["http_proxy"] = "http://localhost:999"
    os.environ["https_proxy"] = "http://localhost:999"


def create_deposit_collection(collection_name: str):
    """Create a deposit collection with name collection_name

    """
    from swh.deposit.models import DepositCollection

    try:
        collection = DepositCollection._default_manager.get(name=collection_name)
    except DepositCollection.DoesNotExist:
        collection = DepositCollection(name=collection_name)
        collection.save()
    return collection


def deposit_collection_factory(collection_name):
    @pytest.fixture
    def _deposit_collection(db, collection_name=collection_name):
        return create_deposit_collection(collection_name)

    return _deposit_collection


deposit_collection = deposit_collection_factory(COLLECTION)
deposit_another_collection = deposit_collection_factory(COLLECTION2)


def _create_deposit_user(
    collection: "DepositCollection", user_data: Dict
) -> "DepositClient":
    """Create/Return the test_user "test"

    For basic authentication, this will save a password.
    This is not required for keycloak authentication scheme.

    """
    from swh.deposit.models import DepositClient

    user_data_d = deepcopy(user_data)
    user_data_d.pop("collection", None)
    passwd = user_data_d.pop("password", None)
    user, _ = DepositClient.objects.get_or_create(  # type: ignore
        username=user_data_d["username"],
        defaults={**user_data_d, "collections": [collection.id]},
    )
    if passwd:
        user.set_password(passwd)
        user.save()

    return user


@pytest.fixture
def deposit_user(db, deposit_collection):
    return _create_deposit_user(deposit_collection, TEST_USER)


@pytest.fixture
def deposit_another_user(db, deposit_another_collection):
    return _create_deposit_user(deposit_another_collection, TEST_USER2)


@pytest.fixture
def anonymous_client():
    """Create an anonymous client (no credentials during queries to the deposit)

    """
    return APIClient()  # <- drf's client


def mock_keycloakopenidconnect(mocker, keycloak_mock):
    """Mock swh.deposit.auth.KeycloakOpenIDConnect to return the keycloak_mock

    """
    mock = mocker.patch("swh.deposit.auth.KeycloakOpenIDConnect")
    mock.from_configfile.return_value = keycloak_mock
    return mock


@pytest.fixture
def mock_keycloakopenidconnect_ok(mocker, keycloak_mock_auth_success):
    """Mock keycloak so it always accepts connection for user with the right
       permissions

    """
    return mock_keycloakopenidconnect(mocker, keycloak_mock_auth_success)


@pytest.fixture
def mock_keycloakopenidconnect_ko(mocker, keycloak_mock_auth_failure):
    """Mock keycloak so it always refuses connections."""
    return mock_keycloakopenidconnect(mocker, keycloak_mock_auth_failure)


def _create_authenticated_client(client, user, password=None):
    """Return a client whose credentials will be proposed to the deposit server.

    This also patched the client instance to keep a reference on the associated
    deposit_user.

    """
    if not password:
        password = "irrelevant-if-not-set"
    _token = "%s:%s" % (user.username, password)
    token = base64.b64encode(_token.encode("utf-8"))
    authorization = "Basic %s" % token.decode("utf-8")
    client.credentials(HTTP_AUTHORIZATION=authorization)
    client.deposit_client = user
    yield client
    client.logout()


@pytest.fixture
def basic_authenticated_client(anonymous_client, deposit_user):
    yield from _create_authenticated_client(
        anonymous_client, deposit_user, password=TEST_USER["password"]
    )


@pytest.fixture
def authenticated_client(mock_keycloakopenidconnect_ok, anonymous_client, deposit_user):
    yield from _create_authenticated_client(anonymous_client, deposit_user)


@pytest.fixture
def unauthorized_client(mock_keycloakopenidconnect_ko, anonymous_client, deposit_user):
    """Create an unauthorized client (will see their authentication fail)

    """
    yield from _create_authenticated_client(anonymous_client, deposit_user)


@pytest.fixture
def insufficient_perm_client(
    mocker, keycloak_mock_auth_success, anonymous_client, deposit_user
):
    """keycloak accepts connection but client returned has no deposit permission, so access
       is not allowed.

    """
    keycloak_mock_auth_success.client_permissions = []
    mock_keycloakopenidconnect(mocker, keycloak_mock_auth_success)
    yield from _create_authenticated_client(anonymous_client, deposit_user)


@pytest.fixture
def sample_archive(tmp_path):
    """Returns a sample archive

    """
    tmp_path = str(tmp_path)  # pytest version limitation in previous version
    archive = create_arborescence_archive(
        tmp_path, "archive1", "file1", b"some content in file"
    )

    return archive


@pytest.fixture
def atom_dataset(datadir) -> Mapping[str, str]:
    """Compute the paths to atom files.

    Returns:
        Dict of atom name per content (bytes)

    """
    atom_path = os.path.join(datadir, "atom")
    data = {}
    for filename in os.listdir(atom_path):
        filepath = os.path.join(atom_path, filename)
        with open(filepath, "rb") as f:
            raw_content = f.read().decode("utf-8")

        # Keep the filename without extension
        atom_name = filename.split(".")[0]
        data[atom_name] = raw_content

    return data


def internal_create_deposit(
    client: "DepositClient",
    collection: "DepositCollection",
    external_id: str,
    status: str,
) -> "Deposit":
    """Create a deposit for a given collection with internal tool

    """
    from swh.deposit.models import Deposit

    deposit = Deposit(
        client=client, external_id=external_id, status=status, collection=collection
    )
    deposit.save()
    return deposit


def create_deposit(
    client,
    collection_name: str,
    sample_archive,
    external_id: str,
    deposit_status=DEPOSIT_STATUS_DEPOSITED,
    in_progress=False,
):
    """Create a skeleton shell deposit

    """
    url = reverse(COL_IRI, args=[collection_name])
    # when
    response = post_archive(
        client,
        url,
        sample_archive,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS=str(in_progress).lower(),
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED, response.content.decode()
    from swh.deposit.models import Deposit

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]
    deposit = Deposit._default_manager.get(id=deposit_id)

    if deposit.status != deposit_status:
        deposit.status = deposit_status
        deposit.save()
    assert deposit.status == deposit_status
    return deposit


def create_binary_deposit(
    authenticated_client,
    collection_name: str,
    deposit_status: str = DEPOSIT_STATUS_DEPOSITED,
    atom_dataset: Mapping[str, bytes] = {},
    **kwargs,
):
    """Create a deposit with both metadata and archive set. Then alters its status
       to `deposit_status`.

    """
    deposit = create_deposit(
        authenticated_client,
        collection_name,
        deposit_status=DEPOSIT_STATUS_PARTIAL,
        **kwargs,
    )

    origin_url = deposit.client.provider_url + deposit.external_id

    response = post_atom(
        authenticated_client,
        reverse(SE_IRI, args=[collection_name, deposit.id]),
        data=atom_dataset["entry-data0"] % origin_url,
        HTTP_IN_PROGRESS="true",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert deposit.status == DEPOSIT_STATUS_PARTIAL

    from swh.deposit.models import Deposit

    deposit = Deposit._default_manager.get(pk=deposit.id)

    assert deposit.status == deposit_status
    return deposit


def deposit_factory(deposit_status=DEPOSIT_STATUS_DEPOSITED, in_progress=False):
    """Build deposit with a specific status

    """

    @pytest.fixture()
    def _deposit(
        sample_archive,
        deposit_collection,
        authenticated_client,
        deposit_status=deposit_status,
    ):
        external_id = "external-id-%s" % deposit_status
        return create_deposit(
            authenticated_client,
            deposit_collection.name,
            sample_archive,
            external_id=external_id,
            deposit_status=deposit_status,
            in_progress=in_progress,
        )

    return _deposit


deposited_deposit = deposit_factory()
rejected_deposit = deposit_factory(deposit_status=DEPOSIT_STATUS_REJECTED)
partial_deposit = deposit_factory(
    deposit_status=DEPOSIT_STATUS_PARTIAL, in_progress=True
)
verified_deposit = deposit_factory(deposit_status=DEPOSIT_STATUS_VERIFIED)
completed_deposit = deposit_factory(deposit_status=DEPOSIT_STATUS_LOAD_SUCCESS)
failed_deposit = deposit_factory(deposit_status=DEPOSIT_STATUS_LOAD_FAILURE)


@pytest.fixture
def partial_deposit_with_metadata(
    sample_archive, deposit_collection, authenticated_client, atom_dataset
):
    """Returns deposit with archive and metadata provided, status 'partial'

    """
    return create_binary_deposit(
        authenticated_client,
        deposit_collection.name,
        sample_archive=sample_archive,
        external_id="external-id-partial",
        in_progress=True,
        deposit_status=DEPOSIT_STATUS_PARTIAL,
        atom_dataset=atom_dataset,
    )


@pytest.fixture
def partial_deposit_only_metadata(
    deposit_collection, authenticated_client, atom_dataset
):

    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data1"],
        HTTP_SLUG="external-id-partial",
        HTTP_IN_PROGRESS=True,
    )

    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(response.content)
    deposit_id = response_content["swh:deposit_id"]
    from swh.deposit.models import Deposit

    deposit = Deposit._default_manager.get(pk=deposit_id)
    assert deposit.status == DEPOSIT_STATUS_PARTIAL
    return deposit


@pytest.fixture
def complete_deposit(sample_archive, deposit_collection, authenticated_client):
    """Returns a completed deposit (load success)

    """
    deposit = create_deposit(
        authenticated_client,
        deposit_collection.name,
        sample_archive,
        external_id="external-id-complete",
        deposit_status=DEPOSIT_STATUS_LOAD_SUCCESS,
    )
    origin = "https://hal.archives-ouvertes.fr/hal-01727745"
    directory_id = "42a13fc721c8716ff695d0d62fc851d641f3a12b"
    release_id = hash_to_bytes("548b3c0a2bb43e1fca191e24b5803ff6b3bc7c10")
    snapshot_id = hash_to_bytes("e5e82d064a9c3df7464223042e0c55d72ccff7f0")
    deposit.swhid = f"swh:1:dir:{directory_id}"
    deposit.swhid_context = str(
        QualifiedSWHID(
            object_type=ObjectType.DIRECTORY,
            object_id=hash_to_bytes(directory_id),
            origin=origin,
            visit=CoreSWHID(object_type=ObjectType.SNAPSHOT, object_id=snapshot_id),
            anchor=CoreSWHID(object_type=ObjectType.RELEASE, object_id=release_id),
            path=b"/",
        )
    )
    deposit.save()
    return deposit


@pytest.fixture()
def tmp_path(tmp_path):
    return str(tmp_path)  # issue with oldstable's pytest version
