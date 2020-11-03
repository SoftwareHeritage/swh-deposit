The metadata-deposit
====================

Goal
----
A client wishes to deposit only metadata about an origin or object in the
Software Heritage archive.

The metadata-deposit is a special deposit where no content is
provided and the data transferred to Software Heritage is only
the metadata about an object in the archive.

Requirements
------------

1. :ref:`Create a metadata-only deposit through a POST request<Create deposit>`
2. It is composed of ONLY one xml metadata file
3. It MUST comply with :ref:`the metadata requirements<Metadata Requirements>`
4. It MUST reference an **object** or an **origin** in a deposit tag
5. The reference SHOULD exist in the SWH archive
6. The **object** reference MUST be a SWHID on one of the following artifact types:
 - origin
 - snapshot
 - release
 - revision
 - directory
 - content
7. The SWHID MAY be a `core identifier`_ with or without `qualifiers`_
8. The SWHID MUST NOT reference a fragment of code with the classifier `lines`

.. _core identifier: https://docs.softwareheritage.org/devel/swh-model/persistent-identifiers.html#core-identifiers
.. _qualifiers: https://docs.softwareheritage.org/devel/swh-model/persistent-identifiers.html#qualifiers

A complete metadata example
---------------------------
The reference element is included in the metadata xml atomEntry under the
swh namespace:

.. code:: xml

  <?xml version="1.0"?>
  <entry xmlns="http://www.w3.org/2005/Atom"
           xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
           xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit">
      <author>
        <name>HAL</name>
        <email>hal@ccsd.cnrs.fr</email>
      </author>
      <client>hal</client>
      <external_identifier>hal-01243573</external_identifier>
      <codemeta:name>The assignment problem</codemeta:name>
      <codemeta:url>https://hal.archives-ouvertes.fr/hal-01243573</codemeta:url>
      <codemeta:identifier>other identifier, DOI, ARK</codemeta:identifier>
      <codemeta:applicationCategory>Domain</codemeta:applicationCategory>
      <codemeta:description>description</codemeta:description>
      <codemeta:author>
        <codemeta:name> author1 </codemeta:name>
        <codemeta:affiliation> Inria </codemeta:affiliation>
        <codemeta:affiliation> UPMC </codemeta:affiliation>
      </codemeta:author>
      <codemeta:author>
        <codemeta:name> author2 </codemeta:name>
        <codemeta:affiliation> Inria </codemeta:affiliation>
        <codemeta:affiliation> UPMC </codemeta:affiliation>
      </codemeta:author>
      <swh:deposit>
        <swh:reference>
          <swh:origin url='https://github.com/user/repo'/>
        </swh:reference>
      </swh:deposit>
  </entry>

References
^^^^^^^^^^

Origins
=======

The metadata may be on an origin, identified by the origin's URL:

.. code:: xml

  <swh:deposit>
    <swh:reference>
      <swh:origin url="https://github.com/user/repo" />
    </swh:reference>
  </swh:deposit>

Graph objects
=============

It may also reference an object in the `SWH graph <data-model>`: contents,
directories, revisions, releases, and snapshots:

.. code:: xml

  <swh:deposit>
    <swh:reference>
      <swh:object swhid="swh:1:xxx:aaaaaaaaaaaaaa..." />
    </swh:reference>
  </swh:deposit>

The value of the ``swhid`` attribute must be a `SWHID <persistent-identifiers>`,
with any context qualifiers in this list:

* ``origin``
* ``visit``
* ``anchor``
* ``path``

and they should be provided whenever relevant, especially ``origin``.

Other qualifiers are not allowed (for example, ``line`` isn't because SWH
cannot store metadata at a finer level than entire contents).


Loading procedure
------------------

In this case, the metadata-deposit will be injected as a metadata entry of
the relevant object, with the information about the contributor of the deposit.
Contrary to the complete and sparse deposit, there will be no object creation.
