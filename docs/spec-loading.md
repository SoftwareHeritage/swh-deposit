# Loading specification (draft)

This part discusses the deposit loading part on the server side.

## Tarball Loading

The `swh-loader-tar` module is already able to inject tarballs in swh
with very limited metadata (mainly the origin).

The loading of the deposit will use the deposit's associated data:
- the metadata
- the archive(s)

We will use the `synthetic` revision notion.

To that revision will be associated the metadata. Those will be
included in the hash computation, thus resulting in a unique
identifier.

### Loading mapping

Some of those metadata will also be included in the `origin_metadata`
table.

```
origin                              |      https://hal.inria.fr/hal-id       |
------------------------------------|----------------------------------------|
origin_visit                        | 1 :reception_date                      |
origin_metadata                     | aggregated metadata                    |
occurrence &amp; occurrence_history | branch: client's version n° (e.g hal)  |
revision                            | synthetic_revision (tarball)           |
directory                           | upper level of the uncompressed archive|
```

### Questions raised concerning loading

- A deposit has one origin, yet an origin can have multiple deposits?

No, an origin can have multiple requests for the same deposit.
Which should end up in one single deposit (when the client pushes its final
request saying deposit 'done' through the header In-Progress).

Only update of existing 'partial' deposit is permitted.
Other than that, the deposit 'update' operation.

To create a new version of a software (already deposited), the client
must prior to this create a new deposit.


Illustration First deposit loading:

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
  loading

- one client to test the communication with SWORD protocol

### Deposit reception schema

- SWORD imposes the use of basic authentication, so we need a way to
authenticate client. Also, a client can access collections:

**deposit_client** table:
  - id (bigint): Client's identifier
  - username (str): Client's username
  - password (pass): Client's crypted password
  - collections ([id]): List of collections the client can access

- Collections group deposits together:

**deposit_collection** table:
  - id (bigint): Collection's identifier
  - name (str): Collection's human readable name

- A deposit is the main object the repository is all about:

**deposit** table:
  - id (bigint): deposit's identifier
  - reception_date (date): First deposit's reception date
  - complete_data (date): Date when the deposit is deemed complete and ready for loading
  - collection (id): The collection the deposit belongs to
  - external id (text): client's internal identifier (e.g hal's id, etc...).
  - client_id (id) : Client which did the deposit
  - swh_id (str) : swh identifier result once the loading is complete
  - status (enum): The deposit's current status

- As mentioned, a deposit can have a status, whose possible values
  are:

``` text
    'partial',   -- the deposit is new or partially received since it
                 -- can be done in multiple requests
    'expired',   -- deposit has been there too long and is now deemed
                 -- ready to be garbage collected
    'deposited'  -- deposit complete, it is ready to be checked to ensure data consistency
    'verified',  -- deposit is fully received, checked, and ready for loading
    'loading',   -- loading is ongoing on swh's side
    'done',      -- loading is successful
    'failed'     -- loading is a failure
```

A deposit is stateful and can be made in multiple requests:

**deposit_request** table:
  - id (bigint): identifier
  - type (id): deposit request's type (possible values: 'archive', 'metadata')
  - deposit_id (id): deposit whose request belongs to
  - metadata: metadata associated to the request
  - date (date): date of the requests

Information sent along a request are stored in a `deposit_request`
row.

They can be either of type `metadata` (atom entry, multipart's atom
entry part) or of type `archive` (binary upload, multipart's binary
upload part).

When the deposit is complete (status `deposited`), those `metadata`
and `archive` deposit requests will be read and aggregated. They will
then be sent as parameters to the loading routine.

During loading, some of those metadata are kept in the
`origin_metadata` table and some other are stored in the `revision`
table (see [metadata loading](#metadata-loading)).

The only update actions occurring on the deposit table are in regards
of:
- status changing:
  - `partial` -> {`expired`/`deposited`},
  - `deposited` -> {`rejected`/`verified`},
  - `verified` -> `loading`
  - `loading` -> {`done`/`failed`}
- `complete_date` when the deposit is finalized (when the status is
  changed to `deposited`)
- `swh-id` is populated once we have the loading result

#### SWH Identifier returned

    The synthetic revision id

    e.g: 47dc6b4636c7f6cba0df83e3d5490bf4334d987e

### Scheduling loading

All `archive` and `metadata` deposit requests should be aggregated
before loading.

The loading should be scheduled via the scheduler's api.

Only `deposited` deposit are concerned by the loading.

When the loading is done and successful, the deposit entry is
updated:
- `status` is updated to `done`
- `swh-id` is populated with the resulting hash
  (cf. [swh identifier](#swh-identifier-returned))
- `complete_date` is updated to the loading's finished time

When the loading is failed, the deposit entry is updated:
- `status` is updated to `failed`
- `swh-id` and `complete_data` remains as is

*Note:* As a further improvement, we may prefer having a retry policy
with graceful delays for further scheduling.

### Metadata loading

- the metadata received with the deposit should be kept in the
`origin_metadata` table before translation as part of the loading
process and an indexation process should be scheduled.

- provider_id and tool_id are resolved by the prepare_metadata method in the
loader-core

- the origin_metadata entry is sent to storage by the send_origin_metadata in
the loader-core


origin_metadata table:
```
id                                      bigint        PK
origin                                  bigint
discovery_date                          date
provider_id                             bigint        FK      // (from provider table)
tool_id                                 bigint        FK     // indexer_configuration_id tool used for extraction
metadata                                jsonb                // before translation
```
