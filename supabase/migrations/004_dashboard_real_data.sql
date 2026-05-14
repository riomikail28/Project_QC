-- Dashboard real-data indexes.
-- Safe to run on existing Supabase projects with partially migrated schemas.

create index if not exists idx_production_batches_production_date
on public.production_batches (production_date);

create index if not exists idx_production_batches_created_at
on public.production_batches (created_at desc);

create index if not exists idx_production_batches_status
on public.production_batches (status);

create index if not exists idx_qc_reports_staff_id
on public.qc_reports (staff_id);

create index if not exists idx_qc_reports_batch_id
on public.qc_reports (batch_id);

create index if not exists idx_qc_reports_created_status
on public.qc_reports (created_at desc, status, approval_status);

create index if not exists idx_barcode_labels_created_at
on public.barcode_labels (created_at desc);

create index if not exists idx_barcode_labels_staff_id
on public.barcode_labels (staff_id);

create index if not exists idx_staff_activity_staff_id
on public.staff_activity (staff_id);

do $$
begin
  if to_regclass('public.temperature_logs') is not null then
    if exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'temperature_logs'
        and column_name = 'created_at'
    ) then
      create index if not exists idx_temperature_logs_created_at_dashboard
      on public.temperature_logs (created_at desc);
    end if;

    if exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'temperature_logs'
        and column_name = 'recorded_at'
    ) then
      create index if not exists idx_temperature_logs_recorded_at_dashboard
      on public.temperature_logs (recorded_at desc);
    end if;

    if exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'temperature_logs'
        and column_name = 'staff_id'
    ) then
      create index if not exists idx_temperature_logs_staff_id
      on public.temperature_logs (staff_id);
    end if;

    if exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'temperature_logs'
        and column_name = 'batch_id'
    ) then
      create index if not exists idx_temperature_logs_batch_id
      on public.temperature_logs (batch_id);
    end if;

    if exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'temperature_logs'
        and column_name = 'device_id'
    ) then
      create index if not exists idx_temperature_logs_device_id
      on public.temperature_logs (device_id);
    end if;
  end if;

  if to_regclass('public.facility_logs') is not null then
    if exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'facility_logs'
        and column_name = 'recorded_at'
    ) then
      create index if not exists idx_facility_logs_recorded_at_dashboard
      on public.facility_logs (recorded_at desc);
    end if;

    if exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'facility_logs'
        and column_name = 'staff_id'
    ) then
      create index if not exists idx_facility_logs_staff_id
      on public.facility_logs (staff_id);
    end if;

    if exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'facility_logs'
        and column_name = 'device_id'
    ) then
      create index if not exists idx_facility_logs_device_id
      on public.facility_logs (device_id);
    end if;

    if exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'facility_logs'
        and column_name = 'room_id'
    ) then
      create index if not exists idx_facility_logs_room_id
      on public.facility_logs (room_id);
    end if;
  end if;

  if to_regclass('public.facility_alerts') is not null then
    if exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'facility_alerts'
        and column_name = 'status'
    ) and exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'facility_alerts'
        and column_name = 'created_at'
    ) then
      create index if not exists idx_facility_alerts_status_created_at
      on public.facility_alerts (status, created_at desc);
    elsif exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'facility_alerts'
        and column_name = 'status'
    ) then
      create index if not exists idx_facility_alerts_status
      on public.facility_alerts (status);
    end if;
  end if;

  if to_regclass('public.approvals') is not null then
    if exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'approvals'
        and column_name = 'status'
    ) and exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'approvals'
        and column_name = 'created_at'
    ) then
      create index if not exists idx_approvals_status_created_at
      on public.approvals (status, created_at desc);
    elsif exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'approvals'
        and column_name = 'status'
    ) then
      create index if not exists idx_approvals_status
      on public.approvals (status);
    end if;
  end if;
end $$;
