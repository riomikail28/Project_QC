-- QC Check field flow for Cooking Check and Final Check.
-- Idempotent migration for existing production Supabase projects.

alter table if exists public.qc_reports
  add column if not exists qc_stage text;

alter table if exists public.qc_reports
  add column if not exists label_photo_url text;

alter table if exists public.qc_reports
  add column if not exists label_storage_path text;

alter table if exists public.qc_reports
  add column if not exists cooking_photo_url text;

alter table if exists public.qc_reports
  add column if not exists cooking_storage_path text;

alter table if exists public.qc_reports
  add column if not exists barcode_storage_path text;

create index if not exists idx_qc_reports_batch_stage_created
  on public.qc_reports (batch_id, qc_stage, created_at desc);

create index if not exists idx_qc_reports_batch_code_stage_created
  on public.qc_reports (batch_code, qc_stage, created_at desc);
