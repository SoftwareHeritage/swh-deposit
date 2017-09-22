# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from ..parsers import SWHFileUploadParser, SWHAtomEntryParser
from ..parsers import SWHMultiPartParser

from ..errors import make_error, make_error_response, BAD_REQUEST
from .common import SWHBaseDeposit


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
            error = make_error(BAD_REQUEST,
                               'Only application/zip is supported!')
            return make_error_response(req, error['error'])

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
        if req.content_type == 'application/zip':
            return self._binary_upload(req, headers, client_name, deposit_id)
        if req.content_type.startswith('multipart/'):
            return self._multipart_upload(req, headers, client_name,
                                          deposit_id)
        return self._atom_entry(req, headers, client_name)

    def update_post_response(self, response, data):
        response._headers['location'] = 'Location', data['cont_file_iri']
        return response


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

        Returns:
            201 Created
            Location: [EM-IRI]

            [optional Deposit Receipt]

        """
        if req.content_type.startswith('multipart/'):
            return self._multipart_upload(req, headers, client_name,
                                          deposit_id=deposit_id)
        return self._atom_entry(req, headers, client_name,
                                deposit_id=deposit_id)

    def update_post_response(self, response, data):
        response._headers['location'] = 'Location', data['em_iri']
        return response
