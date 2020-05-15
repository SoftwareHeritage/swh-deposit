# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os

from .common import *  # noqa
from .common import ALLOWED_HOSTS
from swh.core import config

ALLOWED_HOSTS += ["deposit.softwareheritage.org"]
# Setup support for proxy headers
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

DEBUG = False

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
# https://docs.djangoproject.com/en/1.10/ref/settings/#std:setting-DATABASES
# https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/#databases

# Retrieve the deposit's configuration file
# and check the required setup is ok
# If not raise an error explaining the errors
config_file = os.environ.get("SWH_CONFIG_FILENAME")
if not config_file:
    raise ValueError(
        "Production: SWH_CONFIG_FILENAME must be set to the"
        " configuration file needed!"
    )

if not os.path.exists(config_file):
    raise ValueError(
        "Production: configuration file %s does not exist!" % (config_file,)
    )

conf = config.load_named_config(config_file)
if not conf:
    raise ValueError("Production: configuration %s does not exist." % (config_file,))

for key in ("scheduler", "private"):
    if not conf.get(key):
        raise ValueError(
            "Production: invalid configuration; missing %s config entry." % (key,)
        )

ALLOWED_HOSTS += conf.get("allowed_hosts", [])

private_conf = conf["private"]
SECRET_KEY = private_conf["secret_key"]

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
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": True,},
    },
}

# database

db_conf = private_conf.get("db", {"name": "unset"})

db = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": db_conf["name"],
}

db_user = db_conf.get("user")
if db_user:
    db["USER"] = db_user


db_pass = db_conf.get("password")
if db_pass:
    db["PASSWORD"] = db_pass

db_host = db_conf.get("host")
if db_host:
    db["HOST"] = db_host

db_port = db_conf.get("port")
if db_port:
    db["PORT"] = db_port

# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
DATABASES = {
    "default": db,
}

# Upload user directory

# https://docs.djangoproject.com/en/1.11/ref/settings/#std:setting-MEDIA_ROOT
MEDIA_ROOT = private_conf.get("media_root")
