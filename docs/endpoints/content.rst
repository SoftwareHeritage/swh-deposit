Display content
^^^^^^^^^^^^^^^^

.. http:get:: /1/<collection-name>/<deposit-id>/content/

    Display information on the content's representation in the sword
    server.


    Also known as: CONT-FILE-IRI

    :param text <name><pass>: the client's credentials
    :statuscode 200: no error
    :statuscode 401: Unauthorized
