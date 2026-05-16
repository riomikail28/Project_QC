-- Final production sync contract for staff/admin data flow.
-- Idempotent and additive only.

alter table if exists public.facility_rooms
  add column if not exists slug text,
  add column if not exists description text,
  add column if not exists is_active boolean default true,
  add column if not exists created_at timestamptz default now(),
  add column if not exists updated_at timestamptz default now();

alter table if exists public.facility_devices
  add column if not exists room_id uuid,
  add column if not exists name text,
  add column if not exists slug text,
  add column if not exists device_type text,
  add column if not exists type text,
  add column if not exists target_temperature numeric,
  add column if not exists threshold_temp numeric,
  add column if not exists min_temperature numeric,
  add column if not exists max_temperature numeric,
  add column if not exists is_active boolean default true,
  add column if not exists created_at timestamptz default now(),
  add column if not exists updated_at timestamptz default now();

alter table if exists public.facility_logs
  add column if not exists room_id uuid,
  add column if not exists device_id uuid,
  add column if not exists staff_id uuid,
  add column if not exists temperature_c numeric,
  add column if not exists threshold_c numeric,
  add column if not exists humidity_rh numeric,
  add column if not exists is_normal boolean,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists notes text,
  add column if not exists status text,
  add column if not exists device_type text,
  add column if not exists recorded_at timestamptz default now(),
  add column if not exists created_at timestamptz default now();

alter table if exists public.temperature_logs
  add column if not exists room_id uuid,
  add column if not exists device_id uuid,
  add column if not exists staff_id uuid,
  add column if not exists zone text,
  add column if not exists device_type text,
  add column if not exists device_name text,
  add column if not exists temperature numeric,
  add column if not exists temperature_c numeric,
  add column if not exists threshold_c numeric,
  add column if not exists status text,
  add column if not exists is_abnormal boolean default false,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists notes text,
  add column if not exists facility_log_id uuid,
  add column if not exists recorded_at timestamptz default now(),
  add column if not exists created_at timestamptz default now();

alter table if exists public.qc_reports
  add column if not exists batch_code text,
  add column if not exists product_name text,
  add column if not exists staff_id uuid,
  add column if not exists inspector_name text,
  add column if not exists status text,
  add column if not exists approval_status text default 'pending',
  add column if not exists barcode text,
  add column if not exists notes text,
  add column if not exists temperature numeric,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists product_photo_url text,
  add column if not exists product_storage_path text,
  add column if not exists created_at timestamptz default now(),
  add column if not exists updated_at timestamptz default now();

create table if not exists public.qc_findings (
  id uuid primary key default gen_random_uuid(),
  staff_id uuid,
  reason text not null,
  photo_url text,
  storage_path text,
  status text default 'finding',
  approval_status text default 'pending',
  created_at timestamptz not null default now(),
  updated_at timestamptz default now()
);

create table if not exists public.qc_evidence (
  id uuid primary key default gen_random_uuid(),
  file_name text,
  file_type text,
  mime_type text,
  file_size bigint,
  bucket text not null default 'qc-evidence',
  storage_path text,
  public_url text,
  signed_url text,
  uploaded_by uuid,
  related_type text,
  related_id text,
  created_at timestamptz not null default now()
);

create table if not exists public.approvals (
  id uuid primary key default gen_random_uuid(),
  related_type text,
  related_id text,
  status text not null default 'pending',
  requested_by uuid,
  requester_id uuid,
  approved_by uuid,
  approved_at timestamptz,
  comment text,
  rejection_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz default now()
);

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid,
  actor_name text,
  action text not null,
  entity_type text,
  entity_id text,
  before_data jsonb,
  after_data jsonb,
  metadata jsonb default '{}'::jsonb,
  ip_address text,
  user_agent text,
  created_at timestamptz not null default now()
);

create index if not exists idx_facility_rooms_active_012 on public.facility_rooms (is_active, name);
create index if not exists idx_facility_devices_room_type_012 on public.facility_devices (room_id, device_type, is_active);
create index if not exists idx_facility_logs_staff_date_012 on public.facility_logs (staff_id, recorded_at desc);
create index if not exists idx_facility_logs_room_device_date_012 on public.facility_logs (room_id, device_id, recorded_at desc);
create index if not exists idx_temperature_logs_staff_date_012 on public.temperature_logs (staff_id, created_at desc);
create index if not exists idx_temperature_logs_status_date_012 on public.temperature_logs (status, created_at desc);
create index if not exists idx_qc_reports_staff_date_012 on public.qc_reports (staff_id, created_at desc);
create index if not exists idx_qc_reports_approval_date_012 on public.qc_reports (approval_status, created_at desc);
create index if not exists idx_qc_findings_staff_date_012 on public.qc_findings (staff_id, created_at desc);
create index if not exists idx_qc_evidence_related_012 on public.qc_evidence (related_type, related_id);
create index if not exists idx_approvals_status_date_012 on public.approvals (status, created_at desc);
create index if not exists idx_approvals_related_012 on public.approvals (related_type, related_id);
create index if not exists idx_audit_logs_actor_date_012 on public.audit_logs (actor_id, created_at desc);
create index if not exists idx_audit_logs_action_date_012 on public.audit_logs (action, created_at desc);
