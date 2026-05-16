-- Final Project_QC production contract sync.
-- Safe/idempotent alignment for production schema, backend API, and frontend flows.

create extension if not exists pgcrypto;
create extension if not exists "uuid-ossp";

-- ---------------------------------------------------------------------------
-- Products and default product for free-form batch creation
-- ---------------------------------------------------------------------------
create table if not exists public.products (
  id uuid primary key default uuid_generate_v4(),
  product_code varchar not null unique,
  product_name varchar not null,
  ph_min numeric,
  ph_max numeric,
  brix_min numeric,
  brix_max numeric,
  core_temp_min_c numeric default 75.00,
  raw_temp_max_c numeric default 5.00,
  room_temp_max_c numeric default 20.00,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  tds_min numeric,
  tds_max numeric
);

insert into public.products (product_code, product_name, is_active)
values ('GENERAL-QC', 'General QC Product', true)
on conflict (product_code) do update set
  product_name = excluded.product_name,
  is_active = true,
  updated_at = now();

-- ---------------------------------------------------------------------------
-- Facility standard tables
-- ---------------------------------------------------------------------------
create table if not exists public.facility_rooms (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  description text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.facility_devices (
  id uuid primary key default gen_random_uuid(),
  room_id uuid references public.facility_rooms(id) on delete cascade,
  name text not null,
  slug text,
  type text,
  device_type text not null default 'room_temp',
  threshold_temp numeric,
  target_temperature numeric,
  min_temperature numeric,
  max_temperature numeric,
  is_default boolean not null default false,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.facility_devices
  add column if not exists slug text,
  add column if not exists type text,
  add column if not exists device_type text not null default 'room_temp',
  add column if not exists threshold_temp numeric,
  add column if not exists target_temperature numeric,
  add column if not exists min_temperature numeric,
  add column if not exists max_temperature numeric,
  add column if not exists is_default boolean not null default false,
  add column if not exists is_active boolean not null default true,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

update public.facility_devices
set
  slug = coalesce(nullif(slug, ''), lower(regexp_replace(name, '[^a-zA-Z0-9]+', '-', 'g'))),
  device_type = case
    when coalesce(device_type, type) in ('ambient', 'room') then 'room_temp'
    when coalesce(device_type, type) in ('room_temp', 'chiller', 'freezer') then coalesce(device_type, type)
    else 'room_temp'
  end,
  type = case
    when coalesce(device_type, type) in ('ambient', 'room') then 'room_temp'
    when coalesce(device_type, type) in ('room_temp', 'chiller', 'freezer') then coalesce(device_type, type)
    else 'room_temp'
  end,
  target_temperature = coalesce(target_temperature, threshold_temp),
  threshold_temp = coalesce(threshold_temp, target_temperature);

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'facility_devices_device_type_allowed'
      and conrelid = 'public.facility_devices'::regclass
  ) then
    alter table public.facility_devices
      add constraint facility_devices_device_type_allowed
      check (device_type in ('room_temp', 'chiller', 'freezer')) not valid;
  end if;
end $$;

create unique index if not exists uq_facility_devices_room_name
on public.facility_devices (room_id, name)
where room_id is not null;

create unique index if not exists uq_facility_devices_room_slug
on public.facility_devices (room_id, slug)
where room_id is not null and slug is not null;

-- ---------------------------------------------------------------------------
-- Facility logs/alerts, tolerant of older enum-heavy schema
-- ---------------------------------------------------------------------------
alter table if exists public.facility_logs
  add column if not exists room_id uuid,
  add column if not exists device_id uuid,
  add column if not exists staff_id uuid,
  add column if not exists reason text,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists humidity_rh numeric,
  add column if not exists notes text;

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public'
      and table_name = 'facility_logs'
      and column_name = 'zone'
      and udt_name <> 'text'
  ) then
    alter table public.facility_logs
      alter column zone type text using zone::text;
  end if;
end $$;

alter table if exists public.facility_logs
  alter column zone drop not null,
  alter column threshold_c drop not null,
  alter column is_normal set default true;

update public.facility_logs
set
  zone = coalesce(zone, 'QC Area'),
  threshold_c = coalesce(threshold_c, 25),
  is_normal = coalesce(is_normal, true),
  notes = coalesce(notes, reason);

