.. _swh-loading-specs:

Loading specification
=====================

An important part of the deposit specifications is the loading procedure where
a deposit is ingested into the Software Heritage Archive (SWH) using
the deposit loader and the complete process of software artifacts creation
in the archive.

Deposit Loading
---------------

The ``swh.loader.package.deposit`` module is able to inject zipfile/tarball's
content in SWH with its metadata.

The loading of the deposit will use the deposit's associated data:

* the metadata
* the archive file(s)


Artifacts creation
------------------

Deposit to artifacts mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a global view of the deposit ingestion

+------------------------------------+-----------------------------------------+
| swh artifact                       | representation in deposit               |
+====================================+=========================================+
| origin                             | https://hal.inria.fr/hal-id             |
+------------------------------------+-----------------------------------------+
| raw_extrinsic_metadata             | aggregated metadata                     |
+------------------------------------+-----------------------------------------+
| snapshot                           | reception of all occurrences (branches) |
+------------------------------------+-----------------------------------------+
| branches                           | master & tags for releases              |
|                                    | (not yet implemented)                   |
+------------------------------------+-----------------------------------------+
| release                            | (optional) synthetic release created    |
|                                    | from metadata (not yet implemented)     |
+------------------------------------+-----------------------------------------+
| revision                           | synthetic revision pointing to          |
|                                    | the directory (see below)               |
+------------------------------------+-----------------------------------------+
| directory                          | root directory of the expanded submitted|
|                                    | tarball                                 |
+------------------------------------+-----------------------------------------+


Origin artifact
~~~~~~~~~~~~~~~

If the ``<swh:create_origin>`` is missing,
we create an origin URL by concatenating the client's `provider_url` and the
value of the Slug header of the initial POST request of the deposit
(or a randomly generated slug if it is missing).

For examples:

.. code-block:: bash

    $ http -pb https://archive.softwareheritage.org/api/1/origin/https://hal.archives-ouvertes.fr/hal-01883795/get/

would result in:

.. code-block:: json

    {
        "url": "https://hal.archives-ouvertes.fr/hal-01883795",
        "origin_visits_url": "https://archive.softwareheritage.org/api/1/origin/https://hal.archives-ouvertes.fr/hal-01883795/visits/",
        "metadata_authorities_url": "https://archive.softwareheritage.org/api/1/raw-extrinsic-metadata/swhid/swh:1:ori:0094225e66277f3b2de66155b3cb30ca25f12565/authorities/"
    }


Visits
~~~~~~

We identify with a visit each deposit push of the same origin.
Here in the example below, two snapshots are identified by two different visits.

For examples:

.. code-block:: bash

	$ http -pb https://archive.softwareheritage.org/api/1/origin/https://hal.archives-ouvertes.fr/hal-01883795/visits/

would result in:

.. code-block:: json

    [
        {
            "date": "2023-03-29T12:12:08.960810+00:00",
            "metadata": {},
            "origin": "https://hal.archives-ouvertes.fr/hal-01883795",
            "origin_visit_url": "https://archive.softwareheritage.org/api/1/origin/https://hal.archives-ouvertes.fr/hal-01883795/visit/2/",
            "snapshot": "e59379a4f88c297066e964703893c23b08264ec8",
            "snapshot_url": "https://archive.softwareheritage.org/api/1/snapshot/e59379a4f88c297066e964703893c23b08264ec8/",
            "status": "full",
            "type": "deposit",
            "visit": 2
        },
        {
            "date": "2019-01-10T12:30:26.326411+00:00",
            "metadata": {},
            "origin": "https://hal.archives-ouvertes.fr/hal-01883795",
            "origin_visit_url": "https://archive.softwareheritage.org/api/1/origin/https://hal.archives-ouvertes.fr/hal-01883795/visit/1/",
            "snapshot": "fd1b8fc1bdd3ebeac913eb6dd377a646a3149747",
            "snapshot_url": "https://archive.softwareheritage.org/api/1/snapshot/fd1b8fc1bdd3ebeac913eb6dd377a646a3149747/",
            "status": "full",
            "type": "deposit",
            "visit": 1
        }
    ]

