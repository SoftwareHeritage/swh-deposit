Loading specification
=====================

This part specifies the ingestion of the deposit in the SWH archive, using
the tarball loader and the complete schema of software artifacts creation
in the archive.

Tarball Loading
---------------

The ``swh-loader-tar`` module is already able to inject tarballs in swh
with very limited metadata (mainly the origin).

The loading of the deposit will use the deposit's associated data:

* the metadata
* the archive(s)


SWH artifacts creation
----------------------

Deposit to artifacts mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a global view of the deposit ingestion

+-----------------------------------+----------------------------------------+
|swh artifact                       | representation in deposit              |
+===================================+========================================+
|origin                             |      https://hal.inria.fr/hal-id       |
+-----------------------------------+----------------------------------------+
|origin_visit                       | 1 :reception_date                      |
+-----------------------------------+----------------------------------------+
|origin_metadata                    | aggregated metadata                    |
+-----------------------------------+----------------------------------------+
|snapshot                           | at visit of all occurences             |
+-----------------------------------+----------------------------------------+
|occurrence & occurrence_history    | branch: client's version n° (e.g hal)  |
+-----------------------------------+----------------------------------------+
|revision                           | synthetic_revision (tarball)           |
+-----------------------------------+----------------------------------------+
|directory                          | upper level of the uncompressed archive|
+-----------------------------------+----------------------------------------+


Origin artifact
~~~~~~~~~~~~~~~~
An origin using the url in the deposited metadata is created.
The current deposit and future deposits with the same url or external_id
will be associated with this origin.

.. code-block:: json

  {
    "id": 89283768,
    "origin_visits_url": "/api/1/origin/89283768/visits/",
    "type": "deposit",
    "url": "https://hal.archives-ouvertes.fr/hal-02140606"
  }

Visits
~~~~~~~
Each push of the same origin or external_id will generate a visit of the origin.
Here in the example below, two snapshots are identified by two different visits.

.. code-block:: json

  [
      {
          "date": "2019-06-03T09:28:10.223007+00:00",
          "origin": 89283768,
          "origin_visit_url": "/api/1/origin/89283768/visit/2/",
          "snapshot": "a3773941561cc557853898773a19c07cfe2efc5a",
          "snapshot_url": "/api/1/snapshot/a3773941561cc557853898773a19c07cfe2efc5a/",
          "status": "full",
          "type": "deposit",
          "visit": 2
      },
      {
          "date": "2019-05-27T12:23:31.037273+00:00",
          "origin": 89283768,
          "origin_visit_url": "/api/1/origin/89283768/visit/1/",
          "snapshot": "43fdb8291f1bf6962211c370e394f6abb1cbe01d",
          "snapshot_url": "/api/1/snapshot/43fdb8291f1bf6962211c370e394f6abb1cbe01d/",
          "status": "full",
          "type": "deposit",
          "visit": 1
      }
  ]

Snapshot artifact
~~~~~~~~~~~~~~~~
The snapshot represents one deposit push.

.. code-block:: json

  {
      "branches": {
          "master": {
              "target": "396b1ff29f7c75a0a3cc36f30e24ff7bae70bb52",
              "target_type": "revision",
              "target_url": "/api/1/revision/396b1ff29f7c75a0a3cc36f30e24ff7bae70bb52/"
          }
      },
      "id": "a3773941561cc557853898773a19c07cfe2efc5a",
      "next_branch": null
  }

Revision artifact
~~~~~~~~~~~~~~~~
A ``synthetic`` revision is created because the deposit is not a commit and
is created by the ``swh-loader-tar`` module.

The metadata sent with the deposit will be included in the revision and will
affect the hash computation, thus resulting in a unique identifier.
This way, by depositing the same content with different metadata will be two
different revisions in the archive.

