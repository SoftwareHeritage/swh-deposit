The sparse-deposit
==================

Goal
----
A client wishes to transfer a tarball for which part of the content is
already in the SWH archive.

Requirements
------------
To do so, a list of paths with targets must be provided in the metadata and
the paths to the missing directories/content should not be included
in the tarball. The list will be referred to
as the manifest list using the entry name 'bindings' in the metadata.

+----------------------+-------------------------------------+
| path                 | swh-id                              |
+======================+=====================================+
| path/to/file.txt     |  swh:1:cnt:aaaaaaaaaaaaaaaaaaaaa... |
+----------------------+-------------------------------------+
| path/to/dir/         |  swh:1:dir:aaaaaaaaaaaaaaaaaaaaa... |
+----------------------+-------------------------------------+

Note: the *name* of the file or the directory is given by the path and is not
part of the identified object.

TODO: see if a trailing "/" is mandatory for implementation.

A concrete example
------------------
The manifest list is included in the metadata xml atomEntry under the
swh namespace:

TODO: publish schema at https://www.softwareheritage.org/schema/2018/deposit

.. code:: xml

  <?xml version="1.0"?>
    <entry xmlns="http://www.w3.org/2005/Atom"
             xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
             xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit">
        <author>
          <name>HAL</name>it mandatory to have a trailing "/",
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
          <swh:binding source="path/to/file.txt" destination="swh:1:cnt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"/>
          <swh:binding source="path/to/second_file.txt destination="swh:1:cnt:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"/>
          <swh:binding source="path/to/dir/destination="swh:1:dir:ddddddddddddddddddddddddddddddddd"/>

        </swh:bindings>
        </swh:deposit>
    </entry>


Deposit verification
--------------------

After checking the integrity of the deposit content and
metadata, the following checks should be added:

1. validate the manifest list structure with a correct swh-id for each path  (syntax check on the swh-id format)
2. verify that the path name corresponds to the object type
3. locate the identifiers in the SWH archive

Each failing check should return a different error with the deposit
and result in a 'rejected' deposit.

Loading procedure
------------------
The injection procedure should include:

- load the tarball new data
- create new objects using the path name and create links from the path to the
  SWH object using the identifier
- calculate identifier of the new objects at each level
- return final swh-id of the new revision

Invariant: the same content should yield the same swh-id,
that's why a complete deposit with all the content and
a sparse-deposit with the correct links will result
with the same root directory swh-id.
The same is expected with the revision swh-id if the metadata provided is
identical.
