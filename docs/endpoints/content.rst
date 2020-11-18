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

           <sword:request>

               <deposit_date>Oct. 28, 2020, 3:58 p.m.</deposit_date>
           </sword:request>
           <sword:request>

               <metadata>
                   <id>test-01243065</id>
                   <title>Verifiable online voting system</title>
                   <author>{&#39;name&#39;: &#39;Belenios&#39;, &#39;email&#39;: &#39;belenios@example.com&#39;}</author>
                   <client>test</client>
                   <codemeta:url>https://gitlab.inria.fr/belenios/belenios</codemeta:url>
                   <codemeta:author>{&#39;codemeta:name&#39;: &#39;Belenios Test User&#39;}</codemeta:author>
                   <codemeta:license>{&#39;codemeta:name&#39;: &#39;GNU Affero General Public License&#39;}</codemeta:license>
                   <codemeta:version>1.12</codemeta:version>
                   <codemeta:keywords>Online voting</codemeta:keywords>
                   <external_identifier>test-01243065</external_identifier>
                   <codemeta:description>Verifiable online voting system</codemeta:description>
                   <codemeta:runtimePlatform>opam</codemeta:runtimePlatform>
                   <codemeta:developmentStatus>stable</codemeta:developmentStatus>
                   <codemeta:applicationCategory>test</codemeta:applicationCategory>
                   <codemeta:programmingLanguage>ocaml</codemeta:programmingLanguage>
                   </metadata>

               <deposit_date>Oct. 28, 2020, 3:58 p.m.</deposit_date>
           </sword:request>
       </entry>


    :reqheader Authorization: Basic authentication token
    :statuscode 200: no error
    :statuscode 401: Unauthorized
