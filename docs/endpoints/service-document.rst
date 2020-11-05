Service document
^^^^^^^^^^^^^^^^^

.. http:get:: /1/servicedocument/

    This is the starting endpoint for the client to discover its initial
    collection. The answer to this query will describes:

    * the server's abilities
    * connected client's collection information

    Also known as: SD-IRI - The Service Document IRI

    **Example query**:

    .. code:: http

       GET /1/servicedocument/ HTTP/1.1
       Host: deposit.softwareheritage.org
       Authorization: Basic xxxxxxxxxxxx=

    **Example response**:

    .. code:: http

       HTTP/1.1 200 OK
       Allow: GET, POST, PUT, DELETE, HEAD, OPTIONS
       Connection: keep-alive
       Content-Length: 1247
       Content-Type: application/xml
       Date: Thu, 05 Nov 2020 14:27:05 GMT
       Server: nginx/1.19.2
       Vary: Accept
       X-Frame-Options: SAMEORIGIN

       <?xml version="1.0" ?>
       <service xmlns:dcterms="http://purl.org/dc/terms/"
           xmlns:sword="http://purl.org/net/sword/terms/"
           xmlns:atom="http://www.w3.org/2005/Atom"
           xmlns="http://www.w3.org/2007/app">

           <sword:version>2.0</sword:version>
           <sword:maxUploadSize>20971520</sword:maxUploadSize>

           <workspace>
               <atom:title>The Software Heritage (SWH) archive</atom:title>
               <collection href="https://deposit.softwareherigage.org/1/hal/">
                   <atom:title>SWH Software Archive</atom:title>
                   <accept>application/zip</accept>
                   <accept>application/x-tar</accept>
                   <sword:collectionPolicy>Collection Policy</sword:collectionPolicy>
                   <dcterms:abstract>Software Heritage Archive</dcterms:abstract>
                   <sword:mediation>false</sword:mediation>
                   <sword:metadataRelevantHeader>false</sword:metadataRelevantHeader>
                   <sword:treatment>Collect, Preserve, Share</sword:treatment>
                   <sword:acceptPackaging>http://purl.org/net/sword/package/SimpleZip</sword:acceptPackaging>
                   <sword:service>https://deposit.softwareheritage.org/1/hal/</sword:service>
               </collection>
           </workspace>
       </service>

    :reqheader Authorization: Basic authentication token
    :statuscode 200: no error
    :statuscode 401: Unauthorized
