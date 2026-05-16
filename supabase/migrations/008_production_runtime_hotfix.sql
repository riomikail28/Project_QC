-- Runtime production hotfix after facility migration.
-- Safe to run after 007, even if 007 was already applied before these fixes.

alter table if exists public.facility_logs
  add column if not exists zone text,
  add column if not exists device_type text,
  add column if not exists temperature numeric,
  add column if not exists status text,
  add column if not exists notes text,
  add column if not exists threshold_c numeric,
  add column if not exists is_abnormal boolean not null default false;

update public.facility_logs
set
  zone = coalesce(zone, 'QC Area'),
  device_type = coalesce(device_type, 'room'),
  temperature = coalesce(temperature, temperature_c),
  status = coalesce(status, case when coalesce(is_normal, true) then 'pass' else 'fail' end),
  notes = coalesce(notes, reason);

alter table if exists public.facility_logs
  alter column zone drop not null,
  alter column device_type drop not null;

alter table if exists public.production_batches
  add column if not exists product_name text,
  add column if not exists expired_date date,
  add column if not exists created_by uuid,
  add column if not exists photo_url text,
  add column if not exists storage_path text;
