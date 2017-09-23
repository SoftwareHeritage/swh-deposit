# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.http import HttpResponse
from rest_framework import status

from .common import SWHBaseDeposit
from ..config import CONT_FILE_IRI, EDIT_SE_IRI, EM_IRI
from ..errors import make_error_response, BAD_REQUEST
from ..errors import make_error_response_from_dict
from ..parsers import SWHFileUploadParser, SWHAtomEntryParser
from ..parsers import SWHMultiPartParser


class SWHUpdateArchiveDeposit(SWHBaseDeposit):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'EM IRI' in the sword specification.

    HTTP verbs supported: PUT

    """
    parser_classes = (SWHFileUploadParser, )

    def process_put(self, req, headers, client_name, deposit_id, format=None):
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

        return self._binary_upload(req, headers, client_name,
                                   deposit_id=deposit_id,
                                   replace_archives=True)

    def process_post(self, req, headers, client_name, deposit_id, format=None):
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
                self._binary_upload(req, headers, client_name, deposit_id))

    def delete(self, req, client_name, deposit_id):
        """Delete content (archives) from existing deposit.

        source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
        #protocoloperations_deletingcontent

        Returns:
            204 Created

        """
        data = self._delete_archives(client_name, deposit_id)

        error = data.get('error')
        if error:
            return make_error_response_from_dict(req, error)

        return HttpResponse(status=status.HTTP_204_NO_CONTENT)


class SWHUpdateMetadataDeposit(SWHBaseDeposit):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'Edit IRI' (and SE IRI) in the sword specification.

    HTTP verbs supported: POST (SE IRI), PUT (Edit IRI)

    """
    parser_classes = (SWHMultiPartParser, SWHAtomEntryParser)

    def process_put(self, req, headers, client_name, deposit_id, format=None):
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
            return self._multipart_upload(req, headers, client_name,
                                          deposit_id=deposit_id,
                                          replace_archives=True,
                                          replace_metadata=True)
        return self._atom_entry(req, headers, client_name,
                                deposit_id=deposit_id, replace_metadata=True)

    def process_post(self, req, headers, client_name, deposit_id, format=None):
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
                    self._multipart_upload(req, headers, client_name,
                                           deposit_id=deposit_id))
        # check for final empty post
        # source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
        # #continueddeposit_complete
        if headers['content-length'] == 0 and headers['in-progress'] is False:
            return (status.HTTP_200_OK, EDIT_SE_IRI,
                    self._empty_post(req, headers, client_name, deposit_id))

        return (status.HTTP_201_CREATED, EM_IRI,
                self._atom_entry(req, headers, client_name,
                                 deposit_id=deposit_id))
