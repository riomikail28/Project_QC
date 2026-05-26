-- QC concurrency lock and inspection history metadata.
-- Additive only: keeps existing reports and batch flow intact.

alter table if exists public.qc_reports
  add column if not exists inspection_round integer not null default 1;

alter table if exists public.qc_reports
  add column if not exists parent_inspection uuid;

alter table if exists public.qc_reports
  add column if not exists is_active boolean not null default false;

alter table if exists public.qc_reports
  add column if not exists completed_at timestamptz;

create index if not exists idx_qc_reports_active_batch_id_023
  on public.qc_reports (batch_id, is_active, created_at desc);

create index if not exists idx_qc_reports_active_batch_code_023
  on public.qc_reports (batch_code, is_active, created_at desc);

create index if not exists idx_qc_reports_parent_inspection_023
  on public.qc_reports (parent_inspection);

create index if not exists idx_qc_reports_round_023
  on public.qc_reports (batch_id, inspection_round desc);
