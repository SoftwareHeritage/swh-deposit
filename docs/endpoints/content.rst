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
              xmlns:dcterms="http://purl.org/dc/terms/">
           <deposit_id>1</deposit_id>
           <deposit_status>done</deposit_status>
           <deposit_status_detail>The deposit has been successfully loaded into the Software Heritage archive</deposit_status_detail>
           <deposit_date>Oct. 28, 2020, 3:58 p.m.</deposit_date>
       </entry>


    :reqheader Authorization: Basic authentication token
    :statuscode 200: no error
    :statuscode 401: Unauthorized
