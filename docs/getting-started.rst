Getting Started
===============

This is a guide for how to prepare and push a software deposit with
the swh-deposit commands.

The api is rooted at https://deposit.softwareheritage.org.

For more details, see the `main documentation <./index.html>`__.

Requirements
------------

You need to be referenced on SWH's client list to have:

* a credential (needed for the basic authentication step)
- in this document we reference ``<name>`` as the client's name and ``<pass>``
 as its associated authentication password.
* an associated collection (by default the client's name is the collection
name)


`Contact us for more
information. <https://www.softwareheritage.org/contact/>`__

Prepare a deposit
-----------------
* compress the files in a supported archive format:
  - zip: common zip archive (no multi-disk zip files).
  - tar: tar archive without compression or optionally any of the
         following compression algorithm gzip (.tar.gz, .tgz), bzip2
         (.tar.bz2) , or lzma (.tar.lzma)
* prepare a metadata file with an atom xml entry (more details on
`metadata documentation <./metadata.html>`__.):
  - specify metadata schema/vocabulry (CodeMeta is recommended)
  - specify *MUST* metadata (url, authors, software name and
  the external\_identifier)
  - add all available information under the  compatible metadadata term

  An example of an atom entry file with CodeMeta terms:

  .. code:: xml

  <?xml version="1.0"?>
    <entry xmlns="http://www.w3.org/2005/Atom"
             xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
        <title>Je suis GPL</title>
        <external_identifier>12345</external_identifier>
        <codemeta:url>forge.softwareheritage.org/source/jesuisgpl/</codemeta:url>
        <codemeta:description>Yes, this is another implementation of
        "Hello, world!” when you run it.</codemeta:description>
        <codemeta:license>
            <codemeta:name>GPL</codemeta:name>
            <codemeta:url>https://www.gnu.org/licenses/gpl.html</codemeta:url>
        </codemeta:license>
        <codemeta:author>
            <codemeta:name> Reuben Thomas </codemeta:name>
            <codemeta:jobTitle> Maintainer </codemeta:affiliation>
        </codemeta:author>
        <codemeta:author>
            <codemeta:name> Sami Kerola </codemeta:name>
            <codemeta:jobTitle> Maintainer </codemeta:affiliation>
        </codemeta:author>
    </entry>


Check authentication with a service document request
----------------------------------------------------

Start with a simple request to check credentials and retrieve the
*collection iri* onto which the deposit will be pushed .

.. code:: shell

    curl -i --user <name>:<pass> https://deposit.softwareheritage.org/1/servicedocument/

 The successful response:
^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: shell

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
                <accept>application/x-tar</accept>
                <sword:collectionPolicy>Collection Policy</sword:collectionPolicy>
                <dcterms:abstract>Software Heritage Archive</dcterms:abstract>
                <sword:treatment>Collect, Preserve, Share</sword:treatment>
                <sword:mediation>false</sword:mediation>
                <sword:acceptPackaging>http://purl.org/net/sword/package/SimpleZip</sword:acceptPackaging>
                <sword:service>https://deposit.softwareheritage.org/1/<collection-name>/</sword:service>
            </collection>
        </workspace>
    </service>

The error response 401 for Unauthorized access:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: shell

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


Push deposit
------------

* one single deposit (archive + metadata): The user posts in one query (one deposit) a software
  source code archive and associated metadata (deposit is finalized with status
  ``deposited``).
* multi-part deposit
  1. Create an incomplete deposit (status ``partial``)
  2. Add data to a deposit (and finalize it, so the status becomes ``deposited``)
  3. Finalize deposit (can be done during second step)

Single deposit
~~~~~~~~~~~~~~


Once the files are ready for deposit, we want to do the actual deposit
in one shot, sending exactly one POST query with the prepared archive and
metadata file:

* 1 archive (content-type ``application/zip`` or ``application/x-tar``)
* 1 atom xml content (``content-type: application/atom+xml;type=entry``)

For this, we need to provide:

* the arguments: --username 'name' --password 'pass' as credentials
* the name of the archive  (example: 'path/to/archive-name.tgz')
* in the same location of the archive and with the following namimg pattern
for the metadata file: path/to/archive-name.metadata.xml
* optionally, the --slug 'your-id' argument, a reference to a unique identifier
  the client uses for the software object.

You can do this with the following command:

.. code:: shell

minimal deposit
  $ swh-deposit --username 'name' --password 'pass' je-suis-gpl.tgz

with the client's identifier
  $ swh-deposit --username 'name' --password 'pass' je-suis-gpl.tgz --sulg '123456'

deposit to a specific client's collection
  $ swh-deposit --username 'name' --password 'pass' je-suis-gpl.tgz --collection 'second-collection'



You just posted a deposit to your collection on Software Heritage
https://deposit.softwareheritage.org/1/<collection-name>/.

If everything went well, you should have received a response similar to
this:

.. code:: shell

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
        <deposit_status>deposited</deposit_status>

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

* ``HTTP/1.0 201 Created``: the deposit is successful
* ``Location: /1/<collection-name>/10/metadata/``: the EDIT-SE-IRI through
  which we can update a deposit
* body: it is a deposit receipt detailing all endpoints available to manipulate
  the deposit (update, replace, delete, etc...)  It also explains the deposit
  identifier to be 9 (which is useful for the remaining example).

Note: As the deposit is in ``deposited`` status, you cannot actually
update anything after this query. It will be answered with a 403 forbidden answer.

Multi-part deposit
~~~~~~~~~~~~~~~~~~~
The steps to create a multi-part deposit:

Create an incomplete deposit
^^^^^^^^^^^^^^^^^^^^^^^^^^^
First use the --partial argument to declare there is more to come

.. code:: shell

  $ swh-deposit --username 'name' --password 'secret' --partial \
                  foo.tar.gz


Add content or metadata to the deposit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Continue the deposit by using the --deposit-id argument given as a response
for the first step. You can continue adding content or metadat while you use
the --partial argument.

.. code:: shell

  $ swh-deposit --username 'name' --password 'secret' --partial \
          --deposit-id 42 add-foo.tar.gz


Finalize deposit
^^^^^^^^^^^^^^^^^
On your last addition, by not declaring it as --partial, the deposit will be
considered as completed and its status will be changed to ``deposited``.

.. code:: shell
$ swh-deposit --username 'name' --password 'secret' \
              --deposit-id 42 last-foo.tar.gz


Update deposit
----------------
* replace deposit :
  - only possible if the deposit status is ``partial``
  - by using the --replace argument
.. code:: shell
  $ swh-deposit --username 'name' --password 'secret' --replace\
                --deposit-id 11 updated-je-suis-gpl.tar.gz

* update a loaded deposit with a new version
  - by using the external-id with the --slug argument which will link the
  new deposit with its parent deposit

.. code:: shell

  $ swh-deposit --username 'name' --password 'pass' je-suis-gpl-v2.tgz --sulg '123456'



Check the deposit's status
^^^^^^^^^^^^^^^^^^^^^^^^^

You can check the status of the deposit by using the --deposit-id argument:

.. code:: shell

$ swh-deposit --login 'name' --pass 'secret' --deposit-id '11' --status

Response:

.. code:: xml

    <entry xmlns="http://www.w3.org/2005/Atom"
           xmlns:sword="http://purl.org/net/sword/"
           xmlns:dcterms="http://purl.org/dc/terms/">
        <deposit_id>9</deposit_id>
        <deposit_status>deposited</deposit_status>
        <deposit_status_detail>deposit is fully received and ready for loading</deposit_status_detail>
    </entry>

The different statuses:
- *partial* : multipart deposit is still ongoing
- *deposited*: deposit completed
- *rejected*: deposit failed the checks
- *verified*: content and metadata verified
- *loading*: loading in-progress
- *done*: loading completed successfully
- *failed*: the deposit loading has failed

When the the deposit has been loaded into the archive it will be marked ``done``
and in the response will be also available the <deposit_swh_id>.
For more information about the swh-id go to .....
