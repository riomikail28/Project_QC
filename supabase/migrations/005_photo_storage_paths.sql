insert into storage.buckets (id, name, public)
values ('qc-evidence', 'qc-evidence', true)
on conflict (id) do update set
  name = excluded.name,
  public = true;

alter table if exists public.production_batches
  add column if not exists storage_path text;

alter table if exists public.production_batch_logs
  add column if not exists storage_path text;

alter table if exists public.facility_logs
  add column if not exists storage_path text;

alter table if exists public.temperature_logs
  add column if not exists storage_path text;

alter table if exists public.qc_reports
  add column if not exists temperature_storage_path text,
  add column if not exists barcode_storage_path text,
  add column if not exists product_storage_path text;

create table if not exists public.qc_findings (
  id uuid primary key default gen_random_uuid(),
  staff_id uuid,
  reason text not null,
  photo_url text,
  storage_path text,
  created_at timestamptz not null default now()
);

alter table if exists public.qc_findings
  add column if not exists staff_id uuid,
  add column if not exists reason text,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists created_at timestamptz not null default now();

create index if not exists idx_qc_findings_created_at
on public.qc_findings (created_at desc);
