# API Specification

This is Software Heritage's SWORD Server implementation.

SWORD (Simple Web-Service Offering Repository Deposit) is an
interoperability standard for digital file deposit.

This protocol will be used to interact between a client (a repository)
and a server (swh repository) to permit deposits of software archives.

In this document, we will discuss the interaction between a client
(e.g. HAL server) and the deposit server (SWH's).

## Use cases

### First deposit

From client's deposit repository server to SWH's repository server
(aka deposit).

1. The client requests for the server's abilities.
(GET query to the *service document uri*)

2. The server answers the client with the service document which gives
   the *collection uri*.

3. The client sends a deposit (an archive -> .zip) through the
*collection uri* (also known as COL/collection IRI).

This can be done in:
- one POST request to the creation uri (metadata + archive).
- one POST request to the creation uri (metadata or archive) + other
  PUT or POST request to the *update uri*

4. The server notifies the client it acknowledged the client's
request. An 'http 201 Created' response with a deposit receipt is sent
back.  That deposit receipt will hold the necessary information to
eventually complete the deposit if it was partial.

### Updating an existing deposit

5. Client updates existing deposit through the *update uris* (one or
more POST or PUT requests to the *edit-media* or *edit-iri*).

This would be the case for example if the client initially posted a
partial deposit (e.g. only metadata with no archive, or an archive
without metadata, a splitted archive because the initial one is too
big)

### Deleting

6. Deposit deletion is possible as long as the deposit is still in
   partial state.

That is, a deposit initially occurred with the IN-PROGRESS header to
true and it did not change (even after multiple updates).


## Limitations

Applying the SWORD protocol procedure will result with voluntary implementation
shortcomings, at least, during the first iteration:

- upload limitation of 20Mib
- only tarballs (.zip) will be accepted
- no mediation (we do not know the other system's users)

## Collection

SWORD defines a 'collection' concept.  The collection refers to a
group of documents to which the deposit uploaded (a.k.a deposit) is
part of.

For example, we will start the collaboration with HAL, thus we define
a HAL collection to which the hal client will deposit new document.

### Client asks for operation status and repository id

A state endpoint is defined in the sword specification to provide such
information.

## Endpoints

The api defines the following endpoints:

- /1/servicedocument/
  *service document iri* (a.k.a SD-IRI)

- /1/<collection-name>/
  *collection iri* (a.k.a COL-IRI)

- /1/<collection-name>/<deposit-id>/media/
  *update iri* (a.k.a EM-IRI)

- /1/<collection-name>/<deposit-id>/metadata/
  *update iri* (a.k.a EDIT-SE-IRI)

- /1/<collection-name>/<deposit-id>/content/
  *content iri* (a.k.a CONT-FILE-IRI)

- /1/<collection-name>/<deposit-id>/status/
  *state iri*  (a.k.a STATE-IRI)

## API overview

API access is over HTTPS.

All API endpoints are rooted at https://archive.softwareheritage.org/1/.

Data is sent and received as XML.

### Service document

Endpoint: /1/servicedocument/

This is the starting endpoint from which the client will access its
initial collection information.

This:
- describes the server's abilities
- list the connected client's collection information.

HTTP verbs supported: GET

Also known as: SD-IRI - The Service Document IRI.

#### Sample request

``` Shell
GET https://deposit.softwareheritage.org/1/servicedocument/ HTTP/1.1
Host: deposit.softwareheritage.org
```

The server returns its abilities with the service document in xml format:
- protocol sword version v2
- accepted mime types: application/zip
- upload max size accepted. Beyond that point, it's expected the
  client splits its tarball into multiple ones
- the collection the client can act upon (swh supports only one
  software collection per client)
- mediation is not supported
- etc...

#### Sample answer

The current answer for example for the
[hal archive](https://hal.archives-ouvertes.fr/) is:

``` XML
<?xml version="1.0" ?>
<service xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:sword="http://purl.org/net/sword/terms/"
    xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns="http://www.w3.org/2007/app">

    <sword:version>2.0</sword:version>
    <sword:maxUploadSize>20971520</sword:maxUploadSize>
    <sword:verbose>False</sword:verbose>
    <sword:noOp>False</sword:noOp>

    <workspace>
        <atom:title>The Software Heritage (SWH) archive</atom:title>
        <collection href="https://deposit.softwareherigage.org/1/hal/">
            <atom:title>SWH Software Archive</atom:title>
            <accept>application/zip</accept>
            <sword:collectionPolicy>Collection Policy</sword:collectionPolicy>
            <dcterms:abstract>Software Heritage Archive</dcterms:abstract>
            <sword:mediation>false</sword:mediation>
            <sword:treatment>Collect, Preserve, Share</sword:treatment>
            <sword:acceptPackaging>http://purl.org/net/sword/package/SimpleZip</sword:acceptPackaging>
            <sword:service>https://deposit.softwareheritage.org/1/hal/</sword:service>
        </collection>
    </workspace>
</service>
```

## Deposit Creation: client point of view

Process of deposit creation:

-> [3] client request(s)

  - [3.1] server validation
  - [3.2] server temporary upload

<- [4] server returns deposit receipt id

- [5] server injects deposit into archive*

NOTE: [5] Asynchronously, the server will inject the archive uploaded
and the associated metadata.

The image below represents only the communication and creation of a
deposit:

{F2403754}

### [3] client request(s)

The client can send a deposit through a series of deposit requests to
multiple endpoints:
- *collection iri* (COL-IRI) to initialize a deposit
- *update iris* (EM-IRI, EDIT-SE-IRI) to complete/finalize a deposit

The deposit can also happens in one request.

The deposit request can contain:
- an archive holding the software source code (binary upload)
- an envelop with metadata describing information regarding a deposit
  (atom entry deposit)
- or both (multipart deposit, exactly one archive and one envelop).

## Request Types

### Binary deposit

The client can deposit a binary archive, supplying the following headers:
- Content-Type (text): accepted mimetype
- Content-Length (int): tarball size
- Content-MD5 (text): md5 checksum hex encoded of the tarball
- Content-Disposition (text): attachment; filename=[filename] ; the filename
  parameter must be text (ascii)
- Packaging (IRI): http://purl.org/net/sword/package/SimpleZip
- In-Progress (bool): true to specify it's not the last request, false
  to specify it's a final request and the server can go on with
  processing the request's information (if not provided, this is
  considered false, so final).

This is a single zip archive deposit. Almost no metadata is associated
with the archive except for the unique external identifier.

Note: This kind of deposit should be partial (In-Progress: True) as
almost no metadata can be associated with the uploaded archive.

#### API endpoints concerned

POST /1/<collection-name>/                    Create a first deposit with one archive
PUT /1/<collection-name>/<deposit-id>/media/  Replace existing archives
POST /1/<collection-name>/<deposit-id>/media/ Add new archive

#### Sample request

``` Shell
curl -i -u hal:<pass> \
    --data-binary @swh/deposit.zip \
    -H 'In-Progress: false' -H 'Content-MD5: 0faa1ecbf9224b9bf48a7c691b8c2b6f' \
    -H 'Content-Disposition: attachment; filename=[deposit.zip]' \
    -H 'Slug: some-external-id' \
    -H 'Packaging: http://purl.org/net/sword/package/SimpleZIP' \
    -H 'Content-type: application/zip' \
    -XPOST https://deposit.softwareheritage.org/1/hal/
```

### Atom entry deposit

The client can deposit an xml body holding metadata information on the
deposit.

Note: This kind of deposit is mostly expected to be partial
(In-Progress: True) since no archive will be associated to those
metadata.

#### API endpoints concerned

POST /1/<collection-name>/                       Create a first atom deposit entry
PUT /1/<collection-name>/<deposit-id>/metadata/  Replace existing metadata
POST /1/<collection-name>/<deposit-id>/metadata/ Add new metadata to deposit

#### Sample request

Sample query:

``` Shell
curl -i -u hal:<pass> --data-binary @atom-entry.xml \
-H 'In-Progress: false' \
-H 'Slug: some-external-id' \
-H 'Content-Type: application/atom+xml;type=entry' \
-XPOST http://127.0.0.1:5006/1/hal/
HTTP/1.0 201 Created
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

    <!-- Edit-IRI -->
    <link rel="edit" href="/1/hal/10/metadata/" />
    <!-- EM-IRI -->
    <link rel="edit-media" href="/1/hal/10/media/"/>
    <!-- SE-IRI -->
    <link rel="http://purl.org/net/sword/terms/add" href="/1/hal/10/metadata/" />

    <sword:packaging>http://purl.org/net/sword/package/SimpleZip</sword:packaging>
</entry>
```

Sample body:

``` XML
<entry xmlns="http://www.w3.org/2005/Atom"
        xmlns:dcterms="http://purl.org/dc/terms/">
    <title>Title</title>
    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
    <updated>2005-10-07T17:17:08Z</updated>
    <author><name>Contributor</name></author>
    <summary type="text">The abstract</summary>

    <!-- some embedded metadata -->
    <dcterms:abstract>The abstract</dcterms:abstract>
    <dcterms:accessRights>Access Rights</dcterms:accessRights>
    <dcterms:alternative>Alternative Title</dcterms:alternative>
    <dcterms:available>Date Available</dcterms:available>
    <dcterms:bibliographicCitation>Bibliographic Citation</dcterms:bibliographicCitation>  # noqa
    <dcterms:contributor>Contributor</dcterms:contributor>
    <dcterms:description>Description</dcterms:description>
    <dcterms:hasPart>Has Part</dcterms:hasPart>
    <dcterms:hasVersion>Has Version</dcterms:hasVersion>
    <dcterms:identifier>Identifier</dcterms:identifier>
    <dcterms:isPartOf>Is Part Of</dcterms:isPartOf>
    <dcterms:publisher>Publisher</dcterms:publisher>
    <dcterms:references>References</dcterms:references>
    <dcterms:rightsHolder>Rights Holder</dcterms:rightsHolder>
    <dcterms:source>Source</dcterms:source>
    <dcterms:title>Title</dcterms:title>
    <dcterms:type>Type</dcterms:type>

</entry>
```

### One request deposit / Multipart deposit

The one request deposit is a single request containing both the
metadata (as atom entry attachment) and the archive (as payload
attachment). Thus, it is a multipart deposit.

Client provides:
- Content-Disposition (text): header of type 'attachment' on the Entry
  Part with a name parameter set to 'atom'
- Content-Disposition (text): header of type 'attachment' on the Media
  Part with a name parameter set to payload and a filename parameter
  (the filename will be expressed in ASCII).
- Content-MD5 (text): md5 checksum hex encoded of the tarball
- Packaging (text): http://purl.org/net/sword/package/SimpleZip
  (packaging format used on the Media Part)
- In-Progress (bool): true|false; true means partial upload and we can expect
  other requests in the future, false means the deposit is done.
- add metadata formats or foreign markup to the atom:entry element

#### API endpoints concerned

POST /1/<collection-name>/                       Create a full deposit (metadata + archive)
PUT /1/<collection-name>/<deposit-id>/metadata/  Replace existing metadata and archive
POST /1/<collection-name>/<deposit-id>/metadata/ Add new metadata and archive to deposit

#### Sample request

Sample query:

``` Shell
curl -i -u hal:<pass> \
    -F "file=@../deposit.json;type=application/zip;filename=payload" \
    -F "atom=@../atom-entry.xml;type=application/atom+xml;charset=UTF-8" \
    -H 'In-Progress: false' \
    -H 'Slug: some-external-id' \
    -XPOST http://127.0.0.1:5006/1/hal/

HTTP/1.0 201 Created
Date: Tue, 26 Sep 2017 10:11:55 GMT
Server: WSGIServer/0.2 CPython/3.5.3
Vary: Accept, Cookie
Allow: GET, POST, PUT, DELETE, HEAD, OPTIONS
Location: /1/hal/9/metadata/
X-Frame-Options: SAMEORIGIN
Content-Type: application/xml

<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:sword="http://purl.org/net/sword/"
       xmlns:dcterms="http://purl.org/dc/terms/">
    <deposit_id>9</deposit_id>
    <deposit_date>Sept. 26, 2017, 10:11 a.m.</deposit_date>
    <deposit_archive>payload</deposit_archive>

    <!-- Edit-IRI -->
    <link rel="edit" href="/1/hal/9/metadata/" />
    <!-- EM-IRI -->
    <link rel="edit-media" href="/1/hal/9/media/"/>
    <!-- SE-IRI -->
    <link rel="http://purl.org/net/sword/terms/add" href="/1/hal/9/metadata/" />

    <sword:packaging>http://purl.org/net/sword/package/SimpleZip</sword:packaging>
</entry>
```

Sample content:

``` XML
POST deposit HTTP/1.1
Host: deposit.softwareheritage.org
Content-Length: [content length]
Content-Type: multipart/related;
            boundary="===============1605871705==";
            type="application/atom+xml"
In-Progress: false
MIME-Version: 1.0

Media Post
--===============1605871705==
Content-Type: application/atom+xml; charset="utf-8"
Content-Disposition: attachment; name="atom"
MIME-Version: 1.0

<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom"
        xmlns:dcterms="http://purl.org/dc/terms/">
    <title>Title</title>
    <id>hal-or-other-archive-id</id>
    <updated>2005-10-07T17:17:08Z</updated>
    <author><name>Contributor</name></author>

    <!-- some embedded metadata ... -->
    <dcterms:abstract>The abstract</dcterms:abstract>
    <dcterms:accessRights>Access Rights</dcterms:accessRights>
    <dcterms:alternative>Alternative Title</dcterms:alternative>
    <dcterms:available>Date Available</dcterms:available>
    <dcterms:bibliographicCitation>Bibliographic Citation</dcterms:bibliographicCitation>  # noqa
    <dcterms:contributor>Contributor</dcterms:contributor>
    <dcterms:description>Description</dcterms:description>
    <dcterms:hasPart>Has Part</dcterms:hasPart>
    <dcterms:hasVersion>Has Version</dcterms:hasVersion>
    <dcterms:identifier>Identifier</dcterms:identifier>
    <dcterms:isPartOf>Is Part Of</dcterms:isPartOf>
    <dcterms:publisher>Publisher</dcterms:publisher>
    <dcterms:references>References</dcterms:references>
    <dcterms:rightsHolder>Rights Holder</dcterms:rightsHolder>
    <dcterms:source>Source</dcterms:source>
    <dcterms:title>Title</dcterms:title>
    <dcterms:type>Type</dcterms:type>
</entry>
--===============1605871705==
Content-Type: application/zip
Content-Disposition: attachment; name=payload; filename=[filename]
Packaging: http://purl.org/net/sword/package/SimpleZip
Content-MD5: [md5-digest]
MIME-Version: 1.0

[...binary package data...]
--===============1605871705==--
```

## Deposit Creation - server point of view

The server receives the request(s) and does minimal checking on the
input prior to any saving operations.

### [3.1] Validation of the header and body request

Any kind of errors can happen, here is the list depending on the
situation:

- common errors:
  - 401 (unauthenticated) if a client does not provide credential or
    provide wrong ones
  - 403 (forbidden) if a client tries access to a collection it does
    not own
  - 404 (not found) if a client tries access to an unknown collection
  - 404 (not found) if a client tries access to an unknown deposit
  - 415 (unsupported media type) if a wrong media type is
    provided to the endpoint

- archive/binary deposit:
  - 403 (forbidden) if the length of the archive exceeds the
    max size configured
  - 412 (precondition failed) if the length or hash provided
    mismatch the reality of the archive.
  - 415 (unsupported media type) if a wrong media type is
    provided

- multipart deposit:
  - 412 (precondition failed) if the md5 hash provided mismatch the
    reality of the archive
  - 415 (unsupported media type) if a wrong media type is
    provided

- Atom entry deposit:
  - 400 (bad request) if the request's body is empty (for creation only)

### [3.2] Server uploads the content in a temporary location

Using an objstorage, the server stores the archive in a temporary
location.  It's temporary the time the deposit is completed (status
becomes ready) and the injection finishes.

The server also stores requests' information in a database.

### [4] Servers answers the client

If everything went well, the server answers either with a 200, 201 or
204 response.

A 'http 200' response is returned for GET endpoints.

A 'http 201 Created' response is returned for POST endpoints.
The body holds the deposit receipt.
The headers holds the EDIT-IRI in the Location header of the response.

A 'http 204 No Content' response is returned for PUT, DELETE endpoints.

If something went wrong, the server answers with one of the
[error status code and associated message mentioned](#possible errors)).


### [5] Deposit Update

The client previously deposited a partial document (through an
archive, metadata, or both). The client wants to update information
for that previous deposit (possibly in multiple steps as well).

The important thing to note here is that, as long as the deposit is in
status 'partial', the injection did not start.  Thus, the client can
update information (replace or add new archive, new metadata, even
delete) for that same partial deposit.

When the deposit status changes to `ready`, we no longer can change
the deposit's information (a 403 will be returned in that case).

Then aggregation of all those deposit's information will later be used
for the actual injection.

Providing the collection name, and the identifier of the previous
deposit id received from the deposit receipt, the client executes a
POST or PUT request on the *update iris*.

After validation of the body request, the server:
- uploads such content in a temporary location

- answers the client an 'http 204 (No content)'. In the Location
  header of the response lies an iri to permit further update.

- Asynchronously, the server will inject the archive uploaded and the
  associated metadata. An operation status endpoint *state iri*
  permits the client to query the injection operation status.

Possible endpoints:

PUT /1/<collection-name>/<deposit-id>/media/      Replace existing archives for the deposit
POST /1/<collection-name>/<deposit-id>/media/     Add new archives to the deposit
PUT /1/<collection-name>/<deposit-id>/metadata/   Replace existing metadata (and possible archives)
POST /1/<collection-name>/<deposit-id>/metadata/  Add new metadata

### [6] Deposit Removal

As long as the deposit's status remains 'partial', it's possible to
remove the deposit.

Further query to that deposit will return a 404 response.

### Operation Status

Providing a collection name and a deposit id, the client asks the
operation status of a prior deposit.

URL: GET /1/<collection-name>/<deposit_id>/status/

This returns:
- 201 response with the actual status
- 404 if the deposit does not exist (or no longer does)

## <a name="errors"> Possible errors

### sword:ErrorContent

IRI: http://purl.org/net/sword/error/ErrorContent

The supplied format is not the same as that identified in the
Packaging header and/or that supported by the server Associated HTTP

Status: 415 (Unsupported Media Type) or 406 (Not Acceptable)

### sword:ErrorChecksumMismatch

IRI: http://purl.org/net/sword/error/ErrorChecksumMismatch

Checksum sent does not match the calculated checksum. The server MUST
also return a status code of 412 Precondition Failed

### sword:ErrorBadRequest

IRI: http://purl.org/net/sword/error/ErrorBadRequest

Some parameters sent with the POST/PUT were not understood. The server
MUST also return a status code of 400 Bad Request.

### sword:MediationNotAllowed

IRI: http://purl.org/net/sword/error/MediationNotAllowed

Used where a client has attempted a mediated deposit, but this is not
supported by the server. The server MUST also return a status code of
412 Precondition Failed.

### sword:MethodNotAllowed

IRI: http://purl.org/net/sword/error/MethodNotAllowed

Used when the client has attempted one of the HTTP update verbs (POST,
PUT, DELETE) but the server has decided not to respond to such
requests on the specified resource at that time. The server MUST also
return a status code of 405 Method Not Allowed

### sword:MaxUploadSizeExceeded

IRI: http://purl.org/net/sword/error/MaxUploadSizeExceeded

Used when the client has attempted to supply to the server a file
which exceeds the server's maximum upload size limit

Associated HTTP Status: 413 (Request Entity Too Large)

### sword:Unauthorized

IRI: http://purl.org/net/sword/error/ErrorUnauthorized

The access to the api is through authentication.

Associated HTTP status: 401

### sword:Forbidden

IRI: http://purl.org/net/sword/error/ErrorForbidden

The action is forbidden (access to another collection for example).

Associated HTTP status: 403

## Nomenclature

SWORD uses IRI notion, Internationalized Resource Identifier. In this
chapter, we will describe SWH's IRIs.

### Col-IRI - The Collection IRI

The software collection associated to one user.

The SWORD Collection IRI is the IRI to which the initial deposit will
take place, and which is listed in the Service Document.

Following our previous example, this is:
https://deposit.softwareheritage.org/1/hal/.

HTTP verbs supported: POST

### Cont-IRI - The Content IRI

This is the endpoint which permits the client to retrieve
representations of the object as it resides in the SWORD server.

This will display information about the content and its associated
metadata.

HTTP verbs supported: GET

We refer to it as Cont-File-IRI.

### EM-IRI - The Atom Edit Media IRI

This is the endpoint to upload other related archives for the same
deposit.

It is used to change a 'partial' deposit in regards of archives, in
particular:
- replace existing archives with new ones
- add new archives
- delete archives from a deposit

Example use case:
A first archive to put exceeds the deposit's limit size.
The client can thus split the archives in multiple ones.
Post a first partial archive to the Col-IRI (with In-Progress:

True).  Then, in order to complete the deposit, POST the other
remaining archives to the EM-IRI (the last one with the In-Progress
header to False).

HTTP verbs supported: POST, PUT, DELETE

### Edit-IRI - The Atom Entry Edit IRI

This is the endpoint to change a 'partial' deposit in regards of
metadata. In particular:
- replace existing metadata (and archives) with new ones
- add new metadata (and archives)
- delete deposit

HTTP verbs supported: POST, PUT, DELETE

### SE-IRI - The SWORD Edit IRI

The sword specification permits to merge this with EDIT-IRI, so we
did.

### State-IRI - The SWORD Statement IRI

This is the IRI which can be used to retrieve a description of the
object from the sword server, including the structure of the object
and its state. This will be used as the operation status endpoint.

HTTP verbs supported: GET

## Sources

- [SWORD v2 specification](http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html)
- [arxiv documentation](https://arxiv.org/help/submit_sword)
- [Dataverse example](http://guides.dataverse.org/en/4.3/api/sword.html)
- [SWORD used on HAL](https://api.archives-ouvertes.fr/docs/sword)
- [xml examples for CCSD](https://github.com/CCSDForge/HAL/tree/master/Sword)