Snapshot artifact
~~~~~~~~~~~~~~~~~

The snapshot represents one deposit push. The ``HEAD`` branch points to a
synthetic revision.

For example:

.. code-block:: bash

	$ http -pb https://archive.softwareheritage.org/api/1/snapshot/e59379a4f88c297066e964703893c23b08264ec8/

would result in:

.. code-block:: json

    {
        "branches": {
            "HEAD": {
                "target": "fc8e44c5bb3fabe81e5ebe46ac013a2510271616",
                "target_type": "release",
                "target_url": "https://archive.softwareheritage.org/api/1/release/fc8e44c5bb3fabe81e5ebe46ac013a2510271616/"
            }
        },
        "id": "e59379a4f88c297066e964703893c23b08264ec8",
        "next_branch": null
    }


Note that previous versions of the deposit-loader created a release instead of a revision.
For example:


.. code-block:: bash

    http -pb https://archive.softwareheritage.org/api/1/snapshot/fd1b8fc1bdd3ebeac913eb6dd377a646a3149747/

resulted in:

.. code-block:: json

    {
        "branches": {
            "master": {
                "target": "66ff08f00acc06131fe610be0f9878a6c78bfe44",
                "target_type": "revision",
                "target_url": "https://archive.softwareheritage.org/api/1/revision/66ff08f00acc06131fe610be0f9878a6c78bfe44/"
            }
        },
        "id": "fd1b8fc1bdd3ebeac913eb6dd377a646a3149747",
        "next_branch": null
    }

Even older versions named the branch ``master`` instead of ``HEAD``, and created
release branches (pointing to revisions) under certain conditions.

Release artifact
~~~~~~~~~~~~~~~~

The content is deposited with a set of descriptive metadata in the CodeMeta
vocabulary. The following CodeMeta terms implies that the
artifact is a release:

- ``releaseNotes``
- ``softwareVersion``

If present, a release artifact will be created with the mapping below:

+-------------------+-----------------------------------+-----------------+----------------+
| SWH release field | Description                       | CodeMeta term   | Fallback value |
+===================+===================================+=================+================+
| target            | directory containing all metadata | X               |X               |
+-------------------+-----------------------------------+-----------------+----------------+
| target_type       | directory                         | X               |X               |
+-------------------+-----------------------------------+-----------------+----------------+
| name              | release or tag name (mandatory)   | softwareVersion | X              |
+-------------------+-----------------------------------+-----------------+----------------+
| message           | message associated with release   | releaseNotes    | X              |
+-------------------+-----------------------------------+-----------------+----------------+
| date              | release date = publication date   | datePublished   | deposit_date   |
+-------------------+-----------------------------------+-----------------+----------------+
| author            | deposit client                    | author          | X              |
+-------------------+-----------------------------------+-----------------+----------------+


.. code-block:: bash

    http -pb https://archive.softwareheritage.org/api/1/release/fc8e44c5bb3fabe81e5ebe46ac013a2510271616/

.. code-block:: json

    {
        "author": {
            "email": "robot@softwareheritage.org",
            "fullname": "Software Heritage",
            "name": "Software Heritage"
        },
        "date": "2021-01-01T00:00:00+00:00",
        "id": "fc8e44c5bb3fabe81e5ebe46ac013a2510271616",
        "message": "hal: Deposit 2753 in collection hal\n\n- Replace qmake with CMake.- Fix bugs.- Move repository.\n",
        "name": "HEAD",
        "synthetic": true,
        "target": "7057a716afab8ca80728aa7c6c2cc4bd03b0f45b",
        "target_type": "directory",
        "target_url": "https://archive.softwareheritage.org/api/1/directory/7057a716afab8ca80728aa7c6c2cc4bd03b0f45b/"
    }


Revision artifact
~~~~~~~~~~~~~~~~~

.. note::

   Revision artifacts are no longer created by the deposit.

The metadata sent with the deposit is stored outside the revision,
and does not affect the hash computation.
It contains the same fields as any revision object; in particular:

