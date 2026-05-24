-- Daily staff temperature monitoring schedule metadata.
-- Additive only: keeps existing facility_logs and temperature_logs data intact.

alter table if exists public.facility_logs
  add column if not exists monitoring_date date,
  add column if not exists slot_time time,
  add column if not exists schedule_status text,
  add column if not exists submitted_at timestamptz,
  add column if not exists is_late boolean default false;

alter table if exists public.temperature_logs
  add column if not exists monitoring_date date,
  add column if not exists slot_time time,
  add column if not exists schedule_status text,
  add column if not exists submitted_at timestamptz,
  add column if not exists is_late boolean default false;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'facility_logs_schedule_status_allowed_019'
      and conrelid = 'public.facility_logs'::regclass
  ) then
    alter table public.facility_logs
      add constraint facility_logs_schedule_status_allowed_019
      check (schedule_status is null or schedule_status in ('completed', 'late'));
  end if;

  if not exists (
    select 1
    from pg_constraint
    where conname = 'temperature_logs_schedule_status_allowed_019'
      and conrelid = 'public.temperature_logs'::regclass
  ) then
    alter table public.temperature_logs
      add constraint temperature_logs_schedule_status_allowed_019
      check (schedule_status is null or schedule_status in ('completed', 'late'));
  end if;
end $$;

create index if not exists idx_facility_logs_monitoring_schedule_019
on public.facility_logs (monitoring_date, slot_time, recorded_at desc);

create index if not exists idx_facility_logs_staff_schedule_019
on public.facility_logs (staff_id, monitoring_date, slot_time);

create index if not exists idx_temperature_logs_monitoring_schedule_019
on public.temperature_logs (monitoring_date, slot_time, recorded_at desc);
