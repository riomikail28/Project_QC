-- Optional pH, Brix, and TDS values on production batch creation.
-- Idempotent and safe for existing production data.

alter table if exists public.production_batches
  add column if not exists ph_value numeric,
  add column if not exists brix_value numeric,
  add column if not exists tds_value numeric,
  add column if not exists ph_status text,
  add column if not exists brix_status text,
  add column if not exists tds_status text,
  add column if not exists parameter_notes text,
  add column if not exists parameter_checked_by uuid,
  add column if not exists parameter_checked_at timestamptz;

create index if not exists idx_production_batches_parameter_checked_at
  on public.production_batches (parameter_checked_at desc);
