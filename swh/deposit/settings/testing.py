# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from .common import *  # noqa
from .common import ALLOWED_HOSTS
from .development import *  # noqa
from .development import INSTALLED_APPS

# django setup
ALLOWED_HOSTS += ["testserver"]

INSTALLED_APPS += ["pytest_django"]

# https://docs.djangoproject.com/en/1.10/ref/settings/#logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",  # noqa
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {"swh.deposit": {"handlers": ["console"], "level": "ERROR",},},
}

# https://docs.djangoproject.com/en/1.11/ref/settings/#std:setting-MEDIA_ROOT
# SECURITY WARNING: Override this in the production.py module
MEDIA_ROOT = "/tmp/swh-deposit/test/uploads/"

FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
]
