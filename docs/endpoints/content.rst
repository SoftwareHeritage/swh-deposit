Display content
^^^^^^^^^^^^^^^^

.. http:get:: /1/(str:collection-name)/(int:deposit-id)/content/

    Display information on the content's representation in the sword
    server.


    Also known as: CONT-FILE-IRI

    **Example query**:

    .. code:: http

       GET /deposit/1/test/1/content/ HTTP/1.1
       Accept: */*
       Accept-Encoding: gzip, deflate
       Authorization: Basic xxxxxxxxxx
       Connection: keep-alive
       Host: deposit.softwareheritage.org

    **Example response**:

    .. code:: http

       HTTP/1.1 200 OK
       Allow: GET, POST, PUT, DELETE, HEAD, OPTIONS
       Connection: keep-alive
       Content-Length: 1760
       Content-Type: application/xml
       Date: Thu, 05 Nov 2020 14:31:50 GMT
       Server: nginx/1.19.2
       Vary: Accept
       X-Frame-Options: SAMEORIGIN

       <entry xmlns="http://www.w3.org/2005/Atom"
              xmlns:sword="http://purl.org/net/sword/"
              xmlns:dcterms="http://purl.org/dc/terms/"
              xmlns:swhdeposit="https://www.softwareheritage.org/schema/2018/deposit"
              >
           <swhdeposit:deposit_id>1</swhdeposit:deposit_id>
           <swhdeposit:deposit_date>Oct. 28, 2020, 3:58 p.m.</swhdeposit:deposit_date>
           <swhdeposit:deposit_status>done</swhdeposit:deposit_status>
           <swhdeposit:deposit_status_detail>The deposit has been successfully loaded into the Software Heritage archive</swhdeposit:deposit_status_detail>
       </entry>

    Note: older versions of the deposit used the ``http://www.w3.org/2005/Atom``
    namespace instead of ``https://www.softwareheritage.org/schema/2018/deposit``.
    Tags in the Atom namespace are still provided for backward compatibility, but
    are deprecated.


    :reqheader Authorization: Basic authentication token
    :statuscode 200: no error
    :statuscode 401: Unauthorized
