Getting Started
===================

This is a getting started to demonstrate the deposit api use case with
a shell client.

The api is rooted at https://deposit.softwareheritage.org.

For more details, see the [./README.md](main README).

Requirements
---------------

You need to be referenced on SWH's client list to have:
- a credential (needed for the basic authentication step).
- an associated collection

[Contact us for more information.](https://www.softwareheritage.org/contact/)

Demonstration
----------------

For the rest of the document, we'll reference <client-name>.

We'll use curl as example on how to request the api.

We will present 2 deposit use cases.
Both have a common part.

Use cases:
- one single deposit step: this will create a 'ready' deposit using a
  multipart query.
- another deposit which is in 4 steps:
  1. Create a deposit
  2. Update a deposit (and finalize it)
  3. Check the deposit's state

## Common part

First, to determine the *collection iri*, the client needs to ask the
server where is its *collection* endpoint.  The initial endpoint is
the *service document iri*.

For example:

``` Shell
curl -i --user hal:<pass> https://deposit.softwareheritage.org/1/servicedocument/
```

If everything went well, you should have received a response which
looks like:

``` Shell
HTTP/1.0 200 OK
Date: Tue, 26 Sep 2017 16:24:55 GMT
Server: WSGIServer/0.2 CPython/3.5.3
Content-Type: application/xml
Allow: GET, POST, PUT, DELETE, HEAD, OPTIONS
Vary: Accept, Cookie
X-Frame-Options: SAMEORIGIN

<?xml version="1.0" ?>
<service xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:sword="http://purl.org/net/sword/terms/"
    xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns="http://www.w3.org/2007/app">

    <sword:version>2.0</sword:version>
    <sword:maxUploadSize>209715200</sword:maxUploadSize>
    <sword:verbose>False</sword:verbose>
    <sword:noOp>False</sword:noOp>

    <workspace>
        <atom:title>The Software Heritage (SWH) Archive</atom:title>
        <collection href="https://deposit.softwareheritage.org/1/hal/">
            <atom:title>hal Software Collection</atom:title>
            <accept>application/zip</accept>
            <sword:collectionPolicy>Collection Policy</sword:collectionPolicy>
            <dcterms:abstract>Software Heritage Archive</dcterms:abstract>
            <sword:treatment>Collect, Preserve, Share</sword:treatment>
            <sword:mediation>false</sword:mediation>
            <sword:acceptPackaging>http://purl.org/net/sword/package/SimpleZip</sword:acceptPackaging>
            <sword:service>https://deposit.softwareheritage.org/1/hal/</sword:service>
        </collection>
    </workspace>
</service>
```

Explaining this response:
- `HTTP/1.0 200 OK`: the query is successful and returns a body response
- Content-Type: application/xml: The body response is in xml format
- body response: it is a service document describing that the client
  `hal` has a collection named `hal`. It is available at the
  *collection iri* `/1/hal/` (through POST query).

## Single deposit

A single deposit translates to a multipart deposit request.

This means, in swh's deposit's terms, sending exactly:
- 1 archive with content-type application/zip
- 1 application/atom+xml;type=entry

The archive, for now is a zip files holding some form of software
source code. The atom entry file is an xml file holding metadata about
the software.

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
- the files with the right content-types
- either the header `In-Progress` to false (meaning, it's finished
after this query) or nothing (the server will assume it's not in
progress if not present).
- Optionally, the `Slug` header, which is a reference to a unique
identifier the client knows about and wants to provide us.

You can do this with the following command:

``` Shell
curl -i -u hal:<pass> \
    -F "file=@deposit.zip;type=application/zip;filename=payload" \
    -F "atom=@atom-entry.xml;type=application/atom+xml;charset=UTF-8" \
    -H 'In-Progress: false' \
    -H 'Slug: some-external-id' \
    -XPOST http://deposit.softwareheritage.org/1/hal/
```

You just posted a deposit to
http://deposit.softwareheritage.org/1/hal/, the hal collection IRI.

If everything went well, you should have received a response which
looks like:

``` Shell
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

Explaining this response:
- `HTTP/1.0 201 Created`: the deposit is successful
- `Location: /1/hal/9/metadata/`: the EDIT-SE-IRI through which we can
  update a deposit
- body response: it is a deposit receipt detailing all endpoints
  available to manipulate the deposit (update, replace, delete,
  etc...)  It also explains the deposit identifier to be 9 (which is
  useful for the remaining example).

Note: As the deposit is in `ready` status (meaning ready to be
injected), you cannot actually update anything.  Well, the client can
try, but it will be answered with a 403 forbidden answer.

## Multi-steps deposit

1. Create a deposit

We'll use the collection IRI again as the starting point.

We need to explicitely give to the server information:
- the deposit is not complete (through header `In-Progress` to true).
- md5 hash of the archive to post (through header `Content-MD5`)
- the type of upload (through the headers `Content-Disposition` and `Content-Type`)

The following command:

``` Shell
curl -i -u hal:<pass> \
    --data-binary @swh/deposit.zip \
    -H 'In-Progress: true' \
    -H 'Content-MD5: 0faa1ecbf9224b9bf48a7c691b8c2b6f' \
    -H 'Content-Disposition: attachment; filename=[deposit.zip]' \
    -H 'Slug: some-external-id' \
    -H 'Packaging: http://purl.org/net/sword/package/SimpleZIP' \
    -H 'Content-type: application/zip' \
    -XPOST https://deposit.softwareheritage.org/1/hal/
```

The expected answer is the same as the previous sample.

2. Update a deposit

To update a deposit, we can either add some more archives, some more
metadata or replace existing ones.

As we don't have defined metadata yet (except for the `slug`), we can
add some to the `EDIT-SE-IRI` (/1/hal/9/metadata/).

Using here the same atom-entry.xml file presented in previous chapter.

For example, here is the command to update deposit metadata:

``` Shell
curl -i -u hal:<pass> --data-binary @atom-entry.xml \
-H 'In-Progress: true' \
-H 'Slug: some-external-id' \
-H 'Content-Type: application/atom+xml;type=entry' \
-XPOST http://deposit.softwareheritage.org/1/hal/9/metadata/
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

3. Check the deposit's state
