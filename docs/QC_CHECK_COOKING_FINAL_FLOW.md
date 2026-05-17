# QC Check Cooking Final Flow

## Alasan Flow Disederhanakan

Flow QC Check sebelumnya terlalu umum untuk kondisi lapangan karena menampilkan tahap seperti Receiving, Preparation, Packing, dan step AI yang belum menjadi proses nyata harian staff QC.

Flow aktual untuk demo dan controlled production launch adalah:

1. Cooking Check
2. Final Check

Receiving dan Packing tidak lagi ditampilkan pada QC Check utama.

## Konsep Data

Satu SKU dan satu batch dapat memiliki banyak row QC report.

Contoh:

- Produk: Chicken Katsu
- Batch: QC-20260517-001
- Report 1: Cooking Check oleh Staff A
- Report 2: Final Check oleh Staff B

Setiap submit membuat row baru di `qc_reports`. Report lama tidak ditimpa, sehingga admin dapat melihat timeline per batch.

## Cooking Check

Staff mengisi:

- SKU / barcode
- batch aktif atau batch baru
- suhu masak
- foto masakan / thermometer opsional
- status QC: PASS / HOLD / FAIL
- catatan opsional

Validasi:

- `temperature` wajib untuk `cooking_check`.
- `qc_status` wajib.
- `sku_code` atau `barcode` wajib.

## Final Check

Staff mengisi:

- SKU / barcode
- batch aktif atau batch baru
- foto barcode opsional
- foto label cetak opsional
- status QC: PASS / HOLD / FAIL
- catatan opsional

Validasi:

- `temperature` tidak wajib.
- `qc_status` wajib.
- minimal satu foto direkomendasikan, tapi tidak diwajibkan untuk fase ini.

## Staff Berbeda Bisa Melanjutkan Batch

Batch tidak dikunci ke satu staff.

Contoh:

- Staff A submit `cooking_check`.
- Staff B membuka SKU yang sama.
- Endpoint active batch menampilkan batch aktif.
- Staff B memilih batch tersebut dan submit `final_check`.

## Endpoint Yang Diubah

Staff:

- `GET /api/inspection/batches/active?sku=SKU_CODE`
- `POST /api/inspection/submit`

Admin:

- `GET /api/admin/reports/inspection?date=YYYY-MM-DD`

## Request Contract

`POST /api/inspection/submit` menerima `FormData`:

- `sku_code` atau `barcode`
- `batch_id` optional
- `batch_code` optional
- `qc_stage`: `cooking_check` atau `final_check`
- `qc_status`: `pass`, `hold`, `fail`
- `temperature`: wajib untuk `cooking_check`
- `notes` optional
- `cooking_photo` optional
- `barcode_photo` optional
- `label_photo` optional
- `photo` optional untuk backward compatibility

## Supabase Tables

Flow ini memakai:

- `production_batches`
- `qc_reports`
- `qc_evidence`
- `approvals`
- `audit_logs`

## Migration

Apply migration:

```sql
supabase/migrations/014_qc_check_cooking_final_flow.sql
```

Migration menambahkan kolom idempotent:

- `qc_reports.qc_stage`
- `qc_reports.label_photo_url`
- `qc_reports.label_storage_path`
- `qc_reports.cooking_photo_url`
- `qc_reports.cooking_storage_path`
- `qc_reports.barcode_storage_path`

Juga menambahkan index batch/stage untuk timeline report.

## Admin Timeline

Admin report inspection mengirim:

- `batch_code`
- `product_name`
- `qc_stage`
- `staff_name`
- `temperature`
- `status`
- `approval_status`
- `photo_url`
- `cooking_photo_url`
- `barcode_photo_url`
- `label_photo_url`
- `notes`
- `created_at`

Frontend admin mengelompokkan report berdasarkan batch dan menampilkan:

- Cooking Check selesai / belum dilakukan
- Final Check selesai / belum dilakukan
- status dan evidence per stage

## Batch Status

Setelah submit:

- hanya Cooking Check selesai: `production_batches.status = in_progress`
- Cooking Check dan Final Check PASS: `status = completed`, `final_qc_status = pass`
- ada HOLD: `status = on_hold`, `final_qc_status = hold`
- ada FAIL: `status = failed`, `final_qc_status = fail`

Jika schema production memiliki enum yang lebih ketat, update batch status dilewati secara best-effort dan detail stage tetap aman di `qc_reports`.

## Hasil Test

Test utama:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q backend tests
```

Covered:

- submit Cooking Check sukses
- Cooking Check tanpa suhu gagal 400 jelas
- Final Check tanpa suhu sukses
- Final Check dengan foto barcode dan label sukses
- staff berbeda bisa melanjutkan batch yang sama
- setiap submit membuat row baru di `qc_reports`
- approval pending dibuat per submit
- audit `submit_inspection` tercatat
- admin report menampilkan `cooking_check` dan `final_check`
- active batch endpoint mengembalikan batch berdasarkan SKU
- empty SKU gagal validasi
- frontend QC Check tidak menampilkan Receiving/Packing/Preparation
