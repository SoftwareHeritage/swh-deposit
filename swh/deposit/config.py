# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import logging

from typing import Any, Dict, Tuple

from swh.core.config import SWHConfig
from swh.scheduler import get_scheduler

# IRIs (Internationalized Resource identifier) sword 2.0 specified
EDIT_SE_IRI = "edit_se_iri"
EM_IRI = "em_iri"
CONT_FILE_IRI = "cont_file_iri"
SD_IRI = "servicedocument"
COL_IRI = "upload"
STATE_IRI = "state_iri"
PRIVATE_GET_RAW_CONTENT = "private-download"
PRIVATE_CHECK_DEPOSIT = "check-deposit"
PRIVATE_PUT_DEPOSIT = "private-update"
PRIVATE_GET_DEPOSIT_METADATA = "private-read"
PRIVATE_LIST_DEPOSITS = "private-deposit-list"

ARCHIVE_KEY = "archive"
METADATA_KEY = "metadata"
RAW_METADATA_KEY = "raw-metadata"

ARCHIVE_TYPE = "archive"
METADATA_TYPE = "metadata"


AUTHORIZED_PLATFORMS = ["development", "production", "testing"]

DEPOSIT_STATUS_REJECTED = "rejected"
DEPOSIT_STATUS_PARTIAL = "partial"
DEPOSIT_STATUS_DEPOSITED = "deposited"
DEPOSIT_STATUS_VERIFIED = "verified"
DEPOSIT_STATUS_LOAD_SUCCESS = "done"
DEPOSIT_STATUS_LOAD_FAILURE = "failed"

# Revision author for deposit
SWH_PERSON = {
    "name": "Software Heritage",
    "fullname": "Software Heritage",
    "email": "robot@softwareheritage.org",
}


def setup_django_for(platform=None, config_file=None):
    """Setup function for command line tools (swh.deposit.create_user) to
       initialize the needed db access.

    Note:
        Do not import any django related module prior to this function
        call. Otherwise, this will raise an
        django.core.exceptions.ImproperlyConfigured error message.

    Args:
        platform (str): the platform the scheduling is running
        config_file (str): Extra configuration file (typically for the
                           production platform)

    Raises:
        ValueError in case of wrong platform inputs.

    """
    if platform is not None:
        if platform not in AUTHORIZED_PLATFORMS:
            raise ValueError("Platform should be one of %s" % AUTHORIZED_PLATFORMS)
        if "DJANGO_SETTINGS_MODULE" not in os.environ:
            os.environ["DJANGO_SETTINGS_MODULE"] = "swh.deposit.settings.%s" % platform

    if config_file:
        os.environ.setdefault("SWH_CONFIG_FILENAME", config_file)

    import django

    django.setup()


class SWHDefaultConfig(SWHConfig):
    """Mixin intended to enrich views with SWH configuration.

    """

    CONFIG_BASE_FILENAME = "deposit/server"

    DEFAULT_CONFIG = {
        "max_upload_size": ("int", 209715200),
        "checks": ("bool", True),
        "scheduler": (
            "dict",
            {"cls": "remote", "args": {"url": "http://localhost:5008/"}},
        ),
    }

    ADDITIONAL_CONFIG = {}  # type: Dict[str, Tuple[str, Any]]

    def __init__(self, **config):
        super().__init__()
        self.config = self.parse_config_file(
            additional_configs=[self.ADDITIONAL_CONFIG]
        )
        self.config.update(config)
        self.log = logging.getLogger("swh.deposit")
        if self.config.get("scheduler"):
            self.scheduler = get_scheduler(**self.config["scheduler"])
