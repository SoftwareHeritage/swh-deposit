# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from rest_framework import status
from rest_framework.parsers import JSONParser

from .common import SWHPostDepositAPI, SWHPutDepositAPI, SWHDeleteDepositAPI
from ..config import CONT_FILE_IRI, EDIT_SE_IRI, EM_IRI
from ..errors import make_error_response, make_error_dict, BAD_REQUEST
from ..models import Deposit, DEPOSIT_STATUS_DETAIL
from ..parsers import SWHFileUploadParser, SWHAtomEntryParser
from ..parsers import SWHMultiPartParser


class SWHUpdateArchiveDeposit(SWHPostDepositAPI, SWHPutDepositAPI,
                              SWHDeleteDepositAPI):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'EM IRI' in the sword specification.

    HTTP verbs supported: PUT, POST, DELETE

    """
    parser_classes = (SWHFileUploadParser, )

    def process_put(self, req, headers, collection_name, deposit_id):
        """Replace existing content for the existing deposit.

        +header: Metadata-relevant (to extract metadata from the archive)

        source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
        #protocoloperations_editingcontent_binary

        Returns:
            204 No content

        """
        if req.content_type != 'application/zip':
            return make_error_response(req, BAD_REQUEST,
                                       'Only application/zip is supported!')

        return self._binary_upload(req, headers, collection_name,
                                   deposit_id=deposit_id,
                                   replace_archives=True)

    def process_post(self, req, headers, collection_name, deposit_id):
        """Add new content to the existing deposit.

        +header: Metadata-relevant (to extract metadata from the archive)

        source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
        #protocoloperations_addingcontent_mediaresource

        Returns:
            201 Created
            Headers: Location: [Cont-File-IRI]

            Body: [optional Deposit Receipt]

        """
        if req.content_type != 'application/zip':
            return make_error_response(req, BAD_REQUEST,
                                       'Only application/zip is supported!')

        return (status.HTTP_201_CREATED, CONT_FILE_IRI,
                self._binary_upload(req, headers, collection_name, deposit_id))

    def process_delete(self, req, collection_name, deposit_id):
        """Delete content (archives) from existing deposit.

        source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
        #protocoloperations_deletingcontent

        Returns:
            204 Created

        """
        return self._delete_archives(collection_name, deposit_id)


class SWHUpdateMetadataDeposit(SWHPostDepositAPI, SWHPutDepositAPI,
                               SWHDeleteDepositAPI):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'Edit IRI' (and SE IRI) in the sword specification.

    HTTP verbs supported: POST (SE IRI), PUT (Edit IRI), DELETE

    """
    parser_classes = (SWHMultiPartParser, SWHAtomEntryParser)

    def process_put(self, req, headers, collection_name, deposit_id):
        """Replace existing deposit's metadata/archive with new ones.

        source:
        - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
          #protocoloperations_editingcontent_metadata
        - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
          #protocoloperations_editingcontent_multipart

        Returns:
            204 No content

        """
        if req.content_type.startswith('multipart/'):
            return self._multipart_upload(req, headers, collection_name,
                                          deposit_id=deposit_id,
                                          replace_archives=True,
                                          replace_metadata=True)
        return self._atom_entry(req, headers, collection_name,
                                deposit_id=deposit_id, replace_metadata=True)

    def process_post(self, req, headers, collection_name, deposit_id):
        """Add new metadata/archive to existing deposit.

        source:
        - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
        #protocoloperations_addingcontent_metadata
        - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
        #protocoloperations_addingcontent_multipart

        This also deals with an empty post corner case to finalize a
        deposit.

        Returns:
            In optimal case for a multipart and atom-entry update, a
            201 Created response. The body response will hold a
            deposit. And the response headers will contain an entry
            'Location' with the EM-IRI.

            For the empty post case, this returns a 200.

        """
        if req.content_type.startswith('multipart/'):
            return (status.HTTP_201_CREATED, EM_IRI,
                    self._multipart_upload(req, headers, collection_name,
                                           deposit_id=deposit_id))
        # check for final empty post
        # source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
        # #continueddeposit_complete
        if headers['content-length'] == 0 and headers['in-progress'] is False:
            data = self._empty_post(req, headers, collection_name, deposit_id)
            return (status.HTTP_200_OK, EDIT_SE_IRI, data)

        return (status.HTTP_201_CREATED, EM_IRI,
                self._atom_entry(req, headers, collection_name,
                                 deposit_id=deposit_id))

    def process_delete(self, req, collection_name, deposit_id):
        """Delete the container (deposit).

        Source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
        #protocoloperations_deleteconteiner
        """
        return self._delete_deposit(collection_name, deposit_id)


class SWHUpdateStatusDeposit(SWHPutDepositAPI):
    """Deposit request class to update the deposit's status.

    HTTP verbs supported: PUT

    """
    parser_classes = (JSONParser, )

    def restrict_access(self, req, deposit=None):
        """Remove restriction modification to 'partial' deposit.
           Update is possible regardless of the existing status.

        """
        return None

    def process_put(self, req, headers, collection_name, deposit_id):
        """Update the deposit's status

        Returns:
            204 No content

        """
        status = req.data.get('status')
        if not status:
            msg = 'The status key is mandatory with possible values %s' % list(
                DEPOSIT_STATUS_DETAIL.keys())
            return make_error_dict(BAD_REQUEST, msg)

        if status not in DEPOSIT_STATUS_DETAIL:
            msg = 'Possible status in %s' % list(DEPOSIT_STATUS_DETAIL.keys())
            return make_error_dict(BAD_REQUEST, msg)

        deposit = Deposit.objects.get(pk=deposit_id)
        deposit.status = status
        deposit.save()

        return {}