+-------------------+-----------------------------------------+
| SWH revision field| Description                             |
+===================+=========================================+
| message           | synthetic message, containing the name  |
|                   | of the deposit client and an internal   |
|                   | identifier of the deposit. For example: |
|                   | ``hal: Deposit 817 in collection hal``  |
+-------------------+-----------------------------------------+
| author            | synthetic author (SWH itself, for now)  |
+-------------------+-----------------------------------------+
| committer         | same as the author (for now)            |
+-------------------+-----------------------------------------+
| date              | see below                               |
+-------------------+-----------------------------------------+
| committer_date    | see below                               |
+-------------------+-----------------------------------------+

.. code-block:: bash

    http -pb https://archive.softwareheritage.org/api/1/revision/66ff08f00acc06131fe610be0f9878a6c78bfe44/

.. code-block:: json

    {
        "author": {
            "email": "robot@softwareheritage.org",
            "fullname": "Software Heritage",
            "name": "Software Heritage"
        },
        "committer": {
            "email": "robot@softwareheritage.org",
            "fullname": "Software Heritage",
            "name": "Software Heritage"
        },
        "committer_date": "2019-01-10T12:27:59.639536+00:00",
        "date": "2019-01-10T12:27:59.639536+00:00",
        "directory": "70c73de7d406938315d6cf30bf87bb9eb480017e",
        "directory_url": "https://archive.softwareheritage.org/api/1/directory/70c73de7d406938315d6cf30bf87bb9eb480017e/",
        "extra_headers": [],
        "history_url": "https://archive.softwareheritage.org/api/1/revision/66ff08f00acc06131fe610be0f9878a6c78bfe44/log/",
        "id": "66ff08f00acc06131fe610be0f9878a6c78bfe44",
        "merge": false,
        "message": "hal: Deposit 225 in collection hal",
        "metadata": {
            "@xmlns": "http://www.w3.org/2005/Atom",
            "@xmlns:codemeta": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0",
            "author": {
                "email": "hal@ccsd.cnrs.fr",
                "name": "HAL"
            },
            "client": "hal",
            "codemeta:applicationCategory": "sdu.ocean",
            "codemeta:author": {
                "codemeta:affiliation": "LaMP",
                "codemeta:name": "D. Picard"
            },
            "codemeta:codeRepository": "https://forge.clermont-universite.fr/git/libszdist",
            "codemeta:dateCreated": "2018-09-28T16:58:05+02:00",
            "codemeta:description": "libszdist is a C++ library and command line tools that implement the algorithm used to process the data of instruments called SMPS/DMPS. These instruments measure the size distribution of aerosol particles. The algorithm is known as ''inversion''.",
            "codemeta:developmentStatus": "Actif",
            "codemeta:keywords": "SMPS,DMPS,Aerosol Size Distribution",
            "codemeta:license": {
                "codemeta:name": "GNU GPLv3"
            },
            "codemeta:name": "libszdist",
            "codemeta:operatingSystem": [
                "Linux",
                "Windows",
                "Mac OS X",
                "ARM"
            ],
            "codemeta:programmingLanguage": "C++",
            "codemeta:runtimePlatform": [
                "qmake",
                "gcc"
            ],
            "codemeta:softwareVersion": "v.0.10.4",
            "codemeta:url": "https://hal.archives-ouvertes.fr/hal-01883795",
            "codemeta:version": "1",
            "committer": "David Picard",
            "id": "hal-01883795"
        },
        "parents": [],
        "synthetic": true,
        "type": "tar",
        "url": "https://archive.softwareheritage.org/api/1/revision/66ff08f00acc06131fe610be0f9878a6c78bfe44/"
    }

Note that the metadata field is deprecated. The "extrinsic metadata" endpoints described
below should be used instead.

The date mapping
^^^^^^^^^^^^^^^^

A deposit may contain 4 different dates concerning the software artifacts.

The deposit's revision will reflect the most accurate point in time available.
Here are all dates that can be available in a deposit:

