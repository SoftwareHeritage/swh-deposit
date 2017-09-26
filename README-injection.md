swh-deposit - injection
=============================

This part discusses the deposit injection part on the server side.

== Tarball Injection ==

Providing we use indeed synthetic revision to represent a version of a
tarball injected through the sword use case, this needs to be improved
so that the synthetic revision is created with a parent revision (the
previous known one for the same 'origin').


=== Injection mapping ===
| origin                              |      https://hal.inria.fr/hal-id      |
|-------------------------------------|---------------------------------------|
| origin_visit                        |           1 :reception_date           |
| occurrence &amp; occurrence_history | branch: client's version n° (e.g hal) |
| revision                            |      synthetic_revision (tarball)     |
| directory                           | upper level of the uncompressed archive|


=== Questions raised concerning injection: ===
- A deposit has one origin, yet an origin can have multiple deposits ?

No, an origin can have multiple requests for the same deposit,
which should end up in one single deposit (when the client pushes its final
request saying deposit 'done' through the header In-Progress).

When an update of a deposit is requested,
the new version is identified with the external_id.

Illustration First deposit injection:

HAL's deposit 01535619 = SWH's deposit **01535619-1**

    + 1 origin with url:https://hal.inria.fr/medihal-01535619

    + 1 synthetic revision

    + 1 directory

HAL's update on deposit 01535619 = SWH's deposit **01535619-2**

(*with HAL updates can only be on the metadata and a new version is required
if the content changes)
    + 1 origin with url:https://hal.inria.fr/medihal-01535619

    + new synthetic revision (with new metadata)

    + same directory

HAL's deposit 01535619-v2 = SWH's deposit **01535619-v2-1**

    + same origin

    + new revision

    + new directory



== Technical details ==

We will need:
- one dedicated db to store state - swh-deposit

- one dedicated temporary storage to store archives before injection

- one client to test the communication with SWORD protocol

=== Deposit reception schema ===

- **deposit** table:
  - id (bigint): deposit receipt id

  - external id (text): client's internal identifier (e.g hal's id, etc...).

  - origin id : null before injection
  - swh_id : swh identifier result once the injection is complete

  - reception_date: first deposit date

  - complete_date: reception date of the last deposit which makes the deposit
  complete

  - status (enum):
```
      'partial',      -- the deposit is new or partially received since it
                      -- can be done in multiple requests
      'expired',      -- deposit has been there too long and is now deemed
                      -- ready to be garbage collected
      'ready',        -- deposit is fully received and ready for injection
      'scheduled',    -- injection is scheduled on swh's side
      'success',      -- injection successful
      'failure'       -- injection failure
```
- **deposit_request** table:
  - id (bigint): identifier
  - deposit_id: deposit concerned by the request
  - metadata: metadata associated to the request

- **client** table:
  - id (bigint): identifier
  - name (text): client's name (e.g HAL)
  - credentials


All metadata (declared metadata) are stored in deposit_request (with the
request they were sent with).
When the deposit is complete metadata fields are aggregated and sent
to injection. During injection the metadata is kept in the
origin_metadata table (see [metadata injection](#metadata-injection)).

The only update actions occurring on the deposit table are in regards of:
  - status changing
    - partial -> {expired/ready},
    - ready -> scheduled,
    - scheduled -> {success/failure}
  - complete_date when the deposit is finalized
  (when the status is changed to ready)
  - swh-id being populated once we have the result of the injection

==== SWH Identifier returned? ====

    swh-<client-name>-<synthetic-revision-id>

    e.g: swh-hal-47dc6b4636c7f6cba0df83e3d5490bf4334d987e

    We could have a specific dedicated 'client' table to reference client
    identifier.

=== Scheduling injection ===
All data and metadata separated with multiple requests should be aggregated
before injection.

TODO: injection modeling

=== Metadata injection ===
- the metadata received with the deposit should be kept in the origin_metadata
table before translation as part of the injection process and a indexation
process should be scheduled.

origin_metadata table:
```
origin                                  bigint        PK FK
discovery_date                          date          PK FK
translation_date                        date          PK FK
provenance_type                         text                  // (enum: 'publisher', 'lister' needs to be completed)
raw_metadata                            jsonb                 // before translation
indexer_configuration_id                bigint            FK  // tool used for translation
translated_metadata                     jsonb                 // with codemeta schema and terms
```