create table if not exists public.temperature_logs (
  id uuid primary key default gen_random_uuid(),
  room_id uuid,
  device_id uuid,
  staff_id uuid,
  temperature numeric,
  temperature_c numeric,
  status text,
  is_abnormal boolean not null default false,
  photo_url text,
  storage_path text,
  notes text,
  created_at timestamptz not null default now(),
  recorded_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.temperature_logs
  add column if not exists room_id uuid,
  add column if not exists device_id uuid,
  add column if not exists staff_id uuid,
  add column if not exists temperature numeric,
  add column if not exists temperature_c numeric,
  add column if not exists status text,
  add column if not exists is_abnormal boolean not null default false,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists notes text,
  add column if not exists recorded_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

alter table if exists public.facility_alerts
  add column if not exists room_id uuid,
  add column if not exists device_id uuid,
  add column if not exists temperature numeric,
  add column if not exists threshold numeric,
  add column if not exists severity text not null default 'warning',
  add column if not exists description text,
  add column if not exists corrective_action text,
  add column if not exists created_at timestamptz not null default now();

-- ---------------------------------------------------------------------------
-- Production batch/report contract
-- ---------------------------------------------------------------------------
alter table if exists public.production_batches
  add column if not exists product_name text,
  add column if not exists expired_date date,
  add column if not exists created_by uuid,
  add column if not exists photo_url text,
  add column if not exists storage_path text;

update public.production_batches pb
set product_id = p.id
from public.products p
where p.product_code = 'GENERAL-QC'
  and pb.product_id is null;

alter table if exists public.qc_reports
  add column if not exists barcode text,
  add column if not exists ccp_stage text,
  add column if not exists temperature numeric,
  add column if not exists notes text,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists temperature_storage_path text,
  add column if not exists barcode_storage_path text,
  add column if not exists product_storage_path text,
  add column if not exists updated_at timestamptz not null default now();

-- ---------------------------------------------------------------------------
-- Evidence and storage
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public)
values ('qc-evidence', 'qc-evidence', true)
on conflict (id) do update set name = excluded.name, public = true;

create table if not exists public.qc_evidence (
  id uuid primary key default gen_random_uuid(),
  file_name text,
  file_type text,
  mime_type text,
  file_size bigint,
  bucket text not null default 'qc-evidence',
  storage_path text not null,
  public_url text,
  signed_url text,
  uploaded_by uuid,
  related_type text not null,
  related_id text,
  created_at timestamptz not null default now()
);

alter table public.qc_evidence
  add column if not exists mime_type text,
  add column if not exists file_size bigint,
  add column if not exists public_url text,
  add column if not exists signed_url text,
  add column if not exists uploaded_by uuid,
  add column if not exists related_type text,
  add column if not exists related_id text,
  add column if not exists created_at timestamptz not null default now();

-- ---------------------------------------------------------------------------
-- Staff profiles: staff_accounts remains auth table, users holds names.
-- ---------------------------------------------------------------------------
alter table if exists public.users
  add column if not exists staff_account_id uuid,
  add column if not exists full_name text,
  add column if not exists role text not null default 'qc_staff',
  add column if not exists updated_at timestamptz not null default now();

create unique index if not exists idx_users_staff_account_id_unique
on public.users (staff_account_id)
where staff_account_id is not null;

insert into public.users (staff_account_id, full_name, role)
select
  sa.id,
  sa.username,
  case when sa.role = 'admin' then 'admin' else 'qc_staff' end
from public.staff_accounts sa
where not exists (
  select 1 from public.users u where u.staff_account_id = sa.id
);

-- ---------------------------------------------------------------------------
-- Idempotent facility seed
-- ---------------------------------------------------------------------------
with room_seed(name, slug) as (
  values
    ('PPIC', 'ppic'),
    ('Grouper', 'grouper'),
    ('Pack Basah', 'pack-basah'),
    ('Pack Kering', 'pack-kering'),
    ('Ruang Kopi', 'ruang-kopi'),
    ('Kitchen', 'kitchen')
)
insert into public.facility_rooms (name, slug, description, is_active)
select name, slug, 'Default QC monitoring room', true
from room_seed
on conflict (slug) do update set
  name = excluded.name,
  updated_at = now();

with unit_seed(device_type, name, target_temperature, min_temperature, max_temperature) as (
  values
    ('room_temp', 'Suhu Ruangan', 25::numeric, 15::numeric, 30::numeric),
    ('chiller', 'Chiller', 5::numeric, 0::numeric, 8::numeric),
    ('freezer', 'Freezer', -18::numeric, -30::numeric, -15::numeric)
)
insert into public.facility_devices (
  room_id,
  name,
  slug,
  device_type,
  type,
  target_temperature,
  threshold_temp,
  min_temperature,
  max_temperature,
  is_default,
  is_active
)
select
  r.id,
  u.name,
  r.slug || '-' || u.device_type,
  u.device_type,
  u.device_type,
  u.target_temperature,
  u.target_temperature,
  u.min_temperature,
  u.max_temperature,
  true,
  true
from public.facility_rooms r
cross join unit_seed u
where r.slug in ('ppic', 'grouper', 'pack-basah', 'pack-kering', 'ruang-kopi', 'kitchen')
  and not exists (
    select 1
    from public.facility_devices existing
    where existing.room_id = r.id
      and (existing.slug = r.slug || '-' || u.device_type or existing.name = u.name)
  );

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------
create index if not exists idx_facility_rooms_slug_sync on public.facility_rooms (slug);
create index if not exists idx_facility_devices_room_id_sync on public.facility_devices (room_id);
create index if not exists idx_facility_devices_device_type_sync on public.facility_devices (device_type);
create index if not exists idx_facility_logs_created_at_sync on public.facility_logs (created_at desc);
create index if not exists idx_temperature_logs_created_at_sync on public.temperature_logs (created_at desc);
create index if not exists idx_temperature_logs_device_id_sync on public.temperature_logs (device_id);
create index if not exists idx_facility_alerts_status_sync on public.facility_alerts (status);
create index if not exists idx_qc_reports_created_at_sync on public.qc_reports (created_at desc);
create index if not exists idx_qc_evidence_related_sync on public.qc_evidence (related_type, related_id);
