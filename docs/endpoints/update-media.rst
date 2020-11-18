Update content
^^^^^^^^^^^^^^^

.. http:post:: /1/(str:collection-name)/(int:deposit-id)/media/

    Add archive(s) to a deposit. Only possible if the deposit's status
    is partial.

.. http:put:: /1/(str:collection-name)/(int:deposit-id)/media/

    Replace all content by submitting a new archive. Only possible if
    the deposit's status is partial.


    Also known as: *update iri* (EM-IRI)

    :reqheader Authorization: Basic authentication token
    :reqheader Content-Type: accepted mimetype
    :reqheader Content-Length: tarball size
    :reqheader Content-MD5: md5 checksum hex encoded of the tarball
    :reqheader Content-Disposition: attachment; filename=[filename] ; the filename
      parameter must be text (ascii)
    :reqheader In-progress: `true` if not final; `false` when final request.
    :statuscode 204: success without payload on PUT
    :statuscode 201: success for deposit on POST
    :statuscode 401: Unauthorized
    :statuscode 415: unsupported media type
