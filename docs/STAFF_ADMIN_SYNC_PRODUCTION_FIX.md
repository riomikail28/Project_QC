# Staff/Admin Sync Production Fix

## Root Cause

- Photo upload failed because backend Storage used a generic Supabase client and could run without a service-role capable key.
- Chiller/freezer logging was not fully aligned with room/device master data and `temperature_logs` lacked the same relation/photo fields as `facility_logs`.
- Admin reports mixed fallback views and real tables, so staff submissions could be saved without appearing consistently in monitoring, approvals, audit, and daily reports.

## Fixed Flow

- Backend upload uses `get_supabase_admin_client()` with `SUPABASE_SERVICE_ROLE_KEY`, falling back only to backend `SUPABASE_KEY`.
- Inspection submit accepts `FormData`, uploads photos to `qc-evidence`, writes `qc_reports`, `qc_evidence`, `approvals`, and `audit_logs`.
- Monitoring submit uses one flow for `room_temp`, `chiller`, and `freezer`, writes `facility_logs`, `temperature_logs`, optional `qc_evidence`, alerts, and audit.
- Admin daily reports combine temperature logs, inspection reports, findings, evidence, and pending approvals.
- Facility room/device CRUD writes real Supabase tables and audit entries.

## Endpoints

- `POST /api/inspection/submit`
- `POST /api/monitoring/log`
- `POST /api/qc/findings`
- `GET /api/admin/reports/temperature?date=YYYY-MM-DD`
- `GET /api/admin/reports/daily?date=YYYY-MM-DD`
- `GET /api/admin/export/daily-report?date=YYYY-MM-DD&type=csv`
- `GET /api/admin/approvals`
- `POST /api/admin/approvals/{id}/approve`
- `POST /api/admin/approvals/{id}/reject`
- `GET /api/admin/audit-logs?date=YYYY-MM-DD`
- `GET|POST|PUT|DELETE /api/admin/facility/rooms`
- `GET|POST|PUT|DELETE /api/admin/facility/devices`

## Tables

- `qc_reports`
- `qc_findings`
- `qc_evidence`
- `approvals`
- `audit_logs`
- `facility_rooms`
- `facility_devices`
- `facility_logs`
- `temperature_logs`
- `facility_alerts`

## Migration

Apply:

```bash
supabase db push
```

or run `supabase/migrations/011_full_staff_admin_sync_fix.sql` in the Supabase SQL editor.

## Vercel Checklist

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET=qc-evidence`
- `JWT_SECRET_KEY`
- `CORS_ORIGINS=https://project-qc-mu.vercel.app`

## QA

Run before deploy:

```bash
python -m pytest -q
python -m compileall -q backend tests
```
