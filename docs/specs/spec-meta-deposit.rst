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
The scope of the metadata-deposit is different than the
sparse-deposit. While a sparse-deposit creates a revision with referenced
directories and content files, the metadata-deposit references any of the
following:

- origin
- snapshot
- release
- revision
- directory
- content


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
