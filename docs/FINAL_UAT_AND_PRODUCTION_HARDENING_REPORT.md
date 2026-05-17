# Final UAT And Production Hardening Report

## Release Context

Project sudah berada pada tahap release candidate untuk demo skripsi dan controlled production launch.

Validasi dilakukan pada codebase lokal dengan automated route/service tests, static frontend/security checks, dan release bug sweep. Live browser UAT di Vercel tetap perlu dijalankan oleh operator yang memiliki akun staff/admin production, karena kredensial production tidak tersedia di environment Codex.

## Flow Yang Diuji

### Staff Monitoring

Flow tervalidasi:

- Login staff protected by JWT middleware.
- Staff membuka monitoring dan mengambil `/api/facility/structure`.
- `room_id` dan `device_id` wajib UUID asli.
- Submit suhu ke `POST /api/monitoring/log`.
- Foto diupload ke bucket `qc-evidence`.
- Data masuk ke `facility_logs`, `temperature_logs`, `qc_evidence`, dan `audit_logs`.
- Admin membaca monitoring lewat `/api/admin/reports/temperature`.

Status: Pass via automated UAT/service tests.

### Staff Inspection

Flow tervalidasi:

- Staff submit SKU/barcode.
- `qc_status` menerima `pass`, `hold`, `fail`.
- Foto optional.
- Insert `qc_reports`.
- Create `approvals` status `pending`.
- Insert `qc_evidence` jika ada foto.
- Audit action `submit_inspection` dan `upload_inspection_photo`.
- Admin approval membaca pending report.

Status: Pass via automated UAT/service tests.

### Staff QC Finding

Flow tervalidasi:

- Staff submit finding.
- Foto optional.
- Insert `qc_findings`.
- Insert `qc_evidence` dengan `related_type=qc_finding`.
- Audit action `submit_finding` dan `upload_finding_photo`.
- Admin finding report membaca data real.

Status: Pass via automated UAT/service tests.

### Admin

Flow tervalidasi:

- Admin endpoint protected dengan `require_role("admin")`.
- Staff token ditolak dari admin reports/approval/audit/export.
- Monitoring report membaca data staff.
- Approval bisa approve/reject.
- Approval update sinkron ke `approvals` dan `qc_reports`.
- Audit trail dapat difilter tanggal/action/user.
- Daily report menggabungkan monitoring, inspection, finding, evidence, dan approvals.
- Export CSV memakai kolom production.
- Evidence preview memakai `photo_url`, signed URL, atau public URL dari `storage_path`.

Status: Pass via automated tests.

## Bug Yang Ditemukan

1. Beberapa tabel admin non-daily masih memakai horizontal scroll pada mobile.
2. Row QC reports, approvals, traceability, dan audit trail belum memiliki `data-label`, sehingga sulit dirender sebagai card/list mobile.

## Bug Yang Diperbaiki

1. CSS mobile admin table diperluas untuk semua `.enterprise-table` di bawah 860px.
2. Wrapper inline `overflow-x:auto` dioverride pada mobile agar tidak memaksa horizontal scroll.
3. Row admin utama diberi `data-label`:
   - QC Reports
   - Approvals
   - Audit Trail
   - Traceability
   - Daily Reports sudah existing

## Endpoint Yang Dites

- `GET /api/health/supabase`
- `GET /api/facility/structure`
- `POST /api/monitoring/log`
- `GET /api/admin/reports/temperature`
- `POST /api/inspection/submit`
- `GET /api/admin/reports/inspection`
- `POST /api/qc/findings`
- `GET /api/admin/reports/findings`
- `GET /api/admin/approvals`
- `POST /api/admin/approvals/{id}/approve`
- `POST /api/admin/approvals/{id}/reject`
- `GET /api/admin/audit-logs`
- `GET /api/admin/reports/daily`
- `GET /api/admin/export/daily-report?type=csv`
- `GET /js/config.js`

## Tabel Supabase Yang Tervalidasi

Monitoring:

- `facility_logs`
- `temperature_logs`
- `qc_evidence`
- `audit_logs`

Inspection:

- `qc_reports`
- `approvals`
- `qc_evidence`
- `audit_logs`

Finding:

- `qc_findings`
- `qc_evidence`
- `audit_logs`

Admin reporting:

- `facility_logs`
- `temperature_logs`
- `qc_reports`
- `qc_findings`
- `qc_evidence`
- `approvals`
- `audit_logs`

## Screenshot / QA Notes

No screenshot artifact was captured in this headless validation run.

QA notes:

- Evidence preview uses thumbnail + modal path.
- `storage_path` is not shown as the primary preview value.
- Empty database returns empty arrays/state, not fabricated staff/admin reports.
- Synthetic IDs such as `default-room-*` are rejected before Supabase insert.

## Mobile QA Status

Viewport targets:

- 320px: Pass by CSS contract, requires final browser spot-check.
- 375px: Pass by CSS contract, requires final browser spot-check.
- 390px: Pass by CSS contract, requires final browser spot-check.
- 430px: Pass by CSS contract, requires final browser spot-check.
- 768px: Pass by CSS contract.
- 1024px: Desktop/tablet layout preserved.

Validated:

- Staff bottom navigation exists through global styles.
- Upload controls keep image-only/file-size guard.
- Admin tables convert to card/list style on mobile.
- Horizontal table scroll is removed for admin release-critical tables on mobile.

## Security QA Status

Validated:

- `/js/config.js` exposes only public Supabase config.
- `SUPABASE_SERVICE_ROLE_KEY` is not exposed to frontend.
- `JWT_SECRET_KEY` is not exposed to frontend.
- Admin release routes reject staff tokens.
- Upload client accepts only JPG, PNG, WEBP.
- Upload size limit is enforced.
- Frontend rejects service-role/CLI Supabase keys if accidentally injected as public key.

Manual production checks still required:

- Confirm logout clears production session cookies in browser.
- Confirm expired session redirects to login on deployed Vercel domain.

## Performance QA Status

Local automated tests do not show infinite fetch loops.

Expected release targets:

- Staff dashboard: under 2 seconds with normal Supabase latency.
- Admin panel: under 3 seconds for standard report sizes.
- Daily report: under 3 seconds for controlled launch dataset.
- Upload photo: depends on file size and Supabase Storage latency; client and backend limits are active.

## Production Readiness

Backend: 9/10

Frontend: 8.5/10

Database: 9/10

Storage: 9/10

Security: 8.5/10

Mobile UX: 8/10

Admin Reporting: 9/10

Production Ready: 8.5/10

## Final Status

STATUS:
READY FOR DEMO SKRIPSI AND CONTROLLED PRODUCTION LAUNCH

Condition:

- Run one final live browser UAT on Vercel with real staff/admin accounts.
- Use a small controlled production dataset during launch.
- Keep `/api/health/supabase` as the first diagnostic check before demo.
