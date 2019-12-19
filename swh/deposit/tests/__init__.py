# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.deposit.config import setup_django_for
from swh.deposit.config import SWHDefaultConfig  # noqa


TEST_CONFIG = {
    'max_upload_size': 500,
    'extraction_dir': '/tmp/swh-deposit/test/extraction-dir',
    'checks': False,
    'provider': {
        'provider_name': '',
        'provider_type': 'deposit_client',
        'provider_url': '',
        'metadata': {
        }
    },
    'tool': {
        'name': 'swh-deposit',
        'version': '0.0.1',
        'configuration': {
            'sword_version': '2'
        }
    }
}


def parse_deposit_config_file(base_filename=None, config_filename=None,
                              additional_configs=None, global_config=True):
    return TEST_CONFIG


# monkey patch classes method permits to override, for tests purposes,
# the default configuration without side-effect, i.e do not load the
# configuration from disk
SWHDefaultConfig.parse_config_file = parse_deposit_config_file  # type: ignore


setup_django_for('testing')
