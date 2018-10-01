The metadata-deposit
====================

Goal
----
A client wishes to deposit only metadata about an object in the Software
Heritage archive.

The metadata-deposit is a special deposit where no content is
provided and the data transferred to Software Heritage is only
the metadata about an object or several objects in the archive.

Requirements
------------
The scope of the meta-deposit is different than the
sparse-deposit. While a sparse-deposit creates a revision with referenced
directories and content files, the metadata-deposit references one of the
following:

- origin
- snapshot
- revision
- release


A complete metadata example
---------------------------
The reference element is included in the metadata xml atomEntry under the
swh namespace:

TODO: publish schema at https://www.softwareheritage.org/schema/2018/deposit

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

Examples by target type
^^^^^^^^^^^^^^^^^^^^^^^
Reference an origin:

.. code:: xml

  <swh:deposit>
    <swh:reference>
      <swh:origin url="https://github.com/user/repo"/>
    </swh:reference>
  </swh:deposit>


Reference a snapshot, revision or release:

.. code:: xml

  With ${type} in {snp (snapshot), rev (revision), rel (release) }:
  <swh:deposit>
    <swh:reference>
      <swh:object id="swh:1:${type}:aaaaaaaaaaaaaa..."/>
    </swh:reference>
  </swh:deposit>



Loading procedure
------------------

In this case, the metadata-deposit will be injected as a metadata entry at the
appropriate level (origin_metadata, revision_metadata, etc.) with the information
about the contributor of the deposit. Contrary to the complete and sparse
deposit, there will be no object creation.
