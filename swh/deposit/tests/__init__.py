# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.deposit.config import setup_django_for
from swh.deposit.config import SWHDefaultConfig  # noqa

from swh.loader.core.loader import BufferedLoader


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


TEST_LOADER_CONFIG = {
    'extraction_dir': '/tmp/swh-loader-tar/test/',
    'working_dir': '/tmp/swh-loader-tar/test/working-dir',
    'debug': False,
    'storage': {
        'cls': 'memory',
        'args': {
        }
    },
    'send_contents': True,
    'send_directories': True,
    'send_revisions': True,
    'send_releases': True,
    'send_snapshot': True,

    'content_size_limit': 100 * 1024 * 1024,
    'content_packet_size': 10,
    'content_packet_size_bytes': 100 * 1024 * 1024,
    'directory_packet_size': 10,
    'revision_packet_size': 10,
    'release_packet_size': 10,
}


def parse_loader_config_file(base_filename=None, config_filename=None,
                             additional_configs=None, global_config=True):
    return TEST_LOADER_CONFIG


# monkey patch classes method permits to override, for tests purposes,
# the default configuration without side-effect, i.e do not load the
# configuration from disk
SWHDefaultConfig.parse_config_file = parse_deposit_config_file
BufferedLoader.parse_config_file = parse_loader_config_file

setup_django_for('testing')
