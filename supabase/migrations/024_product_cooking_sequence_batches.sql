-- Product cooking-order batch metadata.
-- 1 batch = 1 cooking process for a product on a production date.

alter table if exists public.production_batches
  add column if not exists batch_sequence integer;

alter table if exists public.production_batches
  add column if not exists cook_name text;

alter table if exists public.production_batches
  add column if not exists quantity numeric(12,2);

alter table if exists public.production_batches
  add column if not exists production_shift text;

create index if not exists idx_production_batches_product_date_sequence_024
  on public.production_batches (product_id, production_date, batch_sequence desc);

create index if not exists idx_production_batches_code_date_024
  on public.production_batches (batch_code, production_date);
