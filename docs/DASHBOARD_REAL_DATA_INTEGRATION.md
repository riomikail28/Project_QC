# Dashboard Real Data Integration

## Endpoint Dibuat

Semua endpoint membutuhkan auth token dan mengembalikan envelope konsisten:

```json
{
  "success": true,
  "data": {},
  "message": "OK"
}
```

- `GET /api/dashboard/summary`
- `GET /api/dashboard/production-trend`
- `GET /api/dashboard/qc-status`
- `GET /api/dashboard/realtime-monitoring`
- `GET /api/dashboard/alerts`
- `GET /api/dashboard/today-summary`

## Tabel Supabase

- `production_batches`: total batch hari ini dan produksi 7 hari.
- `qc_reports`: QC success rate, status QC, pending approval fallback, photo evidence.
- `temperature_logs`: log suhu real, freezer average, abnormal alert fallback.
- `facility_logs`: fallback log suhu real yang dipakai form monitoring saat ini.
- `facility_alerts`: alert abnormal/open jika tersedia.
- `barcode_labels`: jumlah label barcode hari ini.
- `staff_activity`: aktivitas staff hari ini.
- `approvals`: pending approval jika tabel tersedia.
- `storage qc-evidence`: dipakai melalui URL evidence di `qc_reports`.

## Query Data Real

- Total batch hari ini: `production_batches.production_date = today`, fallback `created_at` hari ini.
- Total alert: `facility_alerts.status = open`, fallback abnormal temperature logs.
- QC success rate: `qc_reports.status = pass / total qc_reports`.
- Pending approval: `approvals.status = pending`, fallback `qc_reports.approval_status = pending`.
- Average freezer temperature: latest `temperature_logs`/`facility_logs` dengan device type freezer.
- Produksi 7 hari: agregasi `production_batches` dalam 7 hari terakhir.
- Status QC: hitung `pass`, `warning`, `fail`, `pending` dari `qc_reports`.
- Realtime monitoring: latest log per `device_id`, `room_id`, atau zone.
- Abnormal alert feed: `facility_alerts` open, fallback abnormal temperature logs.
- Today QC Summary: QC submitted, photo evidence, temperature logs, barcode labels, staff activity hari ini.

## Empty State

Database kosong tidak menghasilkan angka palsu. Frontend menampilkan:

`No data available yet`

Nilai yang belum ada ditampilkan sebagai `--` atau `0` sesuai konteks, tanpa hardcoded dummy seperti `18`, `98%`, `4`, atau `-18.4`.

## File Diubah

- `backend/api/dashboard_routes.py`
- `backend/services/dashboard_service.py`
- `backend/__init__.py`
- `frontend/js/dashboard.js`
- `frontend/staff/dashboard.html`
- `frontend/styles/dashboard.css`
- `supabase/migrations/004_dashboard_real_data.sql`
- `tests/test_dashboard_real_data.py`
- `tests/conftest.py`

## Migration

Migration baru:

`supabase/migrations/004_dashboard_real_data.sql`

Berisi index untuk:

- `created_at`
- `status`
- `staff_id`
- `batch_id`
- `device_id`
- `production_date`
- `recorded_at`

Index dibuat aman dengan conditional block untuk tabel/kolom opsional.

## Cara Test

1. Login sebagai staff.
2. Buat batch baru.
3. Submit QC report atau evidence.
4. Input suhu monitoring.
5. Buka `dashboard.html`.
6. Pastikan metrik, chart, monitoring, alert, dan summary berubah sesuai data Supabase.

Automated test:

```bash
py -m pytest tests\test_dashboard_real_data.py tests\test_api.py tests\test_dashboard.py
```

Hasil terakhir: 12 passed.

## QA

- Database kosong: dashboard menampilkan empty state, tidak dummy.
- API error: dashboard menampilkan error state.
- Auto refresh: aktif setiap 30 detik.
- Mobile 390px: card dan chart memakai layout responsive.
- Desktop 1440px: grid dashboard tetap stabil.