+----------------+---------------------------------+------------------------------------------------+
| dates          | location                        | Description                                    |
+================+=================================+================================================+
| reception_date | On SWORD reception (automatic)  | the deposit was received at this ts            |
+----------------+---------------------------------+------------------------------------------------+
| complete_date  | On SWH ingestion  (automatic)   | the ingestion was completed by SWH at this ts  |
+----------------+---------------------------------+------------------------------------------------+
| dateCreated    | metadata in codeMeta (optional) | the software artifact was created at this ts   |
+----------------+---------------------------------+------------------------------------------------+
| datePublished  | metadata in codeMeta (optional) | the software was published (contributed in HAL)|
+----------------+---------------------------------+------------------------------------------------+

A visit targeting a snapshot contains one date:

+-------------------+----------------------------------------------+----------------+
| SWH visit field   | Description                                  |  value         |
+===================+==============================================+================+
| date              | the origin pushed the deposit at this date   | reception_date |
+-------------------+----------------------------------------------+----------------+

A revision contains two dates:

+-------------------+-----------------------------------------+----------------+----------------+
| SWH revision field| Description                             | CodeMeta term  | Fallback value |
+===================+=========================================+================+================+
| date              | date of software artifact modification  | dateCreated    | reception_date |
+-------------------+-----------------------------------------+----------------+----------------+
| committer_date    | date of the commit in VCS               | datePublished  | reception_date |
+-------------------+-----------------------------------------+----------------+----------------+


A release contains one date:

+-------------------+----------------------------------+----------------+-----------------+
| SWH release field |Description                       | CodeMeta term  | Fallback value  |
+===================+==================================+================+=================+
| date              |release date = publication date   | datePublished  | reception_date  |
+-------------------+----------------------------------+----------------+-----------------+

Directory artifact
~~~~~~~~~~~~~~~~~~

The directory artifact is the archive(s)' raw content deposited.

.. code-block:: bash

    http -pb https://archive.softwareheritage.org/api/1/directory/7057a716afab8ca80728aa7c6c2cc4bd03b0f45b/

.. code-block:: json

    [
        {
            "checksums": {
                "sha1": "cadfc0e77c0119a025a5ed45d07f71df4071f645",
                "sha1_git": "b89214f14acaca84efb65ff6542cb5d790b6ac5c",
                "sha256": "47c165ad20425a13f65ebd9db61447363bb9cf3ce0b0fa4418d9cfc951f157e3"
            },
            "dir_id": "7057a716afab8ca80728aa7c6c2cc4bd03b0f45b",
            "length": 150,
            "name": ".gitignore",
            "perms": 33188,
            "status": "visible",
            "target": "b89214f14acaca84efb65ff6542cb5d790b6ac5c",
            "target_url": "https://archive.softwareheritage.org/api/1/content/sha1_git:b89214f14acaca84efb65ff6542cb5d790b6ac5c/",
            "type": "file"
        },
        {
            "checksums": {
                "sha1": "816fde05704e5b7c8a744044949b9f7944702993",
                "sha1_git": "de6f1f373a44be2b16232b2ff9744f31fe7e3715",
                "sha256": "09585c721573beadc56a98754745f9381c15626f6471b7da18475366e4e8f2cb"
            },
            "dir_id": "7057a716afab8ca80728aa7c6c2cc4bd03b0f45b",
            "length": 51,
            "name": "AUTHORS",
            "perms": 33188,
            "status": "visible",
            "target": "de6f1f373a44be2b16232b2ff9744f31fe7e3715",
            "target_url": "https://archive.softwareheritage.org/api/1/content/sha1_git:de6f1f373a44be2b16232b2ff9744f31fe7e3715/",
            "type": "file"
        }
    ]

Questions raised concerning loading
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- A deposit has one origin, yet an origin can have multiple deposits?

No, an origin can have multiple requests for the same deposit. Which
should end up in one single deposit (when the client pushes its final
request saying deposit 'done' through the header In-Progress).

Only update of existing 'partial' deposit is permitted. Other than that,
the deposit 'update' operation.

To create a new version of a software (already deposited), the client
must prior to this create a new deposit.

