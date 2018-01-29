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

  - in this document we reference ``<name>`` as the client's name and
 ``<pass>`` as its associated authentication password.

 * an associated collection


`Contact us for more
information. <https://www.softwareheritage.org/contact/>`__

Prepare a deposit
-----------------
* compress the files in a supported archive format:

  - zip: common zip archive (no multi-disk zip files).
  - tar: tar archive without compression or optionally any of the
         following compression algorithm gzip (.tar.gz, .tgz), bzip2
         (.tar.bz2) , or lzma (.tar.lzma)
* prepare a metadata file (`more details <./metadata.html>`__.):

  - specify metadata schema/vocabulary (CodeMeta is recommended)
  - specify *MUST* metadata (url, authors, software name and
    the external\_identifier)
  - add all available information under the compatible metadata term

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


Push deposit
------------
You can push a deposit with:

* a one single deposit (archive + metadata):

  The user posts in one query a software
  source code archive and associated metadata.
  The deposit is directly marked with status ``deposited``.
* a multisteps deposit:

  1. Create an incomplete deposit (marked with status ``partial``)
  2. Add data to a deposit (in multiple requests if needed)
  3. Finalize deposit (the status becomes ``deposited``)


Single deposit
^^^^^^^^^^^^^^


Once the files are ready for deposit, we want to do the actual deposit
in one shot, sending exactly one POST query:

* 1 archive (content-type ``application/zip`` or ``application/x-tar``)
* 1 metadata file in atom xml format (``content-type: application/atom+xml;type=entry``)

For this, we need to provide:

* the arguments: ``--username 'name' --password 'pass'`` as credentials
* the name of the archive  (example: ``path/to/archive-name.tgz``)
* in the same location of the archive and with the following namimg pattern
  for the metadata file: ``path/to/archive-name.metadata.xml``
* optionally, the --slug 'your-id' argument, a reference to a unique identifier
  the client uses for the software object.

You can do this with the following command:

minimal deposit

.. code:: shell

 $ swh-deposit ---username name --password secret \
               --archive je-suis-gpl.tgz

with the client's identifier

.. code:: shell

 $ swh-deposit --username name --password secret \
               --archive je-suis-gpl.tgz \
               --slug '123456'

deposit to a specific client's collection

.. code:: shell

 $ swh-deposit --username name --password secret \
               --archive je-suis-gpl.tgz \
               --collection 'second-collection'



You just posted a deposit to your collection on Software Heritage


If everything went well, the successful response will contain the
elements below:

.. code:: shell

  {
    'deposit_status': 'deposited',
    'deposit_id': '7'
  }

Note: As the deposit is in ``deposited`` status, you cannot
update the deposit after this query. It will be answered with
a 403 forbidden answer.

multisteps deposit
^^^^^^^^^^^^^^^^^^^^^^^^^
The steps to create a multisteps deposit:

1. Create an incomplete deposit
~~~~~~~~~~~~~~~~~~~
First use the ``--partial`` argument to declare there is more to come

.. code:: shell

  $ swh-deposit --username name --password secret --partial \
                --archive foo.tar.gz


2. Add content or metadata to the deposit
~~~~~~~~~~~~~~~~~~~
Continue the deposit by using the ``--deposit-id`` argument given as a response
for the first step. You can continue adding content or metadata while you use
the ``--partial`` argument.

.. code:: shell

  $ swh-deposit --username name --password secret --partial \
                --archive add-foo.tar.gz \
                --deposit-id 42


In case you want to add only content without metadata:

.. code:: shell

  $ swh-deposit --username name --password secret --partial \
                --archive add-foo.tar.gz \
                --archive-deposit
                --deposit-id 42

If you want to add only metadata, use:

.. code:: shell

  $ swh-deposit --username name --password secret --partial \
                --metadata add-foo.tar.gz.metadata.xml \
                --metadata-deposit
                --deposit-id 42

3. Finalize deposit
~~~~~~~~~~~~~~~~~~~
On your last addition, by not declaring it as  ``--partial``, the deposit will be
considered as completed and its status will be changed to ``deposited``.



Update deposit
----------------
* replace deposit :

  - only possible if the deposit status is ``partial``
  - by using the ``--replace`` argument
  - you can replace only metadata with the --metadata-deposit flag
  - or only the archive with --archive-deposit
  - if none is used, you'll replace metadata and content

.. code:: shell

  $ swh-deposit --username name --password secret --replace\
                --deposit-id 11 \
                --archive updated-je-suis-gpl.tar.gz

* update a loaded deposit with a new version:

  - by using the external-id with the ``--slug`` argument which will link the
    new deposit with its parent deposit

.. code:: shell

  $ swh-deposit --username name --password secret --slug '123456' \
                --archive je-suis-gpl-v2.tgz



Check the deposit's status
--------------------------

You can check the status of the deposit by using the ``--deposit-id`` argument:

.. code:: shell

$ swh-deposit --username name --password secret --deposit-id '11' --status

.. code:: json

  {
    'deposit_id': '11',
    'deposit_status': 'deposited',
    'deposit_swh_id': None,
    'deposit_status_detail': 'Deposit is ready for additional checks \
                              (tarball ok, metadata, etc...)'
  }

The different statuses:

- *partial* : multipart deposit is still ongoing
- *deposited*: deposit completed
- *rejected*: deposit failed the checks
- *verified*: content and metadata verified
- *loading*: loading in-progress
- *done*: loading completed successfully
- *failed*: the deposit loading has failed

When the deposit has been loaded into the archive, the status will be
marked ``done``. In the response, will also be available the
<deposit_swh_id>. For example:

.. code:: json

 {
  'deposit_id': '11',
  'deposit_status': 'done',
  'deposit_swh_id': 'swh:1:rev:34898aa991c90b447c27d2ac1fc09f5c8f12783e',
  'deposit_status_detail': 'The deposit has been successfully \
                            loaded into the Software Heritage archive'
 }
