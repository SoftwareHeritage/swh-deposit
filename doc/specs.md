swh-deposit (draft)
===================

This is SWH's SWORD Server implementation.

SWORD (Simple Web-Service Offering Repository Deposit) is an
interoperability standard for digital file deposit.

This protocol will be used to interact between a client (a repository)
and a server (swh repository) to permit the deposit of software
tarballs.

In this document, we will refer to a client (e.g. HAL server) and a
server (SWH's).

Table of contents
---------------------
1. [use cases](#uc)
2. [api overview](#api)
3. [limitations](#limitations)
4. [scenarios](#scenarios)
5. [errors](#errors)
6. [tarball injection](#tarball)
7. [technical](#technical)
8. [sources](#sources)

# <a name="uc"> Use cases

## First deposit

From client's deposit repository server to SWH's repository server (aka deposit).

-[\[1\]](#1) The client requests for the server's abilities.
  (GET query to the *service document uri*)

- [\[2\]](#2)The server answers the client with the service document

- [\[3\]](#3) The client sends the deposit (an archive -> .zip, .tar.gz) through the deposit
  *creation uri*.
   (one or more POST requests since the archive and metadata can be sent in multiple times)


- [\[4\]](#4) The server notifies the client it acknowledged the client's request.
  ('http 201 Created' with a deposit receipt id in the Location header of the response)


## Updating an existing archive

-[\[5\]](#5) Client updates existing archive through the deposit *update uri*
  (one or more PUT requests, in effect chunking the artifact to deposit)

## Deleting an existing archive

- [\[6\]](#6) Document deletion will not be implemented, cf. limitation paragraph for
  detail

## Client asks for operation status and repository id

I'm not sure yet as to how this goes in the sword protocol.
I speak of operation status but i've yet to find a reference to this in the sword spec.

- [\[7\]](#7)TODO: Detail this when clear

# <a name="api"> API overview

API access is over HTTPS.

service document accessible at: https://archive.softwareheritage.org/api/1/servicedocument/

API endpoints:

    - without a specific collection, are rooted at https://archive.softwareheritage.org/api/1/deposit/.

    - with a specific and unique collection dubbed 'software', are rooted at https://archive.softwareheritage.org/api/1/software/.


TODO: Determine which one of those solutions according to sword possibilities (cf. 'unclear points' chapter below)

# <a name="limitations"> Limitations

With this SWORD protocol procedure there will be some voluntary implementation shortcomings:

- no removal
- no mediation (we do not know the other system's users)
- upload limitation of 200Mib
- only tarballs (.zip, .tar.gz) will be accepted
- no authentication enforced at the application layer
- basic authentication at the server layer

## unclear points

- SWORD defines a 'collection' notion.  But, as SWH is a software archive, we have only one 'software' collection.

I think the collection refers to a group of documents to which the document sent (aka deposit) is part of
in this process with HAL, HAL is the collection, maybe tomorrow we will do the same with MIT and MIT could be the collection
(the logic of the anwser above is a result of this link: https://hal.inria.fr/USPC the USPC collection)

that makes sense.
Still, i don't think we want to do this.
Or, objectively, i don't see how to implement this correctly.

Specifically, I think, the client can push directly the documents to us.
If for some reasons, we want to list the 'documents', we could distinguish then
(as this could help in reducing the length of documents per client, 1 client being equivalent as 1 collection in this case).

What should we do with this?
  - Define one?
  - Define none? (is it possible? i don't think it is due to the service document part listing the collection to act upon...)


# <a name="scenarios"> Scenarios
## <a name="1">[1] Client request for Service Document

This is the endpoint permitting the client to ask the server's abilities.


### API endpoint

GET api/1/servicedocument/

Answer:
- 200, Content-Type: application/atomserv+xml: OK, with the body
  described below

### Sample request:

``` shell
GET https://archive.softwareheritage.org/api/1/servicedocument HTTP/1.1
Host: archive.softwareheritage.org
```

## <a name="2"> [2] Sever respond for Service Document

The server returns its abilities with the service document in xml format:
- protocol sword version v2
- accepted mime types: application/zip, application/gzip
- upload max size accepted, beyond that, it's expected the client
  chunk the tarball into multiple ones
- the collections the client can act upon (swh supports only one software collection)
- mediation not supported

### Sample answer:
``` xml
<?xml version="1.0" ?>
<service xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:sword="http://purl.org/net/sword/terms/"
    xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns="http://www.w3.org/2007/app">

    <sword:version>2.0</sword:version>
    <sword:maxUploadSize>${max_upload_size}</sword:maxUploadSize>

    <workspace>
        <atom:title>The SWH archive</atom:title>

        <collection href="https://archive.softwareherigage.org/api/1/deposit/">
            <atom:title>SWH Collection</atom:title>
            <accept>application/gzip</accept>
            <accept alternate="multipart-related">application/gzip</accept>
            <dcterms:abstract>Software Heritage Archive Deposit</dcterms:abstract>
            <sword:mediation>false</sword:mediation>
            <sword:acceptPackaging>http://purl.org/net/sword/package/SimpleZip</sword:acceptPackaging>
        </collection>
    </workspace>
</service>
```


## Deposit Creation: client point of view

Process of deposit creation:
    -> [3] client request ->

        ( [3.1] server validation -> [3.2] server temporary upload ) -> [3.3] server injects deposit into archive

     <- [4] server returns deposit receipt id


- [3.3] Asynchronously, the server will inject the archive uploaded and the
  associated metadata. The operation status mentioned
  earlier is a reference to that injection operation.

##  <a name="3"></a> [[3] client request

The client can send a deposit through one request deposit or multiple requests deposit.

The deposit can contain:
- an archive holding the software source code,
- an envelop with metadata describing information regarding a deposit,
- or both (Multipart deposit).

the client can deposit a binary file, supplying the following headers:
- Content-Type (text): accepted mimetype
- Content-Length (int):
- Content-MD5 (text): md5 checksum hex encoded of the tarball (we may need to check for the possibility to support a more secure hash)
- Content-Disposition (text): attachment; filename=[filename] ; the filename
  parameter must be text (ascii)
- Packaging (IRI): http://purl.org/net/sword/package/SimpleZip
- In-Progress (bool): true to specify it's not the last request, false
  to specify it's a final request and the server can go on with
  processing the request's information

TODO: required fields (MUST, SHOULD)

I think the optional one is In-Progress, which if not there should be considered done (I'll check the spec for this).

### API endpoint

POST /api/1/deposit/

### One request deposit

The one request deposit is a single request containing both the metadata (body) and the archive (attachment).

A Multipart deposit is a request of an archive along with metadata about
that archive (can be applied in a one request deposit or multiple requests).

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


### sample request for multipart deposit:

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

## Deposit Creation - server point of view

The server receives the request and:

### [3.1] Validation of the header and body request


### [3.2] Server uploads such content in a temporary location (deposit table in a separated DB).
- saves the archives in a temporary location
- executes a md5 checksum on that archive and check it against the
  same header information
- adds a deposit entry and retrieves the associated id


## <a name="4"></a> [[4] Servers answers the client an 'http 201 Created' with a deposit receipt id in the Location header of
  the response.

The server possible answers are:
- OK: '201 created' + one header 'Location' holding the deposit receipt
  id
- KO: with the error status code and associated message
  (cf. [possible errors paragraph](#possible errors)).


##  <a name="5"></a> [5] Deposit Update

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
  a new one is dealt with at the injection level.

URL: PUT /1/deposit/<previous-swh-id>

## <a name="6"></a> [6] Deposit Removal

[#limitation](As explained in the limitation paragraph), removal won't
be implemented.  Nothing is removed from the SWH archive.

The server answers a '405 Method not allowed' error.


## <a name="7"></a>[7] Operation Status

Providing a deposit receipt id, the client asks the operation status
of a prior upload.

URL: GET /1/software/{deposit_receipt}

# <a name="errors"> Possible errors

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

# <a name="tarball"> Tarball Injection

Providing we use indeed synthetic revision to represent a version of a
tarball injected through the sword use case, this needs to be improved
so that the synthetic revision is created with a parent revision (the
previous known one for the same 'origin').


Note:
- origin may no longer be the right term (we may need a new 'at the
  same level' notion, maybe 'deposit'?)

    * deposit is used for the information

    we agreed that for now origin seems fine enough


- As there are no authentication, everyone can push a new version for
  the same origin so we might need to use the synthetic revision's
  author (or committer?) date to discriminate which is the last known
  version for the same 'origin'.
  Note:
  We'll do something simple, the last version is the last one injected.
  The order should be enforced by the scheduling part of the injection, respecting the reception date.
  We may need another date, the one when the deposit is considered complete and use that date.


## Injection path

    origin                             --> origin_visit        --> occurrence & occurrence_history       --> revision         --> directory (upper level of the uncompressed archive)
    ok for me
    https://hal.inria.fr/hal-01327170  --> 1 :reception_date   --> branch: client's version n° (e.g hal) --> synthetic_revision (tarball)


Questions:
    - can an update be on a version without having a new version?
      No, if something is pushed for the same origin via PUT (update), it will result in a new version (well when the deposit will be complete, injection triggered and done that is)

      For example, depositing only new metadata for the same hal deposit version without providing a new archive can result in a new version targetting the same previous archive.
      And in that case, we won't need the archive again since the targetted directory tree won't have changed, we can simply reuse it.
      That is, we'll create a new synthetic revision targetting the same tree whose parent revision is the last know revision for that origin.
      Is it clear? :D
       so we keep raw metadata in the synthetic revision, yes (we need those to have different hash on revision, the revision metadata column is used to compute its hash).

      That makes me think that for the creation (POST).
      Once the client has said, deposit done for an origin.
      Any further request for that origin should be refused (since they should pass by the PUT endpoint as update).

      Shortcoming:
          what about concurrent deposit for the same origin?
          How do we distinguish them?

    A: The client should identify each package sent if it belongs to a chuncked deposit or a new request for same deposit

    On SWH, we should treat each request separately as a new deposit ??? i think yes (I'm answering myself) because the date of reception should be new

    and the depposit receipt id should be new as well


Actions possible on HAL after deposit is public:
    - modify metadata
    - add file
    - deposit new version
    - link ressource
    - share property
    - use as model


    - A deposit has one origin, yet an origin can have multiple deposits ?
    No, not multiple deposits, multiple requests for the same origin, but in the end, this should end up in one single deposit
    (when the client pushes its final request saying deposit 'done' through the header In-Progress).
    When I say multiple deposits, I mean multiple versions/ updates on a deposit identified with external_id ok
    you are talking about multiple requests in the sense of chuncked deposits yes


    HAL's deposit 01535619 = SWH's deposit 01535619-1

    + 1 origin with url:https://hal.inria.fr/medihal-01535619

    + 1 revision

    + 1 directory

    deposit 01535619-v2 = SWH's deposit 01535619-2

    + same origin

    + new revision

    + new directory



## <a name="technical"> Technical

We will need:
- one dedicated db to store state - swh-deposit

- one dedicated temporary storage to store archives before injection

- 'deposit' table:
  - id (bigint): deposit receipt id
  - external id (text): client's internal identifier (e.g hal's id, etc...).
  - origin id : null before injection
  - revision id : null before full injection I don't think we should store this as this will move at each new version...
  - reception_date: first deposit date
  - complete_date: reception date of the last deposit which makes the deposit complete
  - metadata: jsonb (raw format before translation)
  - status (enum):
      -'partially-received',  -- when only a part of the deposit was received (through multiple requests)

     -'received',            -- deposit is fully received (last request arrived)

     -'injecting',           -- injection is ongoing on swh's side

     -'injected',            -- injection is successfully done

      - 'failed'              -- injection failed due to some error

- the metadata received with the deposit should be kept in the origin_metadata table

    after translation as part of the injection process


    what's the origin_metadata table?

    This is the new table we talked with Zack about

    yes, but i wanted some more details

    it's in swh db?

    nothing about metadata is implemented yet

    but it should be in the main db

    right

    still, the nice thing about what we are doing can be untangled yes it's nice

    That is we could run in production the simple deposit stuff (which does not do anything about the deposit injection yet)

    we accept query and store deposits (since we need the scheduling one-shot task as well... which can be worrisome about the delay)



    i remember zack and you spoke about it during the 'tech meeting' but i did not follow everything at that time.

    origin                                  bigint        PK FK

    visit                                   bigint        PK FK  // ?

    date                                    date

    provenance_type                         text                 // (enum: 'publisher', 'external_catalog' needs to be completed)

    location                                 url                 // only needed if there are use cases where this differs from origin for external_catalogs

    raw_metadata                            jsonb                // before translation

    indexer_configuration_id                bigint            FK // tool used for translation

    translated_metadata                     jsonb                // with codemeta schema and terms


# SWH Identifier returned?

    swh-<client-name>-<synthetic-revision-id>

    e.g: swh-hal-47dc6b4636c7f6cba0df83e3d5490bf4334d987e

    We could have a specific dedicated client table.

# <a name="nomenclature"> Nomenclature

SWORD uses IRI. This means Internationalized Resource Identifier. In
this chapter, we will describe SWH's IRI.

## SD-IRI - The Service Document IRI

This is the IRI from which the root service document can be
located.

## Col-IRI - The Collection IRI

Only one collection of software is used in this repository.

Note:
This is the IRI to which the initial deposit will take place, and
which are listed in the Service Document.
Discuss to check if we want to implement this or not.

## Cont-IRI - The Content IRI

This is the IRI from which the client will be able to retrieve
representations of the object as it resides in the SWORD server.

## EM-IRI - The Atom Edit Media IRI

To simplify, this is the same as the Cont-IRI.

## Edit-IRI - The Atom Entry Edit IRI

This is the IRI of the Atom Entry of the object, and therefore also of
the container within the SWORD server.

## SE-IRI - The SWORD Edit IRI

This is the IRI to which clients may POST additional content to an
Atom Entry Resource. This MAY be the same as the Edit-IRI, but is
defined separately as it supports HTTP POST explicitly while the
Edit-IRI is defined by [AtomPub] as limited to GET, PUT and DELETE
operations.

## State-IRI - The SWORD Statement IRI

This is the one of the IRIs which can be used to retrieve a
description of the object from the sword server, including the
structure of the object and its state. This will be used as the
operation status endpoint.

# <a name="sources"> sources

- [SWORD v2 specification](http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html)
- [arxiv documentation](https://arxiv.org/help/submit_sword)
- [Dataverse example](http://guides.dataverse.org/en/4.3/api/sword.html)
- [SWORD used on HAL]https://api.archives-ouvertes.fr/docs/sword
- [xml examples for CCSD] https://github.com/CCSDForge/HAL/tree/master/Sword