Illustration First deposit loading:

HAL's deposit 01535619 = SWH's deposit **01535619-1**

::

    + 1 origin with url:https://hal.inria.fr/medihal-01535619

    + 1 synthetic revision

    + 1 directory

HAL's update on deposit 01535619 = SWH's deposit **01535619-2**

(\*with HAL updates can only be on the metadata and a new version is
required if the content changes)

::

    + 1 origin with url:https://hal.inria.fr/medihal-01535619

    + new synthetic revision (with new metadata)

    + same directory

HAL's deposit 01535619-v2 = SWH's deposit **01535619-v2-1**

::

    + same origin

    + new revision

    + new directory


Scheduling loading
~~~~~~~~~~~~~~~~~~

All ``archive`` and ``metadata`` deposit requests should be aggregated before
loading.

The loading should be scheduled via the scheduler's api.

Only ``deposited`` deposit are concerned by the loading.

When the loading is done and successful, the deposit entry is updated:

  - ``status`` is updated to ``done``
  - ``swh-id`` is populated with the resulting :ref:`SWHID
    <persistent-identifiers>`
  - ``complete_date`` is updated to the loading's finished time

When the loading has failed, the deposit entry is updated:
  - ``status`` is updated to ``failed``
  - ``swh-id`` and ``complete_data`` remains as is

*Note:* As a further improvement, we may prefer having a retry policy with
graceful delays for further scheduling.

Metadata loading
~~~~~~~~~~~~~~~~

- the metadata received with the deposit are kept in a dedicated table
  ``raw_extrinsic_metadata``, distinct from the ``revision`` and ``origin``
  tables.

- ``authority`` is computed from the deposit client information, and ``fetcher``
  is the deposit loader.

They can be queried using the directory SWHID.

First, we need to get the list of authorities which published metadata on this directory:

.. code-block:: bash

    http -pb https://archive.softwareheritage.org/api/1/raw-extrinsic-metadata/swhid/swh:1:dir:7057a716afab8ca80728aa7c6c2cc4bd03b0f45b/authorities/

.. code-block:: json

    [
        {
            "metadata_list_url": "https://archive.softwareheritage.org/api/1/raw-extrinsic-metadata/swhid/swh:1:dir:7057a716afab8ca80728aa7c6c2cc4bd03b0f45b/?authority=deposit_client%20https://hal.archives-ouvertes.fr/",
            "type": "deposit_client",
            "url": "https://hal.archives-ouvertes.fr/"
        },
        {
            "metadata_list_url": "https://archive.softwareheritage.org/api/1/raw-extrinsic-metadata/swhid/swh:1:dir:7057a716afab8ca80728aa7c6c2cc4bd03b0f45b/?authority=registry%20https://softwareheritage.org/",
            "type": "registry",
            "url": "https://softwareheritage.org/"
        }
    ]

The former is HAL, the latter is Software Heritage itself (to provide attestation of tarball checksums).
We can get the list of metadata provided by HAL:


.. code-block:: bash

    http -pb https://archive.softwareheritage.org/api/1/raw-extrinsic-metadata/swhid/swh:1:dir:7057a716afab8ca80728aa7c6c2cc4bd03b0f45b/\?authority\=deposit_client%20https://hal.archives-ouvertes.fr/

.. code-block:: json

    [
        {
            "authority": {
                "type": "deposit_client",
                "url": "https://hal.archives-ouvertes.fr/"
            },
            "discovery_date": "2023-03-29T12:11:53+00:00",
            "fetcher": {
                "name": "swh-deposit",
                "version": "1.1.0"
            },
            "format": "sword-v2-atom-codemeta-v2",
            "metadata_url": "https://archive.softwareheritage.org/api/1/raw-extrinsic-metadata/get/c65992f8f3efe416ccf2666f8ff09753ea94377d/?filename=swh:1:dir:7057a716afab8ca80728aa7c6c2cc4bd03b0f45b_metadata",
            "origin": "https://hal.archives-ouvertes.fr/hal-01883795",
            "release": "swh:1:rel:fc8e44c5bb3fabe81e5ebe46ac013a2510271616",
            "target": "swh:1:dir:7057a716afab8ca80728aa7c6c2cc4bd03b0f45b"
        }
    ]

