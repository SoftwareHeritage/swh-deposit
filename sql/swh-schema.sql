---
--- Software Heritage Data Model
---

-- drop schema if exists swh cascade;
-- create schema swh;
-- set search_path to swh;

create table dbversion(
  version     int primary key,
  release     timestamptz,
  description text
);

insert into dbversion(version, release, description)
values(1, now(), 'Work In Progress');

create type deposit_status as enum ('received', 'to-inject', 'injecting', 'injected', 'failed');

comment on type deposit_status is 'Deposit''s life cycle';

create table deposit_type(
  id serial primary key,
  name text not null
);

comment on table deposit_type is 'Deposit type';
comment on column deposit_type.id is 'Short identifier for the deposit type';
comment on column deposit_type.name is 'Human readable name for the deposit type e.g HAL, arXiv, etc...';

create table deposit(
  id bigserial primary key,
  date timestamptz not null,
  type serial not null references deposit_type(id),
  metadata jsonb not null,
  status deposit_status not null
);

comment on table deposit is 'Deposit reception table of archive to load in swh';
comment on column deposit.id is 'Deposit receipt id';
comment on column deposit.date is 'Deposit reception date';
comment on column deposit.type is 'Deposit reception source type';
comment on column deposit.metadata is 'Deposit information on the data to inject';
-- path to the archive + "raw" metadata from the source (hal)

comment on column deposit.status is 'Deposit''s status regarding injection';
