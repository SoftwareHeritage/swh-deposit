= swh-deposit (draft) =

This is SWH's SWORD Server implementation.

SWORD (Simple Web-Service Offering Repository Deposit) is an
interoperability standard for digital file deposit.

This protocol will be used to interact between a client (a repository)
and a server (swh repository) to permit the deposit of software
tarballs.

In this document, we will refer to a client (e.g. HAL server) and a
server (SWH's).

== Use cases ==

=== First deposit ===

Endpoint: /1/<user-or-collection>/

From client's deposit repository server to SWH's repository server
(aka deposit).

1. The client requests for the server's abilities.
(GET query to the *service document uri*)

2. The server answers the client with the service document

3. The client sends the deposit (an archive -> .zip) through the
deposit *creation uri*

This can be done in:
- one POST request to the creation uri (metadata + archive).
- one POST request to the creation uri + other PUT request to the *update uri*

4. The server notifies the client it acknowledged the client's
request. An 'http 201 Created' response with a deposit receipt is sent
back.  That deposit receipt will hold the necessary information to
eventually complete the deposit if it was partial.

=== Updating an existing archive ===

5. Client updates existing archive through the deposit *update uri*
(one or more PUT requests).

This would be the case for example if:
- the client initially posted only metadata (with no archive)
- the client initially posted only one archive (without metadata)

And that client would like to complete its deposit with another
archive (or other metadata)

=== Deleting an existing archive ===

6. Document deletion will not be implemented, cf. limitation paragraph
for detail


== Limitations ==

Applying the SWORD protocol procedure will result with voluntary implementation
shortcomings during the first iteration:

- upload limitation of 20Mib
- only tarballs (.zip) will be accepted
- no removal (implementation-wise, this will possibly be a means
  to hide the origin).
- basic http authentication enforced at the application layer
  on a per client basis (authentication:
  http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#authenticationmediateddeposit)
- no mediation (we do not know the other system's users)

== Collection ==

SWORD defines a 'collection' concept.  The collection refers to a
group of documents to which the document uploaded (a.k.a deposit) is
part of.

For example, we will start the collaboration with HAL, thus we define a HAL collection to which hal clients will deposit new document.

=== Client asks for operation status and repository id ===

A state endpoint is defined in the sword specification to provide such information.


== API overview ==

API access is over HTTPS.

service document accessible at:
https://deposit.softwareheritage.org/1/

=== Service document ===

Endpoint: /1/servicedocument/

This is the starting endpoint from which the user will access its
initial collection information.

This:
- describes the server's abilities
- list the connected user's collection information.

HTTP verbs supported: GET

Also known as: SD-IRI - The Service Document IRI.

==== Sample request:====

``` Shell
GET https://deposit.softwareheritage.org/1/servicedocument/ HTTP/1.1
Host: deposit.softwareheritage.org
```

The server returns its abilities with the service document in xml format:
- protocol sword version v2
- accepted mime types: application/zip, application/gzip
- upload max size accepted, beyond that, it's expected the client
  chunk the tarball into multiple ones
- the collection the client can act upon (swh supports only one
  software collection per client)
- mediation is not supported

==== Sample answer:====

``` XML
The current answer for example for the [hal
archive](https://hal.archives-ouvertes.fr/) is:

``` xml
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

== Deposit Creation: client point of view ==

Process of deposit creation:

-> [3] client request

  - [3.1] server validation
  - [3.2] server temporary upload
  - [3.3] server injects deposit into archive*

<- [4] server returns deposit receipt id


NOTE: [3.3] Asynchronously, the server will inject the archive
uploaded and the associated metadata. The operation status mentioned
earlier is a reference to that injection operation.

The image bellow represent only the communication and creation of
a deposit:

{F2403754}

=== [3] client request  ===

The client can send a deposit through one request deposit or multiple
requests deposit.

The deposit can contain:
- an archive holding the software source code (binary upload)
- an envelop with metadata describing information regarding a deposit
  (atom entry deposit)
- or both (multipart deposit, exactly one archive and one envelop).

the client can deposit a binary file, supplying the following headers:
- Content-Type (text): accepted mimetype
- Content-Length (int): tarball size
- Content-MD5 (text): md5 checksum hex encoded of the tarball
- Content-Disposition (text): attachment; filename=[filename] ; the filename
  parameter must be text (ascii)
- Packaging (IRI): http://purl.org/net/sword/package/SimpleZip
- In-Progress (bool): true to specify it's not the last request, false
  to specify it's a final request and the server can go on with
  processing the request's information.

WARNING: if In-Progress is not present the server MUST assume that it is false

==== API endpoint ====

POST /1/<client-or-collection-name>/

=== Archive deposit ===

This is a single zip archive deposit. Almost no metadata is associated
with the archive except for the unique external identifier.

Note: This kind of deposit should be partial (In-Progress: True) as
almost no metadata can be associated with the uploaded archive.

==== sample request for binary upload deposit ====

```
curl -i --data-binary @swh/deposit.zip \
    -H 'In-Progress: false' -H 'Content-MD5: 0faa1ecbf9224b9bf48a7c691b8c2b6f' \
    -H 'Content-Disposition: attachment; filename=[deposit.zip]' \
    -H 'Slug: some-external-id' \
    -H 'Packaging: http://purl.org/net/sword/package/SimpleZIP' \
    -H 'Content-type: application/zip' \
    -XPOST http://127.0.0.1:8000/1/hal/
```

=== Atom entry deposit ===

Sample atom entry:
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

Note: This kind of deposit should be partial (In-Progress: True) since
no archive will be associated to those metadata.

==== One request deposit / Multipart deposit ====

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

==== sample request for multipart deposit: ====

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

== Deposit Creation - server point of view ==

The server receives the request and:

=== [3.1] Validation of the header and body request ===

Any kind of errors can happen, here is the list depending on the situation:

- archive deposit:
  - 400 (bad request) if the request is not providing an external
    identifier
  - 403 (forbidden) if the length of the archive exceeds the
    max size configured
  - 412 (precondition failed) if the length or hash provided
    mismatch the reality of the archive.
  - 415 (unsupported media type) if a wrong media type is
    provided

- multipart deposit:
  - 400 (bad request) if the request is not providing an external
    identifier
  - 412 (precondition failed) if the potentially md5 hash
    provided mismatch the reality of the archive
  - 415 (unsupported media type) if a wrong media type is
    provided

- Atom entry deposit:
  - 400 (bad request) if the request is not providing an external
    identifier
  - 400 (bad request) if the request's body is empty
  - 415 (unsupported media type) if a wrong media type is
    provided

=== [3.2] Server uploads the content in a temporary location ==

Using an objstorage, the server stores the archive in a temporary
location, the time the deposit is completed.

Store those information as metadata associated to the request.

=== [4] Servers answers the client ===

If everything went well, an 'http 201 Created' response is returned.
The body holds the deposit receipt.
The headers holds the EDIT-IRI in the Location header of the response.

The server possible answers are:
- OK: '201 created' + one header 'Location' holding the EDIT IRI
- KO: with the error status code and associated message
  (cf. [possible errors paragraph](#possible errors)).


=== [5] Deposit Update ===

The client previously deposited a partial document (through an
archive, or metadata). The client wants to update new metadata
information or other archives for that previous deposit (possibly in
multiple steps as well).

The important thing to note here is that for swh, as long as the
deposit is in status 'partial', the injection did not start.  So the
user can update information (new archive, new metadata) for that same
partial deposit. The aggregation of all those information will then be
used when the injection starts (when the deposit is complete).

However, as soon as the deposit is in another state (different than
'partial'), the update will refuse to continue. It is then expected
that the client will create a new deposit (for a new version).

Providing the identifier of the previous deposit id received from the
status URI, the client executes a PUT request on the same URI as the
deposit one.

After validation of the body request, the server:
- uploads such content in a temporary location (to be defined).

- answers the client an 'http 204 (No content)'. In the Location
  header of the response lies a deposit receipt id permitting the
  client to check back the operation status later on.

- Asynchronously, the server will inject the archive uploaded and the
  associated metadata. The operation status mentioned earlier is a
  reference to that injection operation. The fact that the version is
  a new one is dealt with at the injection level.

  URL: PUT /1/<collection-name>/<deposit-id>/

=== [6] Deposit Removal ===

[#limitation](As explained in the limitation paragraph), removal won't
be implemented.  Nothing is removed from the SWH archive.

The server answers a '405 Method not allowed' error.

=== Operation Status ===

Providing a collection name and a deposit receipt id, the client asks
the operation status of a prior deposit.

  URL: GET /1/<collection-name>/<deposit_id>/status/

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

---------------

== Tarball Injection ==

Providing we use indeed synthetic revision to represent a version of a
tarball injected through the sword use case, this needs to be improved
so that the synthetic revision is created with a parent revision (the
previous known one for the same 'origin').


=== Injection mapping ===
| origin                              |      https://hal.inria.fr/hal-id      |
|-------------------------------------|---------------------------------------|
| origin_visit                        |           1 :reception_date           |
| occurrence &amp; occurrence_history | branch: client's version n° (e.g hal) |
| revision                            |      synthetic_revision (tarball)     |
| directory                           | upper level of the uncompressed archive|


=== Questions raised concerning injection: ===
- A deposit has one origin, yet an origin can have multiple deposits ?

No, an origin can have multiple requests for the same deposit,
which should end up in one single deposit (when the client pushes its final
request saying deposit 'done' through the header In-Progress).

When an update of a deposit is requested,
the new version is identified with the external_id.

Illustration First deposit injection:

HAL's deposit 01535619 = SWH's deposit **01535619-1**

    + 1 origin with url:https://hal.inria.fr/medihal-01535619

    + 1 synthetic revision

    + 1 directory

HAL's update on deposit 01535619 = SWH's deposit **01535619-2**

(*with HAL updates can only be on the metadata and a new version is required
if the content changes)
    + 1 origin with url:https://hal.inria.fr/medihal-01535619

    + new synthetic revision (with new metadata)

    + same directory

HAL's deposit 01535619-v2 = SWH's deposit **01535619-v2-1**

    + same origin

    + new revision

    + new directory



== Technical details ==

We will need:
- one dedicated db to store state - swh-deposit

- one dedicated temporary storage to store archives before injection

- one client to test the communication with SWORD protocol

=== Deposit reception schema ===

- **deposit** table:
  - id (bigint): deposit receipt id

  - external id (text): client's internal identifier (e.g hal's id, etc...).

  - origin id : null before injection
  - swh_id : swh identifier result once the injection is complete

  - reception_date: first deposit date

  - complete_date: reception date of the last deposit which makes the deposit
  complete

  - status (enum):
```
      'partial',      -- the deposit is new or partially received since it
                      -- can be done in multiple requests
      'expired',      -- deposit has been there too long and is now deemed
                      -- ready to be garbage collected
      'ready',        -- deposit is fully received and ready for injection
      'scheduled',    -- injection is scheduled on swh's side
      'success',      -- injection successful
      'failure'       -- injection failure
```
- **deposit_request** table:
  - id (bigint): identifier
  - deposit_id: deposit concerned by the request
  - metadata: metadata associated to the request

- **client** table:
  - id (bigint): identifier
  - name (text): client's name (e.g HAL)
  - credentials


All metadata (declared metadata) are stored in deposit_request (with the
request they were sent with).
When the deposit is complete metadata fields are aggregated and sent
to injection. During injection the metadata is kept in the
origin_metadata table (see [metadata injection](#metadata-injection)).

The only update actions occurring on the deposit table are in regards of:
  - status changing
    - partial -> {expired/ready},
    - ready -> scheduled,
    - scheduled -> {success/failure}
  - complete_date when the deposit is finalized
  (when the status is changed to ready)
  - swh-id being populated once we have the result of the injection

==== SWH Identifier returned? ====

    swh-<client-name>-<synthetic-revision-id>

    e.g: swh-hal-47dc6b4636c7f6cba0df83e3d5490bf4334d987e

    We could have a specific dedicated 'client' table to reference client
    identifier.

=== Scheduling injection ===
All data and metadata separated with multiple requests should be aggregated
before injection.

TODO: injection modeling

=== Metadata injection ===
- the metadata received with the deposit should be kept in the origin_metadata
table before translation as part of the injection process and a indexation
process should be scheduled.

origin_metadata table:
```
origin                                  bigint        PK FK
discovery_date                          date          PK FK
translation_date                        date          PK FK
provenance_type                         text                  // (enum: 'publisher', 'lister' needs to be completed)
raw_metadata                            jsonb                 // before translation
indexer_configuration_id                bigint            FK  // tool used for translation
translated_metadata                     jsonb                 // with codemeta schema and terms
```

== Nomenclature ==

SWORD uses IRI. This means Internationalized Resource Identifier. In
this chapter, we will describe SWH's IRI.

=== Col-IRI - The Collection IRI ===

The software collection associated to one user.

The SWORD Collection IRI is the IRI to which the initial deposit will
take place, and which is listed in the Service Document.

Following our previous example, this is:
https://deposit.softwareheritage.org/1/hal/.

HTTP verbs supported: POST

=== Cont-IRI - The Content IRI ===

This is the endpoint which permits the client to retrieve
representations of the object as it resides in the SWORD server.

This will display information about the content and its associated
metadata.

HTTP verbs supported: GET

=== EM-IRI - The Atom Edit Media IRI ===

This is the endpoint to upload other related archives for the same
deposit.

Typically, if  a first archive  is too big,  the client can  split it.
Post  the first  partial  archive in  the  Col-IRI (with  In-Progress:
True).  Then  other archives needs  to be  uploaded to this  IRI.  The
last  one mentioning  the  In-Progress  flag to  False  to notify  the
deposit is done.

HTTP verbs supported: PUT

=== Edit-IRI - The Atom Entry Edit IRI ===

This is the endpoint to update metadata for a previous incomplete
deposit.

HTTP verbs supported: PUT

=== SE-IRI - The SWORD Edit IRI ===

This is the IRI to which clients may POST additional content to an
Atom Entry Resource. This is the same as Edit-IRI.

HTTP verbs supported: POST

=== State-IRI - The SWORD Statement IRI ===

This is the one of the IRIs which can be used to retrieve a
description of the object from the sword server, including the
structure of the object and its state. This will be used as the
operation status endpoint.

HTTP verbs supported: GET

== Sources ==

- [SWORD v2 specification](http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html)
- [arxiv documentation](https://arxiv.org/help/submit_sword)
- [Dataverse example](http://guides.dataverse.org/en/4.3/api/sword.html)
- [SWORD used on HAL](https://api.archives-ouvertes.fr/docs/sword)
- [xml examples for CCSD](https://github.com/CCSDForge/HAL/tree/master/Sword)