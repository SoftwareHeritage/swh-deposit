Update metadata
^^^^^^^^^^^^^^^^

.. http:post:: /1/(str:collection-name)/(int:deposit-id)/metadata/

    Add metadata to a deposit. Only possible if the deposit's status
    is partial.

.. http:put:: /1/(str:collection-name)/(int:deposit-id)/metadata/

    Replace all metadata by submitting a new metadata file. Only possible if
    the deposit's status is partial.


    Also known as: *update iri* (SE-IRI)

    :reqheader Authorization: Basic authentication token
    :reqheader Content-Disposition: attachment; filename=[filename] ; the filename
      parameter must be text (ascii), with a name parameter set to 'atom'.
    :reqheader In-progress: `true` if not final; `false` when final request.
    :statuscode 204: success without payload on PUT
    :statuscode 201: success for deposit on POST
    :statuscode 401: Unauthorized
    :statuscode 415: unsupported media type
