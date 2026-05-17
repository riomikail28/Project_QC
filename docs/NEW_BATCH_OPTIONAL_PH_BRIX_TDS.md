# New Batch Optional pH Brix TDS

## Scope

`new_batch.html` sekarang mendukung parameter kualitas opsional:

- pH
- Brix
- TDS

Ketiganya tidak wajib. Batch tetap bisa dibuat walaupun semua nilai kosong.

## Flow Create Batch

1. Staff memilih produk dari Admin Products.
2. Staff mengisi batch code atau membiarkannya kosong.
3. Jika batch code kosong, backend generate otomatis: `QC-YYYYMMDD-HHMMSS`.
4. Staff memilih production date.
5. Staff opsional mengisi pH, Brix, dan TDS.
6. Staff klik `START INSPECTION`.
7. Backend membuat row `production_batches`.
8. Staff diarahkan ke `inspection.html` untuk lanjut Cooking Check / Final Check.

## Hubungan Dengan Admin Products

Standar parameter diambil dari tabel `products`:

- `ph_min` / `ph_max`
- `brix_min` / `brix_max`
- `tds_min` / `tds_max`

Jika standar tersedia, frontend menampilkan helper:

- `pH standard: 4.5 - 7`
- `Brix standard: 11 - 14 %`
- `TDS standard: 100 - 150`

Jika standar kosong, helper tidak ditampilkan.

## Status Parameter

Backend menyimpan status:

- `pass`: nilai ada dan berada dalam range standar.
- `warning`: nilai ada dan di luar range standar.
- `not_checked`: nilai kosong.

Nilai di luar standar tidak memblokir batch creation. Admin dapat melihat warning di report.

## Migration

Apply migration:

```sql
supabase/migrations/015_optional_batch_ph_brix_tds.sql
```

Kolom yang ditambahkan:

- `ph_value`
- `brix_value`
- `tds_value`
- `ph_status`
- `brix_status`
- `tds_status`
- `parameter_notes`
- `parameter_checked_by`
- `parameter_checked_at`

Migration idempotent dan tidak merusak data lama.

## Admin Report

`GET /api/admin/reports/batches` mengembalikan:

- Batch Code
- Product
- pH
- pH Status
- Brix
- Brix Status
- TDS
- TDS Status
- Parameter Notes
- Checked By
- Checked At

Jika nilai kosong, status dikembalikan sebagai `not_checked` dan value tetap `null`, bukan `0`.

## Audit Trail

Saat batch dibuat:

- audit action `create_batch`

Jika ada salah satu parameter:

- audit action `batch_parameter_check`

Metadata audit berisi:

- `product_id`
- `batch_code`
- `ph_value`
- `ph_status`
- `brix_value`
- `brix_status`
- `tds_value`
- `tds_status`

## Test

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q backend tests
```

Covered:

- create batch tanpa pH/Brix/TDS sukses
- create batch dengan pH sukses
- create batch dengan Brix sukses
- create batch dengan TDS sukses
- pH/Brix/TDS in range = `pass`
- pH/Brix/TDS out of range = `warning`
- admin report menampilkan pH/Brix/TDS
- empty values tampil `not_checked`, bukan `0`
