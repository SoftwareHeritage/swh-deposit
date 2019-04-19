Getting Started
===============

This is a guide for how to prepare and push a software deposit with
the `swh deposit` commands.

The API is rooted at https://deposit.softwareheritage.org/1.

For more details, see the `main documentation <./index.html>`__.

Requirements
------------

You need to be referenced on SWH's client list to have:

* credentials (needed for the basic authentication step)

  - in this document we reference ``<name>`` as the client's name and
    ``<pass>`` as its associated authentication password.

* an associated collection_.


.. _collection: https://bitworking.org/projects/atom/rfc5023#rfc.section.8.3.3


`Contact us for more information.
<https://www.softwareheritage.org/contact/>`__

Prepare a deposit
-----------------
* compress the files in a supported archive format:

  - zip: common zip archive (no multi-disk zip files).
  - tar: tar archive without compression or optionally any of the
         following compression algorithm gzip (`.tar.gz`, `.tgz`), bzip2
         (`.tar.bz2`) , or lzma (`.tar.lzma`)

* prepare a metadata file (`more details <./metadata.html>`__.):

  - specify metadata schema/vocabulary (CodeMeta is strongly recommended)
  - specify *MUST* metadata (url, authors, software name and
    the external\_identifier)
  - add all available information under the compatible metadata term.

  Here is an example of an atom entry file with CodeMeta terms:

.. code:: xml

  <?xml version="1.0" encoding="utf-8"?>
  <entry xmlns="http://www.w3.org/2005/Atom"
  xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
    <title>Je suis GPL</title>
    <client>swh</client>
    <external_identifier>je-suis-gpl</external_identifier>
    <codemeta:url>https://forge.softwareheritage.org/source/jesuisgpl/</codemeta:url>
    <codemeta:dateCreated>2018-01-05</codemeta:dateCreated>
    <codemeta:description>Je suis GPL is a modified version of GNU Hello whose
      sole purpose is to showcase the usage of
      Software Heritage for license compliance purposes.</codemeta:description>
    <codemeta:version>0.1</codemeta:version>
    <codemeta:runtimePlatform>GNU/Linux</codemeta:runtimePlatform>
    <codemeta:developmentStatus>stable</codemeta:developmentStatus>
    <codemeta:programmingLanguage>C</codemeta:programmingLanguage>

    <codemeta:license>
      <codemeta:name>GNU General Public License v3.0 or later</codemeta:name>
      <codemeta:url>https://spdx.org/licenses/GPL-3.0-or-later.html</codemeta:url>
    </codemeta:license>
    <codemeta:author>
      <codemeta:name>Stefano Zacchiroli</codemeta:name>
      <codemeta:jobTitle>Maintainer</codemeta:jobTitle>
    </codemeta:author>
  </entry>



Push deposit
------------
You can push a deposit with:

* a single deposit (archive + metadata):

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

For this, we need to provide the:

* arguments: ``--username 'name' --password 'pass'`` as credentials
* archive's path (example: ``--archive path/to/archive-name.tgz``) :
* (optionally) metadata file's path ``--metadata
  path/to/file.metadata.xml``. If not provided, the archive's filename
  will be used to determine the metadata file, e.g:
  ``path/to/archive-name.tgz.metadata.xml``
* (optionally) ``--slug 'your-id'`` argument, a reference to a
  unique identifier the client uses for the software object.

You can do this with the following command:

minimal deposit

.. code:: shell

 $ swh deposit upload --username name --password secret \
                      --archive je-suis-gpl.tgz

with client's external identifier (``slug``)

.. code:: shell

 $ swh deposit upload --username name --password secret \
                      --archive je-suis-gpl.tgz \
                      --slug je-suis-gpl

to a specific client's collection

.. code:: shell

 $ swh deposit upload --username name --password secret \
                      --archive je-suis-gpl.tgz \
                      --collection 'second-collection'



You just posted a deposit to your collection on Software Heritage


If everything went well, the successful response will contain the
elements below:

.. code:: shell

  {
    'deposit_status': 'deposited',
    'deposit_id': '7',
    'deposit_date': 'Jan. 29, 2018, 12:29 p.m.'
  }

Note: As the deposit is in ``deposited`` status, you can no longer
update the deposit after this query. It will be answered with a 403
forbidden answer.

If something went wrong, an equivalent response will be given with the
`error` and `detail` keys explaining the issue, e.g.:

