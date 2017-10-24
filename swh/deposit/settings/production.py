# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from .common import *  # noqa
from .common import ALLOWED_HOSTS
from swh.core import config

ALLOWED_HOSTS += ['deposit.softwareheritage.org']
# Setup support for proxy headers
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

DEBUG = False

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
# https://docs.djangoproject.com/en/1.10/ref/settings/#std:setting-DATABASES
# https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/#databases

DEFAULT_PATH = 'deposit/private'

private_conf = config.load_named_config(DEFAULT_PATH)

if not private_conf:
    raise ValueError('Cannot run in production, missing private data file.')

SECRET_KEY = private_conf['secret_key']

# https://docs.djangoproject.com/en/1.10/ref/settings/#logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",  # noqa
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# database

db_conf = private_conf['db']

db = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': db_conf['name'],
}

db_user = db_conf.get('user')
if db_user:
    db['USER'] = db_user


db_pass = db_conf.get('password')
if db_pass:
    db['PASSWORD'] = db_pass

db_host = db_conf.get('host')
if db_host:
    db['HOST'] = db_host

db_port = db_conf.get('port')
if db_port:
    db['PORT'] = db_port

# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
DATABASES = {
    'default': db,
}

# Upload user directory

# https://docs.djangoproject.com/en/1.11/ref/settings/#std:setting-MEDIA_ROOT
MEDIA_ROOT = private_conf['media_root']
