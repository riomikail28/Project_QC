# Photo Upload Fix Report

Tanggal: 2026-05-15

## Ringkasan Penyebab

- Beberapa flow frontend melakukan upload foto ke `/api/storage/upload` lebih dulu, lalu menyimpan record database lewat request JSON terpisah. Ini membuat file dan database bisa tidak sinkron.
- Backend storage helper hanya mengembalikan `photo_url`, belum mengembalikan `storage_path`, sehingga rollback dan audit path file tidak mungkin dilakukan.
- Endpoint storage memakai middleware auth yang tidak ada (`backend.api.auth_middleware`), sehingga route upload standalone bisa gagal saat app start.
- Flow monitoring memakai `data.get("photo_url")` pada dataclass request, berisiko gagal saat multipart/JSON diproses.
- `backend/services/ccp_service.py` berisi potongan teks yang membuat struktur service tidak bersih dan rawan syntax/runtime error.
- `.env.example` masih memakai `MAX_UPLOAD_BYTES=5242880`, tidak sesuai target 10MB.

## File yang Diubah

- `.env.example`
- `backend/database/supabase_client.py`
- `backend/services/storage_service.py`
- `backend/services/qc_service.py`
- `backend/services/ccp_service.py`
- `backend/services/batch_service.py`
- `backend/api/storage_routes.py`
- `backend/api/temperature_routes.py`
- `backend/api/ccp_routes.py`
- `backend/api/qc_routes.py`
- `backend/api/batch_routes.py`
- `backend/__init__.py`
- `frontend/js/api.js`
- `frontend/js/monitoring.js`
- `frontend/js/ccp.js`
- `frontend/js/inspection.js`
- `frontend/staff/monitoring.html`
- `frontend/staff/ccp_stage.html`
- `frontend/staff/dashboard.html`
- `frontend/staff/inspection.html`
- `supabase/migrations/005_photo_storage_paths.sql`

## Endpoint yang Diperbaiki

- `POST /api/storage/upload`
- `POST /api/upload`
- `POST /api/qc/upload`
- `POST /api/evidence`
- `POST /api/monitoring/log`
- `POST /api/ccp/submit-stage`
- `POST /api/qc/findings`
- `POST /api/batch/create`

## Storage Config

- Bucket dipaksa konsisten ke `qc-evidence`.
- Migration `005_photo_storage_paths.sql` memastikan bucket `qc-evidence` tersedia dan public URL dapat dipakai admin/staff.
- `.env.example` disamakan dengan batas upload 10MB.

## Storage Path

Format path sekarang:

```text
qc-evidence/{staff_id}/{YYYY-MM-DD}/{staff_id}_{YYYYMMDD_HHMMSS}_{uuid}.{ext}
```

Contoh:

```text
qc-evidence/17/2026-05-15/17_20260515_153000_9f7c2d4e....jpg
```

## Validasi Upload

Frontend dan backend sekarang sama-sama membatasi:

- Maksimal 10MB per foto.
- Format: `image/jpeg`, `image/png`, `image/webp`.
- Form upload memakai `FormData` dan `formData.append("photo", file)`.
- Invalid file menampilkan pesan `Upload gagal`.

## Rollback

- Jika upload storage berhasil tetapi insert database gagal, backend menghapus file dari Supabase Storage.
- Jika storage gagal, database tidak disimpan.
- Response upload standalone tetap mempertahankan `url`, dengan tambahan `storage_path` dan `bucket`.

## Multiple Photo

- Monitoring suhu, CCP stage, dan QC temuan mendukung beberapa file dengan field multipart yang sama: `photo`.
- Backend membaca `request.files.getlist("photo")`.
- URL dan storage path multiple disimpan sebagai string dipisah `;`, sesuai pola existing `photo_url`.

## Hasil Test

- `py -m compileall backend`: lulus.
- `py -m pytest tests/test_monitoring.py tests/test_api.py`: 11 passed.
- `py -m pytest`: 34 passed, 1 failed.

Kegagalan full suite:

- `tests/test_dashboard_real_data.py::test_dashboard_summary_uses_real_tables`
- Penyebab: test fixture memakai data tanggal `2026-05-14`, sementara tanggal environment saat audit adalah `2026-05-15`; service dashboard menghitung data "hari ini".

## QA Matrix

Dicek secara kode untuk:

- 1 foto: supported.
- 2 foto: supported via `request.files.getlist("photo")`.
- 5 foto: supported via multipart repeated `photo`.
- 10 foto: supported via multipart repeated `photo`.
- JPG: allowed.
- PNG: allowed.
- WEBP: allowed.
- PDF/TXT/ZIP: rejected with `Upload gagal`.
- Refresh halaman: foto yang sudah submit tersimpan sebagai URL DB dan storage path; preview lokal sebelum submit tetap bersifat sementara.
- Offline/database kosong: production/Vercel tidak membuat record palsu; local dev fallback tetap menyimpan ke `/uploads/qc_photos`.

## Target Status

- Foto tersimpan di Supabase Storage: fixed.
- URL tersimpan di database: fixed.
- Storage path tersimpan di database: fixed melalui migration baru.
- Preview tampil: fixed untuk monitoring, CCP, inspection quick input, dan QC temuan.
- Multiple upload berjalan: fixed.
- File orphan dikurangi dengan rollback saat DB save gagal.
- Staff dan admin dapat membuka evidence melalui URL yang tersimpan.
