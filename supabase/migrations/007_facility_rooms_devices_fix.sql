-- Facility rooms/devices production fix.
-- Additive and idempotent for existing Project_QC Supabase projects.

create extension if not exists pgcrypto;

create table if not exists public.facility_rooms (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text unique not null,
  description text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.facility_devices (
  id uuid primary key default gen_random_uuid(),
  room_id uuid references public.facility_rooms(id) on delete cascade,
  name text not null,
  slug text not null,
  device_type text not null default 'room_temp' check (device_type in ('room_temp', 'chiller', 'freezer')),
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
  add column if not exists device_type text not null default 'room_temp',
  add column if not exists target_temperature numeric,
  add column if not exists min_temperature numeric,
  add column if not exists max_temperature numeric,
  add column if not exists is_default boolean not null default false,
  add column if not exists is_active boolean not null default true,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now(),
  add column if not exists type text,
  add column if not exists threshold_temp numeric;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'facility_devices_room_id_fkey'
      and conrelid = 'public.facility_devices'::regclass
  ) then
    alter table public.facility_devices
      add constraint facility_devices_room_id_fkey
      foreign key (room_id) references public.facility_rooms(id) on delete cascade not valid;
  end if;
end $$;

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
  ) then
    alter table public.facility_devices
      add constraint facility_devices_device_type_allowed
      check (device_type in ('room_temp', 'chiller', 'freezer')) not valid;
  end if;
end $$;

create table if not exists public.temperature_logs (
  id uuid primary key default gen_random_uuid(),
  room_id uuid references public.facility_rooms(id) on delete set null,
  device_id uuid references public.facility_devices(id) on delete set null,
  staff_id uuid,
  temperature numeric,
  temperature_c numeric(6,2),
  status text,
  photo_url text,
  storage_path text,
  notes text,
  created_at timestamptz not null default now(),
  recorded_at timestamptz not null default now()
);

alter table public.temperature_logs
  add column if not exists room_id uuid references public.facility_rooms(id) on delete set null,
  add column if not exists device_id uuid references public.facility_devices(id) on delete set null,
  add column if not exists staff_id uuid,
  add column if not exists temperature numeric,
  add column if not exists temperature_c numeric(6,2),
  add column if not exists status text,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists notes text,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists recorded_at timestamptz not null default now();

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'temperature_logs_room_id_fkey'
      and conrelid = 'public.temperature_logs'::regclass
  ) then
    alter table public.temperature_logs
      add constraint temperature_logs_room_id_fkey
      foreign key (room_id) references public.facility_rooms(id) on delete set null not valid;
  end if;

  if not exists (
    select 1 from pg_constraint
    where conname = 'temperature_logs_device_id_fkey'
      and conrelid = 'public.temperature_logs'::regclass
  ) then
    alter table public.temperature_logs
      add constraint temperature_logs_device_id_fkey
      foreign key (device_id) references public.facility_devices(id) on delete set null not valid;
  end if;
end $$;

create table if not exists public.facility_logs (
  id uuid primary key default gen_random_uuid(),
  room_id uuid references public.facility_rooms(id) on delete set null,
  device_id uuid references public.facility_devices(id) on delete set null,
  staff_id uuid,
  temperature_c numeric(6,2),
  humidity_rh numeric(6,2),
  is_normal boolean not null default true,
  reason text,
  photo_url text,
  storage_path text,
  recorded_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

alter table public.facility_logs
  add column if not exists room_id uuid references public.facility_rooms(id) on delete set null,
  add column if not exists device_id uuid references public.facility_devices(id) on delete set null,
  add column if not exists staff_id uuid,
  add column if not exists temperature_c numeric(6,2),
  add column if not exists humidity_rh numeric(6,2),
  add column if not exists is_normal boolean not null default true,
  add column if not exists reason text,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists recorded_at timestamptz not null default now(),
  add column if not exists created_at timestamptz not null default now();

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'facility_logs_room_id_fkey'
      and conrelid = 'public.facility_logs'::regclass
  ) then
    alter table public.facility_logs
      add constraint facility_logs_room_id_fkey
      foreign key (room_id) references public.facility_rooms(id) on delete set null not valid;
  end if;

  if not exists (
    select 1 from pg_constraint
    where conname = 'facility_logs_device_id_fkey'
      and conrelid = 'public.facility_logs'::regclass
  ) then
    alter table public.facility_logs
      add constraint facility_logs_device_id_fkey
      foreign key (device_id) references public.facility_devices(id) on delete set null not valid;
  end if;
