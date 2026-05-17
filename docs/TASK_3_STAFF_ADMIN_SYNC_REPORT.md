# Task 3 Staff Admin Sync Report

## Scope

Task ini menutup sinkronisasi end-to-end:

- Staff submit monitoring suhu dan foto.
- Staff submit QC inspection dan foto.
- Staff submit QC finding.
- Admin melihat monitoring, QC reports, approvals, audit trail, daily report, evidence preview, dan export CSV.

Tidak ada dummy data baru. Jika tabel kosong, endpoint mengembalikan empty state.

## Supabase Env Validation

Backend production wajib memakai:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET=qc-evidence`

Frontend hanya boleh menerima:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

`GET /api/health/supabase` menjadi diagnosis utama. Jika koneksi, schema, storage, atau key gagal, endpoint mengembalikan HTTP 503 dan pesan jelas. Tidak ada response 200 palsu saat Supabase gagal.

## Endpoint Yang Diperbaiki

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

## Monitoring Flow

`POST /api/monitoring/log` menerima `room_id` dan `device_id` UUID asli dari `facility_rooms` dan `facility_devices`.

Backend:

- Validasi UUID sebelum insert.
- Ambil room/device dari Supabase.
- Hitung status temperature.
- Upload foto ke bucket `qc-evidence`.
- Insert `facility_logs`.
- Insert compatibility row ke `temperature_logs`.
- Insert `qc_evidence`.
- Insert audit action `submit_temperature` dan `upload_temperature_photo`.
- Buat alert jika abnormal.

Admin membaca data lewat `GET /api/admin/reports/temperature`.

## Inspection Flow

`POST /api/inspection/submit` menerima SKU/barcode dan `qc_status` (`pass`, `hold`, `fail`).

Backend:

- Insert `qc_reports`.
- Upload foto jika ada.
- Insert `qc_evidence` dengan `related_type=qc_report`.
- Create row `approvals` dengan status `pending`.
- Insert audit action `submit_inspection` dan `upload_inspection_photo`.

Admin membaca data lewat reports, approvals, dan daily report.

## Finding Flow

`POST /api/qc/findings`:

- Insert `qc_findings`.
- Upload foto jika ada.
- Insert `qc_evidence` dengan `related_type=qc_finding`.
- Insert audit action `submit_finding` dan `upload_finding_photo`.

Admin membaca data lewat `GET /api/admin/reports/findings`.

## Approval Flow

Approval endpoint sekarang robust untuk menerima approval id maupun report id.

Approve:

- Update `approvals.status=approved`.
- Update `qc_reports.approval_status=approved`.
- Set `approved_by` dan `approved_at`.
- Insert audit `approve_qc`.

Reject:

- Update `approvals.status=rejected`.
- Update `qc_reports.approval_status=rejected`.
- Set rejection reason/comment.
- Insert audit `reject_qc`.

## Audit Trail

`GET /api/admin/audit-logs` mendukung filter:

- `date`
- `action`
- `user` / `staff` / `staff_id`

Aktivitas penting staff/admin dicatat ke `audit_logs` dengan best-effort audit service.

## Daily Report Dan CSV

`GET /api/admin/reports/daily` menggabungkan:

- temperature/facility logs
- QC reports
- QC findings
- QC evidence
- approvals summary

CSV export memakai kolom production:

- Date
- Time
- Report Type
- Staff
- Room
- Device
- SKU/Barcode
- Product
- Temperature
- QC Status
- Approval Status
- Notes
- Photo URL

Export action dicatat sebagai `export_daily_report`.

## Evidence Preview

Backend menormalisasi URL evidence dengan prioritas:

1. `public_url`
2. `signed_url`
3. `photo_url`
4. signed URL dari `storage_path`
5. public URL fallback dari `storage_path`

Frontend admin memakai thumbnail dan modal preview. `storage_path` tidak dipakai sebagai preview utama.

## File Yang Diubah

- `backend/services/monitoring_service.py`
- `backend/services/inspection_service.py`
- `backend/services/qc_service.py`
- `backend/services/admin_service.py`
- `backend/api/admin_routes.py`
- `frontend/js/api.js`
- `frontend/js/admin_app.js`
- `tests/test_task3_*.py`

## QA Manual

1. Buka `/api/health/supabase`, pastikan `success=true` dan `connection=ok`.
2. Buka staff monitoring, submit suhu Kitchen/PPIC/Pack Kering/Ruang Kopi dengan foto.
3. Pastikan request tidak berisi `default-room-*`.
4. Buka admin monitoring report, pastikan row dan foto muncul.
5. Submit QC inspection dengan SKU manual dan foto.
6. Buka admin reports dan approval, pastikan pending muncul.
7. Approve satu QC report, reject satu QC report dengan comment.
8. Submit QC finding dengan foto.
9. Buka audit trail dan daily report untuk tanggal yang sama.
10. Export CSV dan pastikan kolom sesuai.

## Test

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q backend tests
```
