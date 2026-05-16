# Monitoring, Inspection, and Reporting Fix

## Root Cause

Production Supabase rejected monitoring uploads because `facility_logs` insert payloads included `device_type`. Production does not expose that column in the schema cache. The backend now stores only canonical `facility_logs` fields and resolves device type from `facility_devices` through `device_id`.

## Monitoring Fix

- `POST /api/monitoring/log` inserts only `room_id`, `device_id`, `staff_id`, `temperature_c`, `threshold_c`, `is_normal`, `photo_url`, `storage_path`, `notes`, `humidity_rh`, `recorded_at`, and `created_at`.
- `temperature` and `threshold` request fields are mapped to `temperature_c` and `threshold_c`.
- `device_type`, `status`, and legacy `temperature` are not inserted into `facility_logs`.
- A best-effort `temperature_logs` insert is still written for dashboard compatibility.
- Photo metadata is recorded in `qc_evidence` when a photo URL/storage path exists.

## QC Findings Fix

- QC findings continue to use `qc_findings` as the primary table.
- Uploaded finding photos are recorded in `qc_evidence` with `related_type = qc_finding`.
- Admin can read findings through `GET /api/admin/reports/findings?date=YYYY-MM-DD`.

## Simplified Inspection Flow

`frontend/staff/inspection.html` is now a mobile-first quick QC form:

- SKU/barcode input
- PASS/HOLD/FAIL selector
- optional photo evidence
- optional notes
- optional temperature

Each submit creates a new `qc_reports` row. Manual SKUs are allowed, notes/photo are optional, and no active batch is required. If no batch code is provided, the backend generates `QC-YYYYMMDD-HHMMSS`.

## Admin Reporting Endpoints

- `GET /api/admin/reports/temperature?date=YYYY-MM-DD`
- `GET /api/admin/reports/inspection?date=YYYY-MM-DD`
- `GET /api/admin/reports/findings?date=YYYY-MM-DD`
- `GET /api/admin/reports/evidence?date=YYYY-MM-DD`
- `GET /api/admin/reports/daily?date=YYYY-MM-DD`
- `GET /api/admin/export/daily-report?date=YYYY-MM-DD&type=csv`

The existing `/api/v1/admin/...` routes remain available for the current admin frontend.

## Export CSV

The daily export returns `text/csv` with filename `qc_daily_report_YYYY-MM-DD.csv`. Excel can open the CSV directly.

## Files Changed

- `backend/services/monitoring_service.py`
- `backend/services/inspection_service.py`
- `backend/services/qc_service.py`
- `backend/services/admin_service.py`
- `backend/api/admin_routes.py`
- `backend/api/qc_routes.py`
- `backend/__init__.py`
- `frontend/staff/inspection.html`
- `frontend/js/inspection.js`
- `frontend/js/monitoring.js`
- `frontend/js/admin_app.js`
- `frontend/admin/admin_panel.html`
- `frontend/styles/qc.css`
- `frontend/css/admin_enterprise.css`
- `supabase/migrations/010_reporting_and_facility_log_fix.sql`

## Manual Test

1. Login as staff.
2. Open Monitoring, select room/device, input temperature, optionally upload a photo, then submit.
3. Confirm success toast: `Log suhu berhasil disimpan`.
4. Open QC Check, enter SKU/barcode, select status, optionally add photo/notes, then submit.
5. Submit a QC finding with a reason and optional photo.
6. Login as admin and open `Reports Harian`.
7. Pick today, reload, preview evidence photos, and export CSV.
