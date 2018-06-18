The sparse-deposit
==================

Goal
----
A client wishes to transfer a tarball for which part of the content is
already in the SWH archive.

Requirements
------------
To do so, the paths to the missing directories/content must be provided as
empty paths in the tarball and the list linking each path to the object in the
archive will be provided as part of the metadata. The list will be refered to
as the manifest list.

+----------------------+-------------------------------------+
| path                 | swh-id                              |
+======================+=====================================+
| path/to/file.txt     |  swh:1:cnt:aaaaaaaaaaaaaaaaaaaaa... |
+----------------------+-------------------------------------+
| path/to/dir/         |  swh:1:dir:aaaaaaaaaaaaaaaaaaaaa... |
+----------------------+-------------------------------------+

Note: the *name* of the file or the directory is given by the path and is not
part of the identified object.

A concrete example
------------------
The manifest list is included in the metadata xml atomEntry under the
swh namespace:

.. code:: xml

  <?xml version="1.0"?>
    <entry xmlns="http://www.w3.org/2005/Atom"
             xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
             xmlns:swh="swh.xsd">
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
          <swh:bindings>
          <swh:binding source="path/to/file.txt"
                       destination="swh:1:cnt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"/>
          <swh:binding source="path/to/second_file.txt
                       destination="swh:1:cnt:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"/>
          <swh:binding source="path/to/dir/
                       destination="swh:1:dir:ddddddddddddddddddddddddddddddddd"/>

        </swh:bindings>
        </swh:deposit>
    </entry>

The tarball sent with the deposit will contain the following empty paths:
- path/to/file.txt
- path/to/second_file.txt
- path/to/dir/

Deposit verification
--------------------

After checking the integrity of the deposit content and
metadata, the following checks should be added:

1. validate the manifest list structure with a swh-id for each path
2. verify that the paths in the manifest list are explicit and empty in the tarball
3. verify that the path name corresponds to the object type
4. locate the identifiers in the SWH archive

Each one of the verifications should return a different error with the deposit
and result in a 'rejected' deposit.

Loading procedure
------------------
The injection procedure should include:

- load the tarball data
- create new objects using the path name and create links from the path to the
  SWH object using the identifier
- calculate identifier of the new objects at each level
- return final swh-id of the new revision

Invariant: the same content should yield the same swhid, that's why a complete
deposit with all the content and a sparse-deposit with the correct links will
result with the same root directory swh-id and if the metadata are identical
also with the same revision swh-id.
