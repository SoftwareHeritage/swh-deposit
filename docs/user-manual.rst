.. _user-manual:

User Manual
===========

This is a guide for how to prepare and push a software deposit with
the `swh deposit` commands.


Requirements
------------

You need to have an account on the Software Heritage deposit application to be
able to use the service.

Please `contact the Software Heritage team <deposit@softwareheritage.org>`_ for
more information on how to get access to this service.

For testing purpose, a test instance `is available
<https://deposit.staging.swh.network>`_ [#f1]_ and will be used in the examples below.

Once you have an account, you should get a set of access credentials as a
`login` and a `password` (identified as ``<name>`` and ``<pass>`` in the
remaining of this document). A deposit account also comes with a "provider URL"
which is used by SWH to build the :term:`Origin URL<origin>` of deposits
created using this account.


Installation
------------

To install the `swh.deposit` command line tools, you need a working Python 3.7+
environment. It is strongly recommended you use a `virtualenv
<https://virtualenv.pypa.io/en/stable/>`_ for this.

.. code:: console

   $ python3 -m virtualenv deposit
   [...]
   $ source deposit/bin/activate
   (deposit)$ pip install swh.deposit
   [...]
   (deposit)$ swh deposit --help
   Usage: swh deposit [OPTIONS] COMMAND [ARGS]...

     Deposit main command

   Options:
     -h, --help  Show this message and exit.

   Commands:
     admin   Server administration tasks (manipulate user or...
     status  Deposit's status
     upload  Software Heritage Public Deposit Client Create/Update...
   (deposit)$

Note: in the examples below, we use the `jq`_ tool to make json outputs nicer.
If you do have it already, you may install it using your distribution's
packaging system. For example, on a Debian system:

.. _jq: https://stedolan.github.io/jq/

.. code:: console

   $ sudo apt install jq


Prepare a deposit
-----------------

* compress the files in a supported archive format:

  - zip: common zip archive (no multi-disk zip files).
  - tar: tar archive without compression or optionally any of the
         following compression algorithm gzip (`.tar.gz`, `.tgz`), bzip2
         (`.tar.bz2`) , or lzma (`.tar.lzma`)

* (Optional) prepare a metadata file (more details :ref:`deposit-metadata`):

Example:

Assuming you want to deposit the source code of `belenios
<https://gitlab.inria.fr/belenios/belenios>`_ version 1.12

.. code:: console

   (deposit)$ wget https://gitlab.inria.fr/belenios/belenios/-/archive/1.12/belenios-1.12.zip
   [...]
   2020-10-28 11:40:37 (4,56 MB/s) - ‘belenios-1.12.zip’ saved [449880/449880]
   (deposit)$

Then you need to prepare a metadata file allowing you to give detailed
information on your deposited source code. A rather minimal Atom with Codemeta
file could be:

.. code:: console

   (deposit)$ cat metadata.xml
   <?xml version="1.0" encoding="utf-8"?>
   <entry xmlns="http://www.w3.org/2005/Atom"
   xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
     <title>Verifiable online voting system</title>
     <client>belenios</client>
     <id>belenios-01243065</id>
     <external_identifier>test-01243065</external_identifier>
     <codemeta:url>https://gitlab.inria.fr/belenios/belenios</codemeta:url>
     <codemeta:applicationCategory>test</codemeta:applicationCategory>
     <codemeta:keywords>Online voting</codemeta:keywords>
     <codemeta:description>Verifiable online voting system</codemeta:description>
     <codemeta:version>1.12</codemeta:version>
     <codemeta:runtimePlatform>opam</codemeta:runtimePlatform>
     <codemeta:developmentStatus>stable</codemeta:developmentStatus>
     <codemeta:programmingLanguage>ocaml</codemeta:programmingLanguage>
     <codemeta:license>
       <codemeta:name>GNU Affero General Public License</codemeta:name>
     </codemeta:license>
     <author>
       <name>Belenios</name>
       <email>belenios@example.com</email>
     </author>
     <codemeta:author>
       <codemeta:name>Belenios Test User</codemeta:name>
     </codemeta:author>
   </entry>

   (deposit)$

Please read the :ref:`deposit-metadata` page for a more detailed view on the
metadata file formats and semantics.


Push a deposit
--------------

You can push a deposit with:

* a single deposit (archive + metadata):

  The user posts in one query a software
  source code archive and associated metadata.
  The deposit is directly marked with status ``deposited``.

* a multisteps deposit:

  1. Create an incomplete deposit (marked with status ``partial``)
  2. Add data to a deposit (in multiple requests if needed)
  3. Finalize deposit (the status becomes ``deposited``)


Overall, a deposit can be a in series of steps as follow:

.. figure:: images/status.svg
   :alt:

The important things to notice for now is that it can be:

partial:
  the deposit is partially received

expired:
  deposit has been there too long and is now deemed
  ready to be garbage collected

deposited:
  deposit is complete and is ready to be checked to ensure data consistency

verified:
  deposit is fully received, checked, and ready for loading

loading:
  loading is ongoing on swh's side

done:
  loading is successful

failed:
  loading is a failure


When you push a deposit, it is either in the `deposited` state or in the
`partial` state if you asked for a partial upload.



Single deposit
^^^^^^^^^^^^^^

Once the files are ready for deposit, we want to do the actual deposit in one
shot, i.e. sending both the archive (zip) file and the metadata file.

* 1 archive (content-type ``application/zip`` or ``application/x-tar``)
* 1 metadata file in atom xml format (``content-type: application/atom+xml;type=entry``)

For this, we need to provide the:

* arguments: ``--username 'name' --password 'pass'`` as credentials
* archive's path (example: ``--archive path/to/archive-name.tgz``)
* metadata file path (example: ``--metadata path/to/metadata.xml``)

to the `swh deposit upload` command.



Example:

To push the Belenios 1.12 we prepared previously on the testing instance of the
deposit:

.. code:: console

   (deposit)$ ls
   belenios-1.12.zip  metadata.xml deposit
   (deposit)$ swh deposit upload --username <name> --password <secret> \
                  --url https://deposit.staging.swh.network/1 \
                  --slug belenios-01243065 \
                  --archive belenios.zip \
                  --metadata metadata.xml \
                  --format json | jq
   {
     'deposit_status': 'deposited',
     'deposit_id': '1',
     'deposit_date': 'Oct. 28, 2020, 1:52 p.m.',
     'deposit_status_detail': None
   }

   (deposit)$


You just posted a deposit to your main collection on Software Heritage (staging
area)!

The returned value is a JSON dict, in which you will notably find the deposit
id (needed to check for its status later on) and the current status, which
should be `deposited` if no error has occurred.

Note: As the deposit is in ``deposited`` status, you can no longer
update the deposit after this query. It will be answered with a 403
(Forbidden) answer.

If something went wrong, an equivalent response will be given with the
`error` and `detail` keys explaining the issue, e.g.:

.. code:: console

   {
     'error': 'Unknown collection name xyz',
     'detail': None,
     'deposit_status': None,
     'deposit_status_detail': None,
     'deposit_swh_id': None,
     'status': 404
   }


Once the deposit has been done, you can check its status using the `swh deposit
status` command:

.. code:: console

   (deposit)$ swh deposit status --username <name> --password <secret> \
                  --url https://deposit.staging.swh.network/1 \
                  --deposit-id 1 -f json | jq
   {
     "deposit_id": "1",
     "deposit_status": "done",
     "deposit_status_detail": "The deposit has been successfully loaded into the Software Heritage archive",
     "deposit_swh_id": "swh:1:dir:63a6fc0ed8f69bf66ccbf99fc0472e30ef0a895a",
     "deposit_swh_id_context": "swh:1:dir:63a6fc0ed8f69bf66ccbf99fc0472e30ef0a895a;origin=https://softwareheritage.org/belenios-01234065;visit=swh:1:snp:0ae536667689da7047bfb7aa9f37f5958e9f4647;anchor=swh:1:rev:17ad98c940104d45b6b6bd6fba9aa832eeb95638;path=/",
     "deposit_external_id": "belenios-01234065"
   }




Multisteps deposit
^^^^^^^^^^^^^^^^^^

In this case, the deposit is created by several requests, uploading objects
piece by piece. The steps to create a multisteps deposit:

1. Create an partial deposit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First use the ``--partial`` argument to declare there is more to come

.. code:: console

   $ swh deposit upload --username name --password secret \
                        --archive foo.tar.gz \
                        --partial


2. Add content or metadata to the deposit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Continue the deposit by using the ``--deposit-id`` argument given as a response
for the first step. You can continue adding content or metadata while you use
the ``--partial`` argument.

To only add one new archive to the deposit:

.. code:: console

   $ swh deposit upload --username name --password secret \
                        --archive add-foo.tar.gz \
                        --deposit-id 42 \
                        --partial

To only add metadata to the deposit:

.. code:: console

   $ swh deposit upload --username name --password secret \
                        --metadata add-foo.tar.gz.metadata.xml \
                        --deposit-id 42 \
                        --partial


3. Finalize deposit
~~~~~~~~~~~~~~~~~~~

On your last addition (same command as before), by not declaring it
``--partial``, the deposit will be considered completed. Its status will be
changed to ``deposited``:

.. code:: console

   $ swh deposit upload --username name --password secret \
                        --metadata add-foo.tar.gz.metadata.xml \
                        --deposit-id 42


Update deposit
--------------

* replace deposit:

  - only possible if the deposit status is ``partial`` and
    ``--deposit-id <id>`` is provided

  - by using the ``--replace`` flag

    - ``--metadata-deposit`` replaces associated existing metadata
    - ``--archive-deposit`` replaces associated archive(s)
    - by default, with no flag or both, you'll replace associated
      metadata and archive(s):

.. code:: console

   $ swh deposit upload --username name --password secret \
                        --deposit-id 11 \
                        --archive updated-je-suis-gpl.tgz \
                        --replace

* update a loaded deposit with a new version:

  - by using the external-id with the ``--slug`` argument, you will
    link the new deposit with its parent deposit:

.. code:: console

  $ swh deposit upload --username name --password secret \
                       --archive je-suis-gpl-v2.tgz \
                       --slug 'je-suis-gpl' \



Check the deposit's status
--------------------------

You can check the status of the deposit by using the ``--deposit-id`` argument:

.. code:: console

   $ swh deposit status --username name --password secret \
                        --deposit-id 11

.. code:: json

   {
     "deposit_id": 11,
     "deposit_status": "deposited",
     "deposit_swh_id": null,
     "deposit_status_detail": "Deposit is ready for additional checks \
                               (tarball ok, metadata, etc...)"
   }

When the deposit has been loaded into the archive, the status will be
marked ``done``. In the response, will also be available the
<deposit_swh_id>, <deposit_swh_id_context>. For example:

.. code:: json

   {
     "deposit_id": 11,
     "deposit_status": "done",
     "deposit_swh_id": "swh:1:dir:d83b7dda887dc790f7207608474650d4344b8df9",
     "deposit_swh_id_context": "swh:1:dir:d83b7dda887dc790f7207608474650d4344b8df9;\
	                            origin=https://forge.softwareheritage.org/source/jesuisgpl/;\
								visit=swh:1:snp:68c0d26104d47e278dd6be07ed61fafb561d0d20;\
								anchor=swh:1:rev:e76ea49c9ffbb7f73611087ba6e999b19e5d71eb;path=/",
     "deposit_status_detail": "The deposit has been successfully \
                               loaded into the Software Heritage archive"
   }



.. rubric:: Footnotes

.. [#f1] the test instance of the deposit is not yet available to external users,
         but it should be available soon.
