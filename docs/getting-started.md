# Getting Started

This is a getting started to demonstrate the deposit api use case with
a shell client.

The api is rooted at https://deposit.softwareheritage.org.

For more details, see the [main README](./README.md).

## Requirements

You need to be referenced on SWH's client list to have:
- a credential (needed for the basic authentication step).
- an associated collection

[Contact us for more information.](https://www.softwareheritage.org/contact/)

## Demonstration

For the rest of the document, we will:
- reference `<client-name>` as the client and `<pass>` as its
associated authentication password.
- use curl as example on how to request the api.
- present the main deposit use cases.

The use cases are:

- one single deposit step: The user posts in one query (one deposit) a
  software source code archive and associated metadata (deposit is
  finalized with status `ready`).

  This will demonstrate the multipart query.

- another 3-steps deposit (which can be extended as more than 2
  steps):
  1. Create an incomplete deposit (status `partial`)
  2. Update a deposit (and finalize it, so the status becomes `ready`)
  3. Check the deposit's state

  This will demonstrate the stateful nature of the sword protocol.

Those use cases share a common part, they must start by requesting the
`service document iri` (internationalized resource identifier) for
information about the collection's location.

### Common part - Start with the service document

First, to determine the *collection iri* onto which deposit data, the
client needs to ask the server where is its *collection* located. That
is the role of the *service document iri*.

For example:

``` Shell
curl -i --user <client-name>:<pass> https://deposit.softwareheritage.org/1/servicedocument/
```

If everything went well, you should have received a response similar
to this:

``` Shell
HTTP/1.0 200 OK
Server: WSGIServer/0.2 CPython/3.5.3
Content-Type: application/xml

<?xml version="1.0" ?>
<service xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:sword="http://purl.org/net/sword/terms/"
    xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns="http://www.w3.org/2007/app">

    <sword:version>2.0</sword:version>
    <sword:maxUploadSize>209715200</sword:maxUploadSize>

    <workspace>
        <atom:title>The Software Heritage (SWH) Archive</atom:title>
        <collection href="https://deposit.softwareheritage.org/1/<collection-name>/">
            <atom:title><client-name> Software Collection</atom:title>
            <accept>application/zip</accept>
            <sword:collectionPolicy>Collection Policy</sword:collectionPolicy>
            <dcterms:abstract>Software Heritage Archive</dcterms:abstract>
            <sword:treatment>Collect, Preserve, Share</sword:treatment>
            <sword:mediation>false</sword:mediation>
            <sword:acceptPackaging>http://purl.org/net/sword/package/SimpleZip</sword:acceptPackaging>
            <sword:service>https://deposit.softwareheritage.org/1/<collection-name>/</sword:service>
        </collection>
    </workspace>
</service>
```

Explaining the response:
- `HTTP/1.0 200 OK`: the query is successful and returns a body response
- `Content-Type: application/xml`: The body response is in xml format
- `body response`: it is a service document describing that the client
  `<client-name>` has a collection named `<collection-name>`. That
  collection is available at the *collection iri*
  `/1/<collection-name>/` (through POST query).

At this level, if something went wrong, this should be authentication related.
So the response would have been a 401 Unauthorized access.
Something like:

``` Shell
curl -i https://deposit.softwareheritage.org/1/<collection-name>/
HTTP/1.0 401 Unauthorized
Server: WSGIServer/0.2 CPython/3.5.3
Content-Type: application/xml
WWW-Authenticate: Basic realm=""
X-Frame-Options: SAMEORIGIN

<?xml version="1.0" encoding="utf-8"?>
<sword:error xmlns="http://www.w3.org/2005/Atom"
       xmlns:sword="http://purl.org/net/sword/">
    <summary>Access to this api needs authentication</summary>
    <sword:treatment>processing failed</sword:treatment>

</sword:error>
```

### Single deposit

A single deposit translates to a multipart deposit request.

This means, in swh's deposit's terms, sending exactly one POST query
with:
- 1 archive (`content-type application/zip`)
- 1 atom xml content (`content-type: application/atom+xml;type=entry`)

The supported archive, for now are limited to zip files.  Those
archives are expected to contain some form of software source
code. The atom entry content is some xml defining metadata about that
software.

Example of minimal atom entry file:

``` XML
<?xml version="1.0"?>
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
    <dcterms:bibliographicCitation>Bibliographic Citation</dcterms:bibliographicCitation>
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

Once the files are ready for deposit, we want to do the actual deposit
in one shot.

For this, we need to provide:
- the contents and their associated correct content-types
- either the header `In-Progress` to false (meaning, it's finished
after this query) or nothing (the server will assume it's not in
progress if not present).
- Optionally, the `Slug` header, which is a reference to a unique
identifier the client knows about and wants to provide us.

You can do this with the following command:

``` Shell
curl -i --user <client-name>:<pass> \
    -F "file=@deposit.zip;type=application/zip;filename=payload" \
    -F "atom=@atom-entry.xml;type=application/atom+xml;charset=UTF-8" \
    -H 'In-Progress: false' \
    -H 'Slug: some-external-id' \
    -XPOST https://deposit.softwareheritage.org/1/<collection-name>/
```

You just posted a deposit to the collection <collection-name>
https://deposit.softwareheritage.org/1/<collection-name>/.

If everything went well, you should have received a response similar
to this:

``` Shell
HTTP/1.0 201 Created
Server: WSGIServer/0.2 CPython/3.5.3
Location: /1/<collection-name>/10/metadata/
Content-Type: application/xml

<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:sword="http://purl.org/net/sword/"
       xmlns:dcterms="http://purl.org/dc/terms/">
    <deposit_id>9</deposit_id>
    <deposit_date>Sept. 26, 2017, 10:11 a.m.</deposit_date>
    <deposit_archive>payload</deposit_archive>
    <deposit_status>ready</deposit_status>

    <!-- Edit-IRI -->
    <link rel="edit" href="/1/<collection-name>/10/metadata/" />
    <!-- EM-IRI -->
    <link rel="edit-media" href="/1/<collection-name>/10/media/"/>
    <!-- SE-IRI -->
    <link rel="http://purl.org/net/sword/terms/add" href="/1/<collection-name>/10/metadata/" />
    <!-- State-IRI -->
    <link rel="alternate" href="/1/<collection-name>/10/status/"/>

    <sword:packaging>http://purl.org/net/sword/package/SimpleZip</sword:packaging>
</entry>
```

Explaining this response:
- `HTTP/1.0 201 Created`: the deposit is successful
- `Location: /1/<collection-name>/10/metadata/`: the EDIT-SE-IRI through which we can
  update a deposit
- body response: it is a deposit receipt detailing all endpoints
  available to manipulate the deposit (update, replace, delete,
  etc...)  It also explains the deposit identifier to be 9 (which is
  useful for the remaining example).

Note: As the deposit is in `ready` status (meaning ready to be
injected), you cannot actually update anything after this query.
Well, the client can try, but it will be answered with a 403 forbidden
answer.

### Multi-steps deposit

1. Create a deposit

We will use the collection IRI again as the starting point.

We need to explicitely give to the server information about:
- the deposit's completeness (through header `In-Progress` to true, as
  we want to do in multiple steps now).
- archive's md5 hash (through header `Content-MD5`)
- upload's type (through the headers `Content-Disposition` and
  `Content-Type`)

The following command:

``` Shell
curl -i --user <client-name>:<pass> \
    --data-binary @swh/deposit.zip \
    -H 'In-Progress: true' \
    -H 'Content-MD5: 0faa1ecbf9224b9bf48a7c691b8c2b6f' \
    -H 'Content-Disposition: attachment; filename=[deposit.zip]' \
    -H 'Slug: some-external-id' \
    -H 'Packaging: http://purl.org/net/sword/package/SimpleZIP' \
    -H 'Content-type: application/zip' \
    -XPOST https://deposit.softwareheritage.org/1/<collection-name>/
```

The expected answer is the same as the previous sample.

2. Update deposit's metadata

To update a deposit, we can either add some more archives, some more
metadata or replace existing ones.

As we don't have defined metadata yet (except for the `slug` header),
we can add some to the `EDIT-SE-IRI` endpoint (/1/<collection-name>/10/metadata/).
That information is extracted from the deposit receipt sample.

Using here the same atom-entry.xml file presented in previous chapter.

For example, here is the command to update deposit metadata:

``` Shell
curl -i --user <client-name>:<pass> --data-binary @atom-entry.xml \
-H 'In-Progress: true' \
-H 'Slug: some-external-id' \
-H 'Content-Type: application/atom+xml;type=entry' \
-XPOST https://deposit.softwareheritage.org/1/<collection-name>/10/metadata/
HTTP/1.0 201 Created
Server: WSGIServer/0.2 CPython/3.5.3
Location: /1/<collection-name>/10/metadata/
Content-Type: application/xml

<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:sword="http://purl.org/net/sword/"
       xmlns:dcterms="http://purl.org/dc/terms/">
    <deposit_id>10</deposit_id>
    <deposit_date>Sept. 26, 2017, 10:32 a.m.</deposit_date>
    <deposit_archive>None</deposit_archive>
    <deposit_status>partial</deposit_status>

    <!-- Edit-IRI -->
    <link rel="edit" href="/1/<collection-name>/10/metadata/" />
    <!-- EM-IRI -->
    <link rel="edit-media" href="/1/<collection-name>/10/media/"/>
    <!-- SE-IRI -->
    <link rel="http://purl.org/net/sword/terms/add" href="/1/<collection-name>/10/metadata/" />
    <!-- State-IRI -->
    <link rel="alternate" href="/1/<collection-name>/10/status/"/>

    <sword:packaging>http://purl.org/net/sword/package/SimpleZip</sword:packaging>
</entry>
```

3. Check the deposit's state

You need to check the STATE-IRI endpoint (/1/<collection-name>/10/status/).

``` Shell
curl -i --user <client-name>:<pass> https://deposit.softwareheritage.org/1/<collection-name>/10/status/
HTTP/1.0 200 OK
Date: Wed, 27 Sep 2017 08:25:53 GMT
Content-Type: application/xml
```

Response:

``` XML
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:sword="http://purl.org/net/sword/"
       xmlns:dcterms="http://purl.org/dc/terms/">
    <deposit_id>9</deposit_id>
    <deposit_status>ready</deposit_status>
    <deposit_status_detail>deposit is fully received and ready for injection</deposit_status_detail>
</entry>

```