.. code:: shell

  {
    'error': 'Unknown collection name xyz',
    'detail': None,
    'deposit_status': None,
    'deposit_status_detail': None,
    'deposit_swh_id': None,
    'status': 404
  }



multisteps deposit
^^^^^^^^^^^^^^^^^^^^^^^^^
The steps to create a multisteps deposit:

1. Create an incomplete deposit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
First use the ``--partial`` argument to declare there is more to come

.. code:: shell

  $ swh deposit upload --username name --password secret \
                       --archive foo.tar.gz \
                       --partial


2. Add content or metadata to the deposit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Continue the deposit by using the ``--deposit-id`` argument given as a response
for the first step. You can continue adding content or metadata while you use
the ``--partial`` argument.

.. code:: shell

  $ swh deposit upload --username name --password secret \
                       --archive add-foo.tar.gz \
                       --deposit-id 42 \
                       --partial


In case you want to add only one new archive without metadata:

.. code:: shell

  $ swh deposit upload --username name --password secret \
                       --archive add-foo.tar.gz \
                       --archive-deposit \
                       --deposit-id 42 \
                       --partial

If you want to add only metadata, use:

.. code:: shell

  $ swh deposit upload --username name --password secret \
                       --metadata add-foo.tar.gz.metadata.xml \
                       --metadata-deposit \
                       --deposit-id 42 \
                       --partial

3. Finalize deposit
~~~~~~~~~~~~~~~~~~~
On your last addition, by not declaring it as ``--partial``, the
deposit will be considered as completed and its status will be changed
to ``deposited``:

.. code:: shell

  $ swh deposit upload --username name --password secret \
                       --metadata add-foo.tar.gz.metadata.xml \
                       --metadata-deposit \
                       --deposit-id 42


Update deposit
----------------
* replace deposit:

  - only possible if the deposit status is ``partial`` and
    ``--deposit-id <id>`` is provided

  - by using the ``--replace`` flag

    - ``--metadata-deposit`` replaces associated existing metadata
    - ``--archive-deposit`` replaces associated archive(s)
    - by default, with no flag or both, you'll replace associated
      metadata and archive(s):

.. code:: shell

  $ swh deposit upload --username name --password secret \
                       --deposit-id 11 \
                       --archive updated-je-suis-gpl.tgz \
                       --replace

* update a loaded deposit with a new version:

  - by using the external-id with the ``--slug`` argument, you will
    link the new deposit with its parent deposit:

.. code:: shell

  $ swh deposit upload --username name --password secret \
                       --archive je-suis-gpl-v2.tgz \
                       --slug 'je-suis-gpl' \



Check the deposit's status
--------------------------

You can check the status of the deposit by using the ``--deposit-id`` argument:

.. code:: shell

  $ swh deposit upload --username name --password secret \
                       --deposit-id 11 \
                       --status

.. code:: json

  {
    'deposit_id': '11',
    'deposit_status': 'deposited',
    'deposit_swh_id': None,
    'deposit_status_detail': 'Deposit is ready for additional checks \
                              (tarball ok, metadata, etc...)'
  }

The different statuses:

- **partial**: multipart deposit is still ongoing
- **deposited**: deposit completed
- **rejected**: deposit failed the checks
- **verified**: content and metadata verified
- **loading**: loading in-progress
- **done**: loading completed successfully
- **failed**: the deposit loading has failed

When the deposit has been loaded into the archive, the status will be
marked ``done``. In the response, will also be available the
<deposit_swh_id>, <deposit_swh_id_context>, <deposit_swh_anchor_id>,
<deposit_swh_anchor_id_context>. For example:

.. code:: json

 {
  'deposit_id': '11',
  'deposit_status': 'done',
  'deposit_swh_id': 'swh:1:dir:d83b7dda887dc790f7207608474650d4344b8df9',
  'deposit_swh_id_context': 'swh:1:dir:d83b7dda887dc790f7207608474650d4344b8df9;origin=https://forge.softwareheritage.org/source/jesuisgpl/',
  'deposit_swh_anchor_id': 'swh:1:rev:e76ea49c9ffbb7f73611087ba6e999b19e5d71eb',
  'deposit_swh_anchor_id_context': 'swh:1:rev:e76ea49c9ffbb7f73611087ba6e999b19e5d71eb;origin=https://forge.softwareheritage.org/source/jesuisgpl/',
  'deposit_status_detail': 'The deposit has been successfully \
                            loaded into the Software Heritage archive'
 }
