swh-sword (draft)
=================

SWORD (Simple Web-Service Offering Repository Deposit) is an
interoperability standard for digital file deposit.

This protocol will be used to interact between a client (a repository)
and a server (swh repository) to permit the deposit of software
tarballs.

In this document, we will refer to a client (e.g. HAL server) and a
server (SWH's).

To summarize, the SWORD protocol exchange, from repository to
repository scenario is:

- Discussion with the client and the server to establish the server's
  abilities (GET). The client can ask the server's abilities through a
  GET query to the service document uri. The server answers to the
  client describing but not limited to, the sword version supported
  (v2), the max upload size it expects, a URI list of supported
  endpoints, the collection it can query, etc...

- Client deposits one document version (archive) through the deposit
  creation uri (one or more POST request, in effect chunking the
  artifact to deposit)

- Client updates existing document version (archive) through the
  deposit update uri via (one or more PUT requests, in effect chunking
  the artifact to deposit)

- Client deletes a document through the delete uri via a DELETE
  request (cf. limitation paragraph about this one)

- Client can list collections' documents (let's not?).


Note:

IRI: Internationalized Resource identifier

# API

API access is over HTTPS.
All API endpoints are rooted at https://archive.softwareheritage.org/deposit/.

# Limitation

In the current state, there will be some voluntary shortcomings in the
implementation, notably:

- no removal
- no mediation (we do not know the other system's users)
- upload limitation of 100Mib
- only tarballs (.zip, .tar.gz) will be accepted
- no authentication or a simple one not dealt with at the application
  layer
- SWORD defines a collection notion.  As SWH is a software archive, we
  will define only one collection or none if possible.

# Service Document

This is a step permitting the client to determine the server's abilities.

The server responds its abilities:
- protocol sword version v2
- accepted mime types: application/zip, application/gzip
- upload max size accepted, beyond that, it's expected the client
  chunk the tarball into multiple ones
- the collections the client can act upon (the only collection
  'software')
- mediation not supported

## API

GET /1/servicedocument/

Answer:
- 200, Content-Type: application/atomserv+xml: OK, with the body
  described below

## Sample

``` shell
GET https://archive.softwareheritage.org/1/servicedocument HTTP/1.1
Host: archive.softwareheritage.org
```

Server answers:

``` xml
<?xml version="1.0" ?>
<service xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:sword="http://purl.org/net/sword/terms/"
    xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns="http://www.w3.org/2007/app">

    <sword:version>2.0</sword:version>
    <sword:maxUploadSize>${max_upload_size}</sword:maxUploadSize>
    <!-- <sword:verbose>true</sword:verbose> -->
    <!-- <sword:noOp>true</sword:noOp> -->

    <workspace>
        <atom:title>The SWH archive</atom:title>

        <collection href="https://archive.softwareherigage.org/1/deposit/">
            <atom:title>SWH Collection</atom:title>
            <accept>application/gzip</accept>
            <accept alternate="multipart-related">application/gzip</accept>
            <dcterms:abstract>Software Heritage Archive</dcterms:abstract>
            <sword:mediation>false</sword:mediation>
            <sword:acceptPackaging>http://purl.org/net/sword/package/SimpleZip</sword:acceptPackaging>
        </collection>
    </workspace>
</service>
```

# Deposit Creation

The client posts (in possibly multiple requests):
- only an archive holding the software source code.
- only an envelop with metadata (to be defined) describing information
on an (already or not yet) uploaded archive
- both

After validation of the header and body request, the server:

- uploads such content in a temporary location (to be defined).

- answers the client an 'http 201 Created'. In the Location header of
  the response lies a deposit receipt id permitting the client to
  check back the operation status later on.

- Asynchronously, the server will inject the archive uploaded and the
  associated metadata (swh-loader-tar). The operation status mentioned
  earlier is a reference to that injection operation.

## Mono deposit

This describes the posting of an archive (in possibly multiple
requests).

### client

In one or multiple requests, the client can deposit a binary file,
supplying the following headers:
- Content-Type (text): accepted mimetype
- Content-Length (int):
- Content-MD5 (text): md5 checksum hex encoded of the tarball
- Content-Disposition (text): attachment; filename=[filename] ; the filename
  parameter must be text (ascii)
- Packaging (IRI): http://purl.org/net/sword/package/SimpleZip
- In-Progress (bool): true to specify it's not the last request, false
  to specify it's a final request and the server can go on with
  processing the request's information

Example:
```
POST Col-IRI HTTP/1.1
Host: archive.softwareheritage.org
Content-Type: application/zip
Content-Length: [content length]
Content-MD5: [md5-digest]
Content-Disposition: attachment; filename=[filename]
Packaging: http://purl.org/net/sword/package/METSDSpaceSIP
In-Progress: true|false
[request entity]
```

POST /1/software/

### server

The server receives the request and:
- saves the archives in a temporary location
- executes a md5 checksum on that archive and check it against the
  same header information
- adds a deposit entry and retrieves the associated id

The server answers either:
- OK: 201 created with one header 'Location' with the deposit receipt
  id
- KO: with the error status code and associated message
  (cf. [possible errors paragraph](#possible errors)).

## Multipart deposit

This describes the posting of an archive along with metadata about
that archive (in possibly multiple requests).

Client provides:
- Content-Disposition (text): header of type 'attachment' on the Entry
  Part with a name parameter set to 'atom'
- Content-Disposition (text): header of type 'attachment' on the Media
  Part with a name parameter set to payload and a filename parameter
  [SWORD004] (the filename will be expressed in ASCII).
- Content-MD5 (text): md5 checksum hex encoded of the tarball

- Packaging (text): http://purl.org/net/sword/package/SimpleZip
  (packaging format used on the Media Part)
- In-Progress (bool): true|false
- add metadata formats or foreign markup to the atom:entry element (TO
  BE DEFINED)

## Example

``` xml
POST deposit HTTP/1.1
Host: archive.softwareheritage.org
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

    <!-- some embedded metadata TO BE DEFINED -->

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

## API

POST /1/deposit/

Answers:

- OK: 201 created + 'Location' header with the deposit receipt id
- KO: any errors mentioned in the [possible errors paragraph](#possible errors).

# Deposit Update

The client previously uploaded an archive and wants to add either new
metadata information or a new version for that previous deposit
(possibly in multiple steps as well).  The important thing to note
here is that for swh, this will result in a new version of the
previous deposit in any case.

Providing the identifier of the previous version deposit received from
the status URI, the client executes a PUT request on the same URI as
the deposit one.

After validation of the body request, the server:
- uploads such content in a temporary location (to be defined).

- answers the client an 'http 204 (No content)'. In the Location
  header of the response lies a deposit receipt id permitting the
  client to check back the operation status later on.

- Asynchronously, the server will inject the archive uploaded and the
  associated metadata. The operation status mentioned earlier is a
  reference to that injection operation. The fact that the version is
  a new one is up to the tarball injection.

URL: PUT /1/deposit/<previous-swh-id>

# Deposit Removal

[#limitation](As explained in the limitation paragraph), removal won't
be implemented.  Nothing is removed from the SWH archive.

The server answers a '405 Method not allowed' error.


# Operation Status

Providing a deposit receipt id, the client asks the operation status
of a prior upload.

URL: GET /1/software/{deposit_receipt}


# Possible errors

## sword:ErrorContent

IRI: http://purl.org/net/sword/error/ErrorContent

The supplied format is not the same as that identified in the
Packaging header and/or that supported by the server Associated HTTP

Status: 415 (Unsupported Media Type) or 406 (Not Acceptable)

## sword:ErrorChecksumMismatch

IRI: http://purl.org/net/sword/error/ErrorChecksumMismatch

Checksum sent does not match the calculated checksum. The server MUST
also return a status code of 412 Precondition Failed

## sword:ErrorBadRequest

IRI: http://purl.org/net/sword/error/ErrorBadRequest

Some parameters sent with the POST/PUT were not understood. The server
MUST also return a status code of 400 Bad Request.

## sword:MediationNotAllowed

IRI: http://purl.org/net/sword/error/MediationNotAllowed

Used where a client has attempted a mediated deposit, but this is not
supported by the server. The server MUST also return a status code of
412 Precondition Failed.

## sword:MethodNotAllowed

IRI: http://purl.org/net/sword/error/MethodNotAllowed

Used when the client has attempted one of the HTTP update verbs (POST,
PUT, DELETE) but the server has decided not to respond to such
requests on the specified resource at that time. The server MUST also
return a status code of 405 Method Not Allowed

## sword:MaxUploadSizeExceeded

IRI: http://purl.org/net/sword/error/MaxUploadSizeExceeded

Used when the client has attempted to supply to the server a file
which exceeds the server's maximum upload size limit

Associated HTTP Status: 413 (Request Entity Too Large)

----------------------------------------------------------------------


# Tarball Injection

Providing we use indeed synthetic revision to represent a version of a
tarball injected through the sword use case, this needs to be improved
so that the synthetic revision is created with a parent revision (the
previous known one for the same 'origin').


Note:
- origin may no longer be the right term (we may need a new 'at the
  same level' notion, maybe 'deposit'?)

- As there are no authentication, everyone can push a new version for
  the same tarball so we might need to use the synthetic revision's
  author (or committer?) date to discriminate which is the last known
  version for the same 'origin'.


# Technical

We will need:
- one dedicated db to store state - swh-sword
- one dedicated temporary storage to store archives
- 'deposit' table:
  - id (bigint); deposit receipt id
  - external id (text):
  - date: date of the full deposit is done
  - status (enum): received, ongoing, partial, full

# source

- [http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html](SWORD v2 specification).
- [https://arxiv.org/help/submit_sword](arxiv documentation)
- [http://guides.dataverse.org/en/4.3/api/sword.html]()
