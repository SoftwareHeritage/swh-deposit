Retrieve status
^^^^^^^^^^^^^^^^

.. http:get:: /1/<collection-name>/<deposit-id>/

    Display deposit's status in regards to loading.


    The different statuses:

    - **partial**: multipart deposit is still ongoing
    - **deposited**: deposit completed
    - **rejected**: deposit failed the checks
    - **verified**: content and metadata verified
    - **loading**: loading in-progress
    - **done**: loading completed successfully
    - **failed**: the deposit loading has failed

    Also known as STATE-IRI

    :param text <name><pass>: the client's credentials
    :statuscode 201: with the deposit's status
    :statuscode 401: Unauthorized
    :statuscode 404: access to an unknown deposit



Sample response
~~~~~~~~~~~~~~~