.. code-block:: json

  {
    "author": {
        "email": "robot@softwareheritage.org",
        "fullname": "Software Heritage",
        "id": 18233048,
        "name": "Software Heritage"
    },
    "author_url": "/api/1/person/18233048/",
    "committer": {
        "email": "robot@softwareheritage.org",
        "fullname": "Software Heritage",
        "id": 18233048,
        "name": "Software Heritage"
    },
    "committer_date": "2019-05-27T16:28:33+02:00",
    "committer_url": "/api/1/person/18233048/",
    "date": "2012-01-01T00:00:00+00:00",
    "directory": "fb13b51abbcfd13de85d9ba8d070a23679576cd7",
    "directory_url": "/api/1/directory/fb13b51abbcfd13de85d9ba8d070a23679576cd7/",
    "history_url": "/api/1/revision/396b1ff29f7c75a0a3cc36f30e24ff7bae70bb52/log/",
    "id": "396b1ff29f7c75a0a3cc36f30e24ff7bae70bb52",
    "merge": false,
    "message": "hal: Deposit 282 in collection hal",
    "metadata": {
        "@xmlns": "http://www.w3.org/2005/Atom",
        "@xmlns:codemeta": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0",
        "author": {
            "email": "hal@ccsd.cnrs.fr",
            "name": "HAL"
        },
        "client": "hal",
        "codemeta:applicationCategory": "info",
        "codemeta:author": {
            "codemeta:name": "Morane Gruenpeter"
        },
        "codemeta:codeRepository": "www.code-repository.com",
        "codemeta:contributor": "Morane Gruenpeter",
        "codemeta:dateCreated": "2012",
        "codemeta:datePublished": "2019-05-27T16:28:33+02:00",
        "codemeta:description": "description\\_en test v2",
        "codemeta:developmentStatus": "Inactif",
        "codemeta:keywords": "mot_cle_en,mot_cle_2_en,mot_cle_fr",
        "codemeta:license": [
            {
                "codemeta:name": "MIT License"
            },
            {
                "codemeta:name": "CeCILL Free Software License Agreement v1.1"
            }
        ],
        "codemeta:name": "Test\\_20190527\\_01",
        "codemeta:operatingSystem": "OS",
        "codemeta:programmingLanguage": "Java",
        "codemeta:referencePublication": null,
        "codemeta:relatedLink": null,
        "codemeta:releaseNotes": "releaseNote",
        "codemeta:runtimePlatform": "outil",
        "codemeta:softwareVersion": "1.0.1",
        "codemeta:url": "https://hal.archives-ouvertes.fr/hal-02140606",
        "codemeta:version": "2",
        "external_identifier": "hal-02140606",
        "id": "hal-02140606",
        "original_artifact": [
            {
                "archive_type": "zip",
                "blake2s256": "96be3ddedfcee9669ad9c42b0bb3a706daf23824d04311c63505a4d8db02df00",
                "length": 193072,
                "name": "archive.zip",
                "sha1": "5b6ecc9d5bb113ff69fc275dcc9b0d993a8194f1",
                "sha1_git": "bd10e4d3ede17162692d7e211e08e87e67994488",
                "sha256": "3e2ce93384251ce6d6da7b8f2a061a8ebdaf8a28b8d8513223ca79ded8a10948"
            }
        ]
    },
    "parents": [
        {
            "id": "a9fdc3937d2b704b915852a64de2ab1b4b481003",
            "url": "/api/1/revision/a9fdc3937d2b704b915852a64de2ab1b4b481003/"
        }
    ],
    "synthetic": true,
    "type": "tar",
    "url": "/api/1/revision/396b1ff29f7c75a0a3cc36f30e24ff7bae70bb52/"
  }

Directory artifact
~~~~~~~~~~~~~~~~
The directory artifact is the actual content deposited.

.. code-block:: json

  [
      {
          "dir_id": "fb13b51abbcfd13de85d9ba8d070a23679576cd7",
          "length": null,
          "name": "AffectationRO",
          "perms": 16384,
          "target": "fbc418f9ac2c39e8566b04da5dc24b14e65b23b1",
          "target_url": "/api/1/directory/fbc418f9ac2c39e8566b04da5dc24b14e65b23b1/",
          "type": "dir"
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

When the loading is done and successful, the deposit entry is updated: -
``status`` is updated to ``done`` - ``swh-id`` is populated with the resulting
hash (cf. `swh identifier <#swh-identifier-returned>`__) - ``complete_date`` is
updated to the loading's finished time

When the loading is failed, the deposit entry is updated: - ``status`` is
updated to ``failed`` - ``swh-id`` and ``complete_data`` remains as is

*Note:* As a further improvement, we may prefer having a retry policy with
graceful delays for further scheduling.

Metadata loading
~~~~~~~~~~~~~~~~

- the metadata received with the deposit are also kept in the
  ``origin_metadata`` table before translation as part of the loading process
  and an indexation process should be scheduled.

- provider\_id and tool\_id are resolved by the prepare\_metadata method in the
  loader-core

- the origin\_metadata entry is sent to storage by the send\_origin\_metadata
  in the loader-core

origin\_metadata table:

::

    id                                      bigint        PK
    origin                                  bigint
    discovery_date                          date
    provider_id                             bigint        FK      // (from provider table)
    tool_id                                 bigint        FK     // indexer_configuration_id tool used for extraction
    metadata                                jsonb                // before translation
