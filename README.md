# QC Enterprise - Quality Control & Traceability System for Central Kitchen

Sistem digital untuk monitoring suhu, QC inspection, batch traceability, approval, audit trail, dan pembelajaran HACCP berbasis web.

Demo link: https://project-qc-mu.vercel.app/
Rio
123456

## Demo Account

Admin:

```text
demo.admin@qcenterprise.id
demoadmin123
```

Staff:

```text
demo.staff@qcenterprise.id
demostaff123
```

> Catatan: akun demo dibuat melalui seed database `supabase/seed/001_demo_seed.sql`. Jangan menyimpan Supabase service role key atau secret lain di repository.

## Key Features

- Admin enterprise dashboard
- Staff mobile-first QC workflow
- Temperature monitoring schedule
- Batch production
- QC inspection
- PASS/HOLD/FAIL decision
- Photo evidence upload
- Traceability
- Alerts
- Reports
- Audit trail
- ITDV Learning Center
- HACCP competency modules
- Module mini quiz
- Certificate completion
- Career recommendation

## Tech Stack

- HTML
- CSS
- JavaScript
- Python Flask
- Supabase PostgreSQL
- Vercel
- Pytest

## Screenshots

Tambahkan screenshot pada section berikut saat materi demo final sudah siap:

- Admin Dashboard
- Staff Mobile Dashboard
- QC Check
- Monitoring Schedule
- Learning Center

## Problem Statement

QC central kitchen masih banyak dilakukan manual sehingga rawan human error, keterlambatan monitoring suhu, dan sulit traceability.

## Solution

QC Enterprise membantu digitalisasi monitoring, inspeksi, traceability, dan pelatihan QC. Admin mendapatkan dashboard enterprise untuk memantau batch, alert suhu, approval, dan laporan. Staff mendapatkan workflow mobile-first untuk monitoring suhu, QC check, upload evidence, dan keputusan PASS/HOLD/FAIL di lapangan.

## Target Users

- Central kitchen
- Catering
- Bakery
- Frozen food
- Cloud kitchen
- UMKM makanan
- SMK Tata Boga
- Mahasiswa Teknologi Pangan

## Installation

1. Clone repository.

```bash
git clone <repository-url>
cd Project_QC
```

2. Buat virtual environment dan install dependency.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. Copy environment template.

```bash
copy .env.example .env
```

4. Isi konfigurasi Supabase dan JWT di `.env`.

5. Jalankan aplikasi lokal.

```bash
python api/app.py
```

6. Buka aplikasi:

```text
http://localhost:5000/staff/login.html
http://localhost:5000/admin/admin_panel.html
http://localhost:5000/learning/
```

## Environment Variables

Gunakan `.env.example` sebagai template. Variable utama:

- `JWT_SECRET_KEY`
- `JWT_ISSUER`
- `CORS_ORIGINS`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `MAX_UPLOAD_BYTES`
- `GOOGLE_APPS_SCRIPT_WEBHOOK_URL` optional, untuk export monitoring suhu dan QC inspection ke Google Sheets melalui Google Apps Script Web App. Biarkan kosong jika tidak digunakan.

Jangan commit file `.env`, service role key, refresh token, atau credential production.

## Optional Google Sheets Export

Backend dapat mengirim data monitoring suhu dan QC inspection ke Google Apps Script Web App setelah submit utama berhasil. Integrasi ini opsional: jika `GOOGLE_APPS_SCRIPT_WEBHOOK_URL` kosong, aplikasi tetap berjalan normal.

Cara setup:

1. Buat Google Sheet baru untuk menerima laporan.
2. Buka `Extensions > Apps Script`.
3. Buat script Web App dengan fungsi `doPost(e)` yang membaca `JSON.parse(e.postData.contents)`, lalu append data ke sheet sesuai `type` (`monitoring_log`, `qc_report`, atau `qc_finding`).
4. Deploy melalui `Deploy > New deployment > Web app`.
5. Set akses sesuai kebutuhan, misalnya `Anyone with the link` untuk webhook sederhana.
6. Copy URL Web App dan isi env:

```env
GOOGLE_APPS_SCRIPT_WEBHOOK_URL=https://script.google.com/macros/s/your-deployment-id/exec
```