end $$;

create table if not exists public.facility_alerts (
  id uuid primary key default gen_random_uuid(),
  room_id uuid references public.facility_rooms(id) on delete set null,
  device_id uuid references public.facility_devices(id) on delete set null,
  temperature numeric,
  temperature_c numeric(6,2),
  threshold numeric,
  threshold_c numeric(6,2),
  status text not null default 'open',
  severity text not null default 'warning',
  description text,
  corrective_action text,
  created_at timestamptz not null default now()
);

alter table public.facility_alerts
  add column if not exists room_id uuid references public.facility_rooms(id) on delete set null,
  add column if not exists device_id uuid references public.facility_devices(id) on delete set null,
  add column if not exists temperature numeric,
  add column if not exists temperature_c numeric(6,2),
  add column if not exists threshold numeric,
  add column if not exists threshold_c numeric(6,2),
  add column if not exists status text not null default 'open',
  add column if not exists severity text not null default 'warning',
  add column if not exists description text,
  add column if not exists corrective_action text,
  add column if not exists created_at timestamptz not null default now();

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'facility_alerts_room_id_fkey'
      and conrelid = 'public.facility_alerts'::regclass
  ) then
    alter table public.facility_alerts
      add constraint facility_alerts_room_id_fkey
      foreign key (room_id) references public.facility_rooms(id) on delete set null not valid;
  end if;

  if not exists (
    select 1 from pg_constraint
    where conname = 'facility_alerts_device_id_fkey'
      and conrelid = 'public.facility_alerts'::regclass
  ) then
    alter table public.facility_alerts
      add constraint facility_alerts_device_id_fkey
      foreign key (device_id) references public.facility_devices(id) on delete set null not valid;
  end if;
end $$;

create table if not exists public.production_batches (
  id uuid primary key default gen_random_uuid(),
  batch_code text not null unique,
  product_id uuid,
  product_name text,
  production_date date,
  expired_date date,
  status text not null default 'pending',
  created_by uuid,
  operator_id uuid,
  qc_officer_id uuid,
  photo_url text,
  storage_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.production_batches
  add column if not exists batch_code text,
  add column if not exists product_id uuid,
  add column if not exists product_name text,
  add column if not exists production_date date,
  add column if not exists expired_date date,
  add column if not exists status text not null default 'pending',
  add column if not exists created_by uuid,
  add column if not exists operator_id uuid,
  add column if not exists qc_officer_id uuid,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

insert into storage.buckets (id, name, public)
values ('qc-evidence', 'qc-evidence', true)
on conflict (id) do update set name = excluded.name, public = true;

create table if not exists public.qc_evidence (
  id uuid primary key default gen_random_uuid(),
  bucket text not null default 'qc-evidence',
  storage_path text not null,
  public_url text,
  signed_url text,
  uploaded_by uuid,
  related_type text not null,
  related_id text,
  mime_type text,
  file_type text,
  file_size bigint,
  file_name text,
  created_at timestamptz not null default now()
);

alter table public.qc_evidence
  add column if not exists bucket text not null default 'qc-evidence',
  add column if not exists storage_path text,
  add column if not exists public_url text,
  add column if not exists signed_url text,
  add column if not exists uploaded_by uuid,
  add column if not exists related_type text,
  add column if not exists related_id text,
  add column if not exists mime_type text,
  add column if not exists file_type text,
  add column if not exists file_size bigint,
  add column if not exists file_name text,
  add column if not exists created_at timestamptz not null default now();

create index if not exists idx_facility_rooms_slug on public.facility_rooms (slug);
create index if not exists idx_facility_devices_room_id on public.facility_devices (room_id);
create index if not exists idx_facility_devices_device_type on public.facility_devices (device_type);
create index if not exists idx_temperature_logs_device_id_007 on public.temperature_logs (device_id);
create index if not exists idx_temperature_logs_created_at_007 on public.temperature_logs (created_at desc);
create index if not exists idx_facility_alerts_status_007 on public.facility_alerts (status);
create index if not exists idx_qc_evidence_related_007 on public.qc_evidence (related_type, related_id);

with rooms(name, slug) as (
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
from rooms
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
      and existing.slug = r.slug || '-' || u.device_type
  );

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'storage' and tablename = 'objects' and policyname = 'qc evidence public read'
  ) then
    create policy "qc evidence public read"
    on storage.objects for select
    using (bucket_id = 'qc-evidence');
  end if;
end $$;