and finally, we got the URL to the metadata blob itself:

.. code-block:: bash

    http -pb https://archive.softwareheritage.org/api/1/raw-extrinsic-metadata/get/c65992f8f3efe416ccf2666f8ff09753ea94377d/\?filename\=swh:1:dir:7057a716afab8ca80728aa7c6c2cc4bd03b0f45b_metadata

.. code-block:: xml

    <?xml version="1.0" encoding="utf-8"?>
    <entry xmlns="http://www.w3.org/2005/Atom" xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0" xmlns:schema="http://schema.org/" xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit">
      <id>hal-01883795</id>
      <swh:deposit>
        <swh:create_origin>
          <swh:origin url="https://hal.archives-ouvertes.fr/hal-01883795"/>
        </swh:create_origin>
        <swh:metadata-provenance>
          <schema:url>https://hal.archives-ouvertes.fr/hal-01883795</schema:url>
        </swh:metadata-provenance>
      </swh:deposit>
      <author>
        <name>HAL</name>
        <email>hal@ccsd.cnrs.fr</email>
      </author>
      <codemeta:name>libszdist</codemeta:name>
      <codemeta:description>libszdist is a C++ library and command line tools that implement the algorithm used to process the data of instruments called SMPS/DMPS. These instruments measure the size distribution of aerosol particles. The algorithm is known as ''inversion''.</codemeta:description>
      <codemeta:dateCreated>2021-01-01</codemeta:dateCreated>
      <codemeta:datePublished>2023-03-16</codemeta:datePublished>
      <codemeta:license>
        <codemeta:name>GNU GPLv3</codemeta:name>
      </codemeta:license>
      <schema:identifier>
        <codemeta:type>schema:PropertyValue</codemeta:type>
        <schema:propertyID>HAL-ID</schema:propertyID>
        <schema:value>hal-01883795</schema:value>
      </schema:identifier>
      <codemeta:applicationCategory>sdu.ocean</codemeta:applicationCategory>
      <codemeta:keywords>SMPS,DMPS,Aerosol Size Distribution,MPSS</codemeta:keywords>
      <codemeta:institution>CNRS</codemeta:institution>
      <codemeta:codeRepository>https://forge.clermont-universite.fr/git/libszdist</codemeta:codeRepository>
      <codemeta:relatedLink>https://gitlab.in2p3.fr/david.picard/libszdist</codemeta:relatedLink>
      <codemeta:programmingLanguage>C++</codemeta:programmingLanguage>
      <codemeta:runtimePlatform>gcc</codemeta:runtimePlatform>
      <codemeta:runtimePlatform>CMake</codemeta:runtimePlatform>
      <codemeta:operatingSystem>Linux</codemeta:operatingSystem>
      <codemeta:operatingSystem>Windows</codemeta:operatingSystem>
      <codemeta:operatingSystem>Mac OS X</codemeta:operatingSystem>
      <codemeta:operatingSystem>ARM</codemeta:operatingSystem>
      <codemeta:operatingSystem>PC</codemeta:operatingSystem>
      <codemeta:version>2</codemeta:version>
      <codemeta:softwareVersion>v.0.11.1</codemeta:softwareVersion>
      <codemeta:dateModified>2023-03-24</codemeta:dateModified>
      <codemeta:releaseNotes>- Replace qmake with CMake.- Fix bugs.- Move repository.</codemeta:releaseNotes>
      <codemeta:developmentStatus>Actif</codemeta:developmentStatus>
      <codemeta:author>
        <codemeta:name>D. Picard</codemeta:name>
        <codemeta:affiliation>LPC</codemeta:affiliation>
        <codemeta:affiliation>LaMP</codemeta:affiliation>
      </codemeta:author>
      <codemeta:contributor>
        <codemeta:name>David PICARD</codemeta:name>
      </codemeta:contributor>
    </entry>

which is the exact document provided by HAL when uploading the deposit.
