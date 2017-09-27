# Injection specification (draft)

This part discusses the deposit injection part on the server side.

## Tarball Injection

Providing we use indeed synthetic revision to represent a version of a
tarball injected through the sword use case, this needs to be improved
so that the synthetic revision is created with a parent revision (the
previous known one for the same 'origin').


### Injection mapping

| origin                              |      https://hal.inria.fr/hal-id       |
|-------------------------------------|----------------------------------------|
| origin_visit                        |           1 :reception_date            |
| occurrence &amp; occurrence_history | branch: client's version n° (e.g hal)  |
| revision                            |      synthetic_revision (tarball)      |
| directory                           | upper level of the uncompressed archive|


### Questions raised concerning injection

- A deposit has one origin, yet an origin can have multiple deposits?

No, an origin can have multiple requests for the same deposit.
Which should end up in one single deposit (when the client pushes its final
request saying deposit 'done' through the header In-Progress).

Only update of existing 'partial' deposit is permitted.
Other than that, the deposit 'update' operation.

To create a new version of a software (already deposited), the client
must prior to this create a new deposit.


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



## Technical details

### Requirements

- one dedicated database to store the deposit's state - swh-deposit

- one dedicated temporary objstorage to store archives before
  injection

- one client to test the communication with SWORD protocol

### Deposit reception schema

- SWORD imposes the use of basic authentication, so we need a way to
authenticate client:

**deposit_client** table:
  - id (bigint): Client's identifier
  - username (str): Client's username
  - password (pass): Client's password
  - collections ([id]): List of collections the client can access

- A client can access collection and a deposit is specific to a collection.

**deposit_collection** table:
  - id (bigint): Collection's identifier
  - name (str): Collection's human readable name

- A deposit is the main entity the repository is all about:

**deposit** table:
  - id (bigint): deposit's identifier
  - reception_date (date): First deposit's reception date
  - complete_data (date): Date when the deposit is deemed complete and ready for injection
  - collection (id): The collection the deposit belongs to
  - external id (text): client's internal identifier (e.g hal's id, etc...).
  - client_id (id) : Client which did the deposit
  - swh_id (str) : swh identifier result once the injection is complete
  - status (enum): The deposit's current status

- As mentioned, a deposit can have a status, whose possible values are:
```
      'partial',      -- the deposit is new or partially received since it
                      -- can be done in multiple requests
      'expired',      -- deposit has been there too long and is now deemed
                      -- ready to be garbage collected
      'ready',        -- deposit is fully received and ready for injection
      'injecting,     -- injection is ongoing on swh's side
      'success',      -- injection is successful
      'failure'       -- injection is a failure
```

A deposit is stateful and can be made in multiple requests:
**deposit_request** table:
  - id (bigint): identifier
  - type (id): deposit request's type (possible values: 'archive', 'metadata')
  - deposit_id (id): deposit whose request belongs to
  - metadata: metadata associated to the request
  - date (date): date of the requests

Information sent along a request are stored in a deposit_request row.

They can be either of type 'metadata' (atom entry, multipart's atom
entry part) or of type 'archive' (binary upload, multipart's binary
upload part).

When the deposit is complete (status 'ready'), those metadata fields
are read and aggregated. They will be sent as parameters to the
injection routine. During injection, those metadata are kept in the
origin_metadata table (see [metadata injection](#metadata-injection)).

The only update actions occurring on the deposit table are in regards
of:
- status changing:
  - partial -> {expired/ready},
  - ready -> injecting,
  - injecting -> {success/failure}
- complete_date when the deposit is finalized (when the status is
  changed to ready)
- swh-id is populated once we have the injection result

#### SWH Identifier returned

    swh-<client-name>-<synthetic-revision-id>

    e.g: swh-hal-47dc6b4636c7f6cba0df83e3d5490bf4334d987e

### Scheduling injection

All data and metadata separated with multiple requests should be
aggregated before injection.
The injection should be scheduled via the scheduler's api.

When the injection is done and successful, the deposit entry is updated:
- status is updated to success
- swh-id is populated with the resulting hash
- complete_date is updated to the injection's finished date

When the injection is failed, the deposit entry is updated:
- status is updated to failure
- swh-id and complete_data are left as is

We may install a retry policy with graceful delays for further
scheduling.

### Metadata injection

- the metadata received with the deposit should be kept in the
origin_metadata table before translation as part of the injection
process and an indexation process should be scheduled.

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
