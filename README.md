# QC Enterprise - Quality Control & Traceability System for Central Kitchen

Sistem digital untuk monitoring suhu, QC inspection, batch traceability, approval, audit trail, dan pembelajaran HACCP berbasis web.

Demo link: https://project-qc-mu.vercel.app/

## Demo Account

Admin:

```text
demo.admin@qcenterprise.id
demo123456
```

Staff:

```text
demo.staff@qcenterprise.id
demo123456
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

Jangan commit file `.env`, service role key, refresh token, atau credential production.

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
