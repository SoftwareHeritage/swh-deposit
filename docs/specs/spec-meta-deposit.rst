The meta-deposit
================

Goal
----
A client wishes to deposit only metadata about an object in the Software
Heritage archive.

The meta-deposit is a special deposit where no content is
deposited and the data transfered to Software Heritage is only
the metadata about an object or several objects in the archive.

The scope of the meta-deposit is larger than the sparse-deposit, because
with a meta-deposit all types of objects in the archive can be described
with the deposited metadata:

- origin
- snapshot
- revision
- release
- directory
- content


Loading procedure
------------------

In this case, the meta-deposit will be injected as a metadata entry at the
appropriate level (origin_metadata, revision_metadata, etc.) and won't result
in  the creation of a new object like with the complete deposit and the
sparse-deposit.
