.. _API-create-deposit:

Create deposit
^^^^^^^^^^^^^^^

.. http:post:: /1/(str:collection-name)/

    Create deposit in a collection which name is `collection-name`.

    The client sends a deposit request to a specific collection with:

    * an archive holding the software source code (binary upload)
    * an envelop with metadata describing information regarding a deposit (atom
      entry deposit)

      Also known as: COL-IRI

    **Example query**:

    .. code:: shell

       curl -i -u hal:<pass> \
            -F "file=@deposit.json;type=application/zip;filename=payload" \
            -F "atom=@atom-entry.xml;type=application/atom+xml;charset=UTF-8" \
            -H 'In-Progress: false' \
            -H 'Slug: some-external-id' \
            -XPOST https://deposit.softwareheritage.org/1/hal/

    .. code:: http

       POST /1/hal/ HTTP/1.1
       Host: deposit.softwareheritage.org
       Authorization: Basic xxxxxxxxxxxx=
       Slug: some-external-id
       In-Progress: false
       Content-Length: 123456
       Content-Type: multipart/form-data; boundary=----------------------123456798

    **Example response**:

    .. code:: http

       HTTP/1.1 201 Created
       Date: Tue, 26 Sep 2017 10:32:35 GMT
       Server: WSGIServer/0.2 CPython/3.5.3
       Vary: Accept, Cookie
       Allow: GET, POST, PUT, DELETE, HEAD, OPTIONS
       Location: /1/hal/10/metadata/
       X-Frame-Options: SAMEORIGIN
       Content-Type: application/xml

       <entry xmlns="http://www.w3.org/2005/Atom"
              xmlns:sword="http://purl.org/net/sword/"
              xmlns:dcterms="http://purl.org/dc/terms/">
           <deposit_id>10</deposit_id>
           <deposit_date>Sept. 26, 2017, 10:32 a.m.</deposit_date>
           <deposit_archive>None</deposit_archive>
           <deposit_status>deposited</deposit_status>

           <!-- Edit-IRI -->
           <link rel="edit" href="/1/hal/10/metadata/" />
           <!-- EM-IRI -->
           <link rel="edit-media" href="/1/hal/10/media/"/>
           <!-- SE-IRI -->
           <link rel="http://purl.org/net/sword/terms/add" href="/1/hal/10/metadata/" />
           <!-- State-IRI -->
           <link rel="alternate" href="/1/hal/10/status/"/>

           <sword:packaging>http://purl.org/net/sword/package/SimpleZip</sword:packaging>
       </entry>

    :reqheader Authorization: Basic authentication token
    :reqheader Content-Type: accepted mimetype
    :reqheader Content-Length: tarball size
    :reqheader Content-MD5: md5 checksum hex encoded of the tarball
    :reqheader Content-Disposition: attachment; filename=[filename]; the filename
      parameter must be text (ascii); for the metadata file set name parameter
      to 'atom'.
    :reqheader In-progress: `true` if not final; `false` when final request.
    :statuscode 201: success for deposit on POST
    :statuscode 401: Unauthorized
    :statuscode 404: access to an unknown collection
    :statuscode 415: unsupported media type
