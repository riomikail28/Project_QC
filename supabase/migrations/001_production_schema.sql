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
-- Index for temperature_logs will be created in separate migration to avoid dependency issues
-- create index if not exists idx_temperature_logs_recorded_at on public.temperature_logs (recorded_at desc);
create index if not exists idx_temperature_logs_zone on public.temperature_logs (zone, device_type);
create index if not exists idx_barcode_labels_value on public.barcode_labels (barcode_value);
create index if not exists idx_audit_logs_created_at on public.audit_logs (created_at desc);
create index if not exists idx_staff_activity_created_at on public.staff_activity (created_at desc);

insert into storage.buckets (id, name, public)
values
  ('qc-evidence', 'qc-evidence', false)
on conflict (id) do nothing;
