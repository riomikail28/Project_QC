-- Daily reporting and facility log schema compatibility.
-- The application no longer inserts device_type into facility_logs; device type
-- is resolved through facility_devices by device_id.

alter table if exists public.facility_logs
  add column if not exists room_id uuid,
  add column if not exists device_id uuid,
  add column if not exists staff_id uuid,
  add column if not exists temperature_c numeric,
  add column if not exists threshold_c numeric,
  add column if not exists is_normal boolean,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists notes text,
  add column if not exists humidity_rh numeric,
  add column if not exists recorded_at timestamptz default now(),
  add column if not exists created_at timestamptz default now();

create table if not exists public.qc_findings (
  id uuid primary key default gen_random_uuid(),
  staff_id uuid,
  reason text not null,
  photo_url text,
  storage_path text,
  status text default 'finding',
  approval_status text default 'pending',
  created_at timestamptz not null default now()
);

alter table if exists public.qc_findings
  add column if not exists staff_id uuid,
  add column if not exists reason text,
  add column if not exists photo_url text,
  add column if not exists storage_path text,
  add column if not exists status text default 'finding',
  add column if not exists approval_status text default 'pending',
  add column if not exists created_at timestamptz default now();

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

alter table if exists public.qc_evidence
  add column if not exists file_name text,
  add column if not exists file_type text,
  add column if not exists mime_type text,
  add column if not exists file_size bigint,
  add column if not exists bucket text default 'qc-evidence',
  add column if not exists storage_path text,
  add column if not exists public_url text,
  add column if not exists signed_url text,
  add column if not exists uploaded_by uuid,
  add column if not exists related_type text,
  add column if not exists related_id text,
  add column if not exists created_at timestamptz default now();

create index if not exists idx_facility_logs_recorded_at_010 on public.facility_logs (recorded_at desc);
create index if not exists idx_facility_logs_staff_id_010 on public.facility_logs (staff_id);
create index if not exists idx_qc_findings_created_at_010 on public.qc_findings (created_at desc);
create index if not exists idx_qc_findings_staff_id_010 on public.qc_findings (staff_id);
create index if not exists idx_qc_evidence_created_at_010 on public.qc_evidence (created_at desc);
create index if not exists idx_qc_evidence_uploaded_by_010 on public.qc_evidence (uploaded_by);
create index if not exists idx_qc_evidence_related_type_010 on public.qc_evidence (related_type);
create index if not exists idx_qc_evidence_related_010 on public.qc_evidence (related_type, related_id);