Payload monitoring berisi `date`, `slot_time`, `room`, `device`, `temperature`, `status`, `staff_name`, `submitted_at`, `notes`, `source_type`, dan `source_id`. Payload QC berisi `timestamp`, `date`, `product_name`, `batch_code`, `batch_sequence`, `cook_name`, `quantity`, `inspection_type`, `temperature`, `ph`, `brix`, `tds`, `status`, `staff_name`, `photo_url`, `notes`, `inspection_round`, `is_recheck`, `source_type`, dan `source_id`. Payload QC Temuan berisi `timestamp`, `type`, `staff_name`, `finding_description`, `photo_url`, `status`, `source_type`, dan `source_id`.

Admin dapat mengirim ulang data lama dari menu `Google Sheets`:

- `Export All Monitoring` mengirim ulang data `facility_logs` / `temperature_logs`.
- `Export All QC Reports` mengirim ulang data `qc_reports` / `qc_findings`.
- `Export by Date Range` menggunakan filter `Start Date` dan `End Date`.

Untuk Apps Script, gunakan header tab `QC Reports` berikut agar data QC final lengkap:

`Timestamp`, `Type`, `Date`, `Product`, `Batch Code`, `Batch Sequence`, `Cook`, `Qty`, `Inspection Type`, `Temperature`, `pH`, `Brix`, `TDS`, `Status`, `Staff`, `Photo URL`, `Notes`, `Inspection Round`, `Re-check`, `Source Type`, `Source ID`.

Tambahkan juga tab `QC Temuan` untuk laporan temuan lapangan dengan header:

`Timestamp`, `Type`, `Staff`, `Temuan`, `Foto URL`, `Status`, `Source Type`, `Source ID`.

Mapping row untuk `qc_finding`:

`new Date()`, `type`, `data.staff_name`, `data.finding_description || data.finding || data.temuan || data.notes || data.message`, `data.photo_url || data.evidence_url`, `data.status || "OPEN"`, `data.source_type`, `data.source_id`.

Jika Google Apps Script gagal atau timeout, backend hanya mencatat warning dan tetap mengembalikan sukses untuk submit utama.

Troubleshooting jika data tidak masuk Google Sheet:

1. Pastikan `GOOGLE_APPS_SCRIPT_WEBHOOK_URL` sudah dipasang di environment Vercel/hosting, bukan hanya di `.env` lokal.
2. Redeploy aplikasi setelah environment variable ditambahkan atau diubah.
3. Di Apps Script, deploy sebagai `Web app`.
4. Set `Execute as` ke `Me`.
5. Set `Who has access` ke `Anyone` agar webhook backend bisa mengirim request.
6. Cek `Executions` log di Apps Script untuk melihat error parsing payload atau permission.
7. Dari Admin Dashboard, buka menu `Google Sheets`, lalu gunakan tombol `Test Export` untuk melihat status, response error, dan waktu export terakhir.

## Install PWA

QC Enterprise dapat dipasang sebagai PWA dari browser modern.

1. Buka aplikasi di browser, misalnya `/staff/login.html`.
2. Login atau biarkan halaman login terbuka.
3. Di Chrome/Edge desktop, klik ikon install di address bar atau menu `Install app`.
4. Di Android Chrome, buka menu browser lalu pilih `Add to Home screen` atau `Install app`.
5. Setelah terpasang, aplikasi akan terbuka dalam mode standalone dengan tampilan portrait.

## Demo Data

Seed demo tersedia di:

```text
supabase/seed/001_demo_seed.sql
```

Seed tersebut menambahkan:

- akun demo admin dan staff
- produk demo
- batch demo
- monitoring suhu normal dan alert
- QC PASS/HOLD/FAIL
- barcode traceability
- progress awal ITDV Learning

Jalankan seed melalui Supabase SQL editor atau pipeline migration internal setelah schema utama selesai diterapkan.

## Testing

Jalankan seluruh test:

```bash
pytest
```

Jika `pytest` tidak tersedia di PATH Windows:

```bash
.venv\Scripts\python.exe -m pytest
```

Syntax check JavaScript frontend:

```powershell
Get-ChildItem frontend -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
```

## Roadmap

- IoT temperature integration
- WhatsApp notification
- AI anomaly detection
- Export PDF report
- Multi-tenant SaaS

## License / Author

Author: Rio Mikail

Project portfolio: QC Enterprise - Central Kitchen Quality Control System
