# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from .common import *  # noqa

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "development-key"

# https://docs.djangoproject.com/en/1.10/ref/settings/#logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",  # noqa
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "DEBUG", "propagate": True,},
        "django.db.backends": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "swh.deposit": {"handlers": ["console"], "level": "DEBUG",},
    },
}

# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "swh-deposit-dev",  # this is no longer used in test env
    }
}

# https://docs.djangoproject.com/en/1.11/ref/settings/#std:setting-MEDIA_ROOT
# SECURITY WARNING: Override this in the production.py module
MEDIA_ROOT = "/tmp/swh-deposit/uploads/"
