# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from ..config import SWHDefaultConfig
from .common import SWHAPIView


class SWHUpdateArchiveDeposit(SWHDefaultConfig, SWHAPIView):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'EM IRI' in the sword specification.

    HTTP verbs supported: PUT

    """
    def put(self, req, client_name, deposit_id, format=None):
        pass


class SWHUpdateMetadataDeposit(SWHDefaultConfig, SWHAPIView):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'Edit IRI' (and SE IRI) in the sword specification.

    HTTP verbs supported: POST (SE IRI), PUT (Edit IRI)

    """
    def post(self, req, client_name, deposit_id, format=None):
        pass

    def put(self, req, client_name, deposit_id, format=None):
        pass
