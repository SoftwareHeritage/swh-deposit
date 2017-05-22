swh-sword-poc (draft)
================

SWORD (Simple Web-Service Offering Repository Deposit) is an
interoperability standard for digital file deposit.

This protocol will be used to interact between a client and a server.

In this document, we will refer to a client (e.g. HAL server) and a
server (SWH).

Rougly, the sword protocol exchange, from repository to repository
scenario, can be summarized in the following manner:

1. Discussion with the client and the server to establish the server's
   abilities (GET). The client asks the server's capacities through a
   GET query to the service document uri. The server answers with the
   sword version supported (v2), a URI list it supports.

2. Client deposits one or more files through the deposit creation uri
   via a POST request.

3. Client updates existing files through the deposit update uri via
   a PUT request.

4. Client deletes a document through the delete uri via a DELETE
   request.

# Limitation

In the current state, there will be some voluntary shortcomings in the
implementation, notably:

- no authentication
- no removal
- upload limitation of 1Gib (less?)
- only tarball (.zip, .tar.gz) will be accepted
- SWORD defines a collection notion.  As SWH is a software archive, we
  will define only one collection dubbed 'software'.

# Service Document

This is a step permitting the client to determine the server's abilities.

The server responds its abilities:
- protocol sword version v2
- accepted mime types: application/zip, application/gzip
- mediation (to act on behalf of) accepted (e.g. HAL will send data on
  behalf of a HAL user)
- the collections the client can act upon (the only collection
  'software')

## API

GET /v1/servicedocument/

Answer:
- 200, Content-Type: application/atomserv+xml: OK, with the body
  described below

## Sample

``` shell
GET https://sword.softwareheritage.org/v1/servicedocument HTTP/1.1
Host: sword.softwareheritage.org
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

        <collection href="https://sword.softwareherigage.org/v1/software/">
            <atom:title>SWH Collection</atom:title>
            <accept>application/zip</accept>
            <accept>application/gzip</accept>
            <accept alternate="multipart-related">application/zip</accept>
            <accept alternate="multipart-related">application/gzip</accept>
            <sword:collectionPolicy>Collection Policy</sword:collectionPolicy>
            <dcterms:abstract>Software Heritage's software collection</dcterms:abstract>
            <sword:mediation>true</sword:mediation>
            <sword:treatment>Treatment description</sword:treatment>
            <sword:acceptPackaging>http://purl.org/net/sword/package/SimpleZip</sword:acceptPackaging>
            <sword:service>https://sword.softwareheritage.org/v1/software/</sword:service>
        </collection>
    </workspace>
</service>
```

# Deposit Creation

The client uploads in possibly multiple steps an archive holding the
software source code to deposit in swh. The body also holds metadata
information (to be defined) that are to be injected in swh's model.

After validation of the body request, the server:

- uploads such content in a temporary location (to be defined).

- answers the client an 'http 201 Created'. In the Location header of
  the response lies a deposit receipt id permitting the client to
  check back the operation status later on.

- Asynchronously, the server will inject the archive uploaded and the
  associated metadata (swh-loader-tar). The operation status mentioned
  earlier is a reference to that injection operation.

## API

POST /v1/software/

Answers:

- OK: 201 created + 'Location' header with the deposit receipt id
- KO: 400 bad request when a problem is raised during the post request
  checks (wrong header, checksum mismatched, tarball too big, etc...)

## Sample

TODO

# Deposit Update

The client previously uploaded an archive and wants to add a new
version (possibly in multiple steps as well). Providing the identifier
of the previous version deposit received from the status URI, the
client executes a PUT request on the same URI as the deposit one.

After validation of the body request, the server:
- uploads such content in a temporary location (to be defined).

- answers the client an 'http 201 Created'. In the Location header of
  the response lies a deposit receipt id permitting the client to
  check back the operation status later on.

- Asynchronously, the server will inject the archive uploaded and the
  associated metadata (swh-loader-tar). The operation status mentioned
  earlier is a reference to that injection operation. The fact that
  the version is a new one is up to the tarball injection.

URL: PUT /v1/software/

# Deposit Removal

[#limitation](As explained in the limitation paragraph), removal won't
be implemented.  Nothing is removed from the SWH archive.


# Operation Status

Providing a deposit receipt id, the client asks the operation status
of a prior upload.

URL: GET /v1/software/{deposit_receipt}


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


# source

- [http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html](SWORD v2 specification).
- [https://arxiv.org/help/submit_sword](arxiv documentation)
- [http://guides.dataverse.org/en/4.3/api/sword.html]()
