-- Massive QC production stabilization.
-- Additive only: keeps existing data and API-compatible tables intact.

create extension if not exists pgcrypto;

insert into storage.buckets (id, name, public)
values ('qc-evidence', 'qc-evidence', true)
on conflict (id) do update set
  name = excluded.name,
  public = true;

create table if not exists public.staff_accounts (
  id uuid primary key default gen_random_uuid(),
  username text not null unique,
  password_hash text,
  full_name text,
  role text not null default 'qc_staff',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  staff_account_id uuid references public.staff_accounts(id) on delete set null,
  email text unique,
  full_name text,
  role text not null default 'qc_staff',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.production_batches (
  id uuid primary key default gen_random_uuid(),
  batch_code text not null unique,
  product_id uuid,
  product_name text,
  production_date date,
  expired_date date,
  status text not null default 'pending',
  created_by uuid,
  storage_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table if exists public.production_batches
  add column if not exists batch_code text,
  add column if not exists product_id uuid,
  add column if not exists product_name text,
  add column if not exists production_date date,
  add column if not exists expired_date date,
  add column if not exists status text not null default 'pending',
  add column if not exists created_by uuid,
  add column if not exists storage_path text,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

alter table if exists public.qc_reports
  add column if not exists batch_id uuid,
  add column if not exists product_id uuid,
  add column if not exists barcode text,
  add column if not exists ccp_stage text,
  add column if not exists temperature numeric(6,2),
  add column if not exists notes text,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists temperature_storage_path text,
  add column if not exists barcode_storage_path text,
  add column if not exists product_storage_path text,
  add column if not exists updated_at timestamptz not null default now();

alter table if exists public.temperature_logs
  add column if not exists room_id uuid,
  add column if not exists device_id uuid,
  add column if not exists status text,
  add column if not exists notes text,
  add column if not exists storage_path text,
  add column if not exists updated_at timestamptz not null default now();

alter table if exists public.facility_logs
  add column if not exists staff_id uuid,
  add column if not exists reason text,
  add column if not exists photo_url text,
  add column if not exists storage_path text;

create table if not exists public.qc_evidence (
  id uuid primary key default gen_random_uuid(),
  file_name text,
  file_type text,
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

create table if not exists public.approvals (
  id uuid primary key default gen_random_uuid(),
  related_type text not null default 'qc_report',
  related_id text,
  status text not null default 'pending',
  comment text,
  requested_by uuid,
  approved_by uuid,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.facility_devices (
  id uuid primary key default gen_random_uuid(),
  room_id uuid,
  name text not null,
  type text not null,
  threshold_temp numeric(6,2),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.facility_alerts (
  id uuid primary key default gen_random_uuid(),
  log_id uuid,
  device_id uuid,
  zone text,
  temperature_c numeric(6,2),
  threshold_c numeric(6,2),
  severity text not null default 'warning',
  status text not null default 'open',
  description text,
  corrective_action text,
  resolved_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_staff_accounts_role_active on public.staff_accounts (role, is_active);
create index if not exists idx_production_batches_batch_code on public.production_batches (batch_code);
create index if not exists idx_production_batches_status_created_at on public.production_batches (status, created_at desc);
create index if not exists idx_qc_reports_staff_created_at on public.qc_reports (staff_id, created_at desc);
create index if not exists idx_qc_reports_batch_created_at on public.qc_reports (batch_id, created_at desc);
create index if not exists idx_qc_reports_approval_status on public.qc_reports (approval_status, created_at desc);
create index if not exists idx_temperature_logs_staff_created_at on public.temperature_logs (staff_id, created_at desc);
create index if not exists idx_temperature_logs_room_device_created_at on public.temperature_logs (room_id, device_id, created_at desc);
create index if not exists idx_qc_evidence_related on public.qc_evidence (related_type, related_id);
create index if not exists idx_qc_evidence_uploaded_by on public.qc_evidence (uploaded_by, created_at desc);
create index if not exists idx_approvals_status_created_at on public.approvals (status, created_at desc);
create index if not exists idx_audit_logs_actor_created_at on public.audit_logs (actor_id, created_at desc);

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

  if not exists (
    select 1 from pg_policies
    where schemaname = 'storage' and tablename = 'objects' and policyname = 'qc evidence authenticated upload'
  ) then
    create policy "qc evidence authenticated upload"
    on storage.objects for insert
    with check (bucket_id = 'qc-evidence');
  end if;
end $$;
