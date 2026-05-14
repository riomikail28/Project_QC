create extension if not exists pgcrypto;

create table if not exists public.staff_activity (
  id uuid primary key default gen_random_uuid(),
  staff_id uuid,
  staff_name text,
  role text not null default 'staff',
  action text not null,
  ip_address text,
  user_agent text,
  created_at timestamptz not null default now()
);

create table if not exists public.products (
  id uuid primary key default gen_random_uuid(),
  product_code text not null unique,
  sku_code text unique,
  product_name text not null,
  ph_min numeric(8,2),
  ph_max numeric(8,2),
  brix_min numeric(8,2),
  brix_max numeric(8,2),
  tds_min numeric(10,2),
  tds_max numeric(10,2),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.qc_reports (
  id uuid primary key default gen_random_uuid(),
  batch_id uuid,
  batch_code text not null,
  product_id uuid,
  product_name text,
  staff_id uuid,
  inspector_name text,
  status text not null default 'pending' check (status in ('pass','warning','failed','pending','rejected')),
  approval_status text not null default 'pending' check (approval_status in ('pending','approved','rejected')),
  inspection_result jsonb not null default '{}'::jsonb,
  temperature_photo_url text,
  barcode_photo_url text,
  product_photo_url text,
  approved_by uuid,
  approved_at timestamptz,
  rejection_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.temperature_logs (
  id uuid primary key default gen_random_uuid(),
  device_type text not null check (device_type in ('freezer','chiller','room')),
  zone text not null,
  temperature_c numeric(6,2) not null,
  humidity_rh numeric(6,2),
  threshold_c numeric(6,2),
  is_abnormal boolean not null default false,
  photo_url text,
  staff_id uuid,
  batch_id uuid,
  recorded_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

alter table public.temperature_logs
  add column if not exists device_type text,
  add column if not exists zone text,
  add column if not exists temperature_c numeric(6,2),
  add column if not exists humidity_rh numeric(6,2),
  add column if not exists threshold_c numeric(6,2),
  add column if not exists is_abnormal boolean not null default false,
  add column if not exists photo_url text,
  add column if not exists staff_id uuid,
  add column if not exists batch_id uuid,
  add column if not exists recorded_at timestamptz not null default now(),
  add column if not exists created_at timestamptz not null default now();

update public.temperature_logs
set
  zone = coalesce(zone, 'QC Area'),
  device_type = coalesce(device_type, 'room'),
  temperature_c = coalesce(temperature_c, 0),
  is_abnormal = coalesce(is_abnormal, false)
where zone is null
   or device_type is null
   or temperature_c is null
   or is_abnormal is null;

create table if not exists public.barcode_labels (
  id uuid primary key default gen_random_uuid(),
  batch_id uuid,
  batch_code text,
  product_id uuid,
  product_name text,
  barcode_value text not null,
  barcode_photo_url text,
  staff_id uuid,
  staff_name text,
  created_at timestamptz not null default now()
);

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid,
  actor_name text,
  action text not null,
  entity_type text not null,
  entity_id text,
  before jsonb,
  after jsonb,
  ip_address text,
  user_agent text,
  created_at timestamptz not null default now()
);

create index if not exists idx_qc_reports_created_at on public.qc_reports (created_at desc);
create index if not exists idx_qc_reports_status on public.qc_reports (status, approval_status);
create index if not exists idx_products_active_code on public.products (is_active, product_code);
-- Index for temperature_logs will be created in separate migration to avoid dependency issues
-- create index if not exists idx_temperature_logs_recorded_at on public.temperature_logs (recorded_at desc);
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public'
      and table_name = 'temperature_logs'
      and column_name = 'zone'
  ) and exists (
    select 1 from information_schema.columns
    where table_schema = 'public'
      and table_name = 'temperature_logs'
      and column_name = 'device_type'
  ) then
    create index if not exists idx_temperature_logs_zone
    on public.temperature_logs (zone, device_type);
  end if;
end $$;
create index if not exists idx_barcode_labels_value on public.barcode_labels (barcode_value);
create index if not exists idx_audit_logs_created_at on public.audit_logs (created_at desc);
create index if not exists idx_staff_activity_created_at on public.staff_activity (created_at desc);

insert into storage.buckets (id, name, public)
values
  ('qc-evidence', 'qc-evidence', false)
on conflict (id) do nothing;
