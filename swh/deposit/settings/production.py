# Copyright (C) 2017-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os

import django

from swh.core import config
from swh.deposit.settings.common import *  # noqa
from swh.deposit.settings.common import ALLOWED_HOSTS, CACHES

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
        "Production: SWH_CONFIG_FILENAME must be set to the configuration file needed!"
    )

if not os.path.exists(config_file):
    raise ValueError(
        f"Production: configuration file {config_file} does not exist!",
    )

conf = config.load_named_config(config_file)
if not conf:
    raise ValueError(f"Production: configuration {config_file} does not exist.")

for key in ("scheduler", "private", "authentication_provider"):
    if not conf.get(key):
        raise ValueError(
            f"Production: invalid configuration; missing {key} config entry."
        )

ALLOWED_HOSTS += conf.get("allowed_hosts", [])

private_conf = conf["private"]
SECRET_KEY = private_conf["secret_key"]

# Deactivate logging configuration as our uwsgi application is configured to do it
# https://docs.djangoproject.com/en/2.2/ref/settings/#logging-config
LOGGING_CONFIG = None

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

# Default authentication is http basic
authentication = conf["authentication_provider"]

# With the following, we delegate the authentication mechanism to keycloak
if authentication == "keycloak":
    # Optional cache server
    server_cache = conf.get("cache_uri")
    if server_cache:
        cache_backend = "django.core.cache.backends.memcached.MemcachedCache"
        if django.VERSION[:2] >= (3, 2):
            cache_backend = "django.core.cache.backends.memcached.PyMemcacheCache"
        CACHES.update(
            {
                "default": {
                    "BACKEND": cache_backend,
                    "LOCATION": server_cache,
                }
            }
        )

# Optional azure backend to use
cfg_azure = conf.get("azure", {})
if cfg_azure:
    # Those 3 keys are mandatory
    for key in ("container_name", "connection_string"):
        if not cfg_azure.get(key):
            raise ValueError(
                f"Production: invalid configuration; missing {key} config entry."
            )

    # Default options
    options = dict(
        azure_container=cfg_azure["container_name"],
        connection_string=cfg_azure["connection_string"],
        timeout=cfg_azure.get("connection_timeout", 120),
    )

    # Which may be enhanced with some extra options, lookup "object_parameters" in
    # https://django-storages.readthedocs.io/en/latest/backends/azure.html
    object_parameters = {}
    for optional_config_key in ["content_type", "content_disposition"]:
        if optional_config_key in cfg_azure:
            value = cfg_azure[optional_config_key]
            # Explicit "" as None instead of empty string which is not interpreted
            # correctly
            object_parameters[optional_config_key] = None if not value else value

    options.update(dict(object_parameters=object_parameters))

    STORAGES = {
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
        "default": {
            "BACKEND": "storages.backends.azure_storage.AzureStorage",
            "OPTIONS": options,
        },
    }
