# Supabase Schema Contract Final

## Facility

- `facility_rooms`: room master data for monitoring pages and admin facility CRUD.
- `facility_devices`: room unit master data. `device_type` is `room_temp`, `chiller`, or `freezer`.
- `facility_logs`: primary staff temperature submissions.
- `temperature_logs`: compatibility/reporting copy of temperature submissions.
- `facility_alerts`: abnormal temperature alerts.

Endpoints:
- `GET /api/facility/structure`
- `POST /api/monitoring/log`
- `GET /api/admin/reports/temperature`
- `GET|POST|PUT|DELETE /api/admin/facility/rooms`
- `GET|POST|PUT|DELETE /api/admin/facility/devices`

Frontend:
- `frontend/staff/monitoring.html`
- `frontend/js/monitoring.js`
- `frontend/admin/admin_panel.html`
- `frontend/js/admin_app.js`

## Staff QC

- `qc_reports`: one staff inspection/QC check per SKU/barcode submission.
- `qc_findings`: QC Temuan submissions.
- `qc_evidence`: storage metadata for uploaded evidence.
- `production_batches`: optional batch references.
- `barcode_labels`: barcode traceability.

Endpoints:
- `POST /api/inspection/submit`
- `POST /api/qc/findings`
- `GET /api/admin/reports/inspection`
- `GET /api/admin/reports/findings`
- `GET /api/admin/reports/evidence`

Frontend:
- `frontend/staff/inspection.html`
- `frontend/staff/dashboard.html`
- `frontend/js/inspection.js`

## Admin

- `approvals`: approval queue for QC reports.
- `audit_logs`: staff/admin activity trail.
- `staff_activity`: staff activity source when present.
- `users` and `staff_accounts`: authentication/profile identity.

Endpoints:
- `GET /api/admin/approvals`
- `POST /api/admin/approvals/{id}/approve`
- `POST /api/admin/approvals/{id}/reject`
- `GET /api/admin/audit-logs`
- `GET /api/admin/reports/daily`
- `GET /api/admin/export/daily-report`

Legacy tables `rooms` and `storage_units` are not used for new staff/admin sync features.
