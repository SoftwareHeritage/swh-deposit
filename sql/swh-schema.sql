---
--- Software Heritage - SWH Deposit Data Model
---

create table dbversion(
  version     int primary key,
  release     timestamptz,
  description text
);

insert into dbversion(version, release, description)
values(1, now(), 'Work In Progress');

create type deposit_status as enum (
  'partially-received',  -- the deposit is partial since it can be done in multiple requests
  'received',            -- deposit is fully deposited and can be injected
  'injecting',           -- injection is ongoing on swh's side
  'injected',            -- injection is successfully done
  'failed'               -- injection failed due to some error
);

comment on type deposit_status is 'Deposit''s life cycle';

create table client(
  id bigserial primary key,
  name text not null
);

comment on table client is 'Deposit''s Client references';
comment on column client.id is 'Short identifier for the client';
comment on column client.name is 'Human readable name for the client e.g hal, arXiv, etc...';

create table deposit_type(
  id serial primary key,
  name text not null
);

comment on table deposit_type is 'Deposit type';
comment on column deposit_type.id is 'Short identifier for the deposit type';
comment on column deposit_type.name is 'Human readable name for the deposit type e.g HAL, arXiv, etc...';

create table deposit(
  id bigserial primary key,
  reception_date timestamptz not null,
  complete_date timestamptz not null,
  type serial not null references deposit_type(id),
  external_id text not null,
  status deposit_status not null,
  client_id bigint not null
);

comment on table deposit is 'Deposit reception table of archive to load in swh';

comment on column deposit.id is 'Deposit receipt id';
comment on column deposit.reception_date is 'First deposit reception date';
comment on column deposit.complete_date is 'Date when the deposit is deemed complete and ready for injection';
comment on column deposit.type is 'Deposit reception source type';
comment on column deposit.external_id is 'Deposit''s unique external identifier';
comment on column deposit.status is 'Deposit''s status regarding injection';
comment on column deposit.client_id is 'Deposit client identifier';


--create unique index deposit_pkey on deposit(client_id, external_id);

-- We may need another table for the multiple requests
-- When reading for injection, we'd need to aggregate information

create table deposit_request(
  id bigserial primary key,
  deposit_id bigint not null references deposit(id),
  metadata jsonb not null
);

comment on table deposit_request is 'Deposit request made by the client';

comment on column deposit_request.id is 'Deposit request id';
comment on column deposit_request.deposit_id is 'Deposit concerned by the request';
comment on column deposit_request.metadata is 'Deposit request information on the data to inject';
-- path to the archive + "raw" metadata from the source (e.g hal)
