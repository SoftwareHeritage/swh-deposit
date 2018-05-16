The meta-deposit
================

Goal
----
A client wishes to deposit only metadata about an object in the Software
Heritage archive.

The meta-deposit is a special deposit where no content is
deposited and the data transfered to Software Heritage is only
the metadata about an object or several objects in the archive.

The scope of the meta-deposit is different than the
sparse-deposit, while a sparse-deposit creates a revision with referenced
directories and content files, the meta-deposit references one of the following:

- origin
- snapshot
- revision
- release


A complete metadata example
---------------------------
The reference element is included in the metadata xml atomEntry under the
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
          <swh:reference>
            <swh:type> origin </swh:type>
            <swh:target> https://github.com/user/repo </swh:target>
          </swh:reference>
        </swh:deposit>
    </entry>

examples by target type
^^^^^^^^^^^^^^^^^^^^^^^
snapshot
*********
.. code:: xml

  <swh:deposit>
    <swh:reference>
      <swh:type> snapshot </swh:type>
      <swh:target> swh:1:snp:aaaaaaaaaaaaaa... </swh:target>
    </swh:reference>
  </swh:deposit>

revision
********
.. code:: xml

  <swh:deposit>
    <swh:reference>
      <swh:type> revision </swh:type>
      <swh:target> swh:1:rev:aaaaa............ </swh:target>
    </swh:reference>
  </swh:deposit>

release
*******
.. code:: xml

  <swh:deposit>
    <swh:reference>
      <swh:type> release </swh:type>
      <swh:target> swh:1:rel:aaaaaaaaaaaaaa.... </swh:target>
    </swh:reference>
  </swh:deposit>

Loading procedure
------------------

In this case, the meta-deposit will be injected as a metadata entry at the
appropriate level (origin_metadata, revision_metadata, etc.) and won't result
in  the creation of a new object like with the complete deposit and the
sparse-deposit.
