# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json

from swh.deposit.client import PrivateApiDepositClient


CLIENT_TEST_CONFIG = {
    'url': 'http://nowhere:9000/',
    'auth': {},  # no authentication in test scenario
}


class SWHDepositTestClient(PrivateApiDepositClient):
    """Deposit test client to permit overriding the default request
       client.

    """
    def __init__(self, client, config):
        super().__init__(config=config)
        self.client = client

    def archive_get(self, archive_update_url, archive_path, log=None):
        r = self.client.get(archive_update_url)
        with open(archive_path, 'wb') as f:
            for chunk in r.streaming_content:
                f.write(chunk)

        return archive_path

    def metadata_get(self, metadata_url, log=None):
        r = self.client.get(metadata_url)
        return json.loads(r.content.decode('utf-8'))

    def status_update(self, update_status_url, status,
                      revision_id=None, directory_id=None, origin_url=None):
        payload = {'status': status}
        if revision_id:
            payload['revision_id'] = revision_id
        if directory_id:
            payload['directory_id'] = directory_id
        if origin_url:
            payload['origin_url'] = origin_url
        self.client.put(update_status_url,
                        content_type='application/json',
                        data=json.dumps(payload))

    def check(self, check_url):
        r = self.client.get(check_url)
        data = json.loads(r.content.decode('utf-8'))
        return data['status']
