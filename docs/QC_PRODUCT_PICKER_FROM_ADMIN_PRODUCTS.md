# QC Product Picker From Admin Products

## Source Of Truth

Staff QC Check sekarang memakai tabel `products` sebagai source of truth untuk daftar SKU.

Produk yang dikelola dari Admin Panel menu Products / SKU Produk akan muncul di halaman staff `inspection.html` selama `is_active = true`.

Kolom utama:

- `id`
- `product_code`
- `product_name`
- `ph_min`
- `ph_max`
- `brix_min`
- `brix_max`
- `tds_min`
- `tds_max`
- `is_active`

## Staff Flow

Flow QC Check:

1. Pilih Produk / SKU dari searchable picker.
2. Sistem menampilkan produk terpilih.
3. Sistem mencari batch aktif dengan `GET /api/inspection/batches/active?sku=PRODUCT_CODE`.
4. Staff memilih lanjut batch aktif atau membuat batch baru saat submit.
5. Staff memilih `Cooking Check` atau `Final Check`.
6. Staff upload evidence sesuai stage.
7. Submit QC Check.

## Manual SKU Fallback

Manual input bukan mode utama.

Tombol `Input SKU manual` dipakai hanya jika produk belum terdaftar di Admin Products.

Saat manual:

- `product_id` kosong.
- `sku_code` memakai input staff.
- `product_name` disimpan sebagai `Manual SKU` atau value frontend.

## Endpoint

### Product Picker

`GET /api/inspection/products`

Response:

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "product_code": "SKU-CHKN-001",
      "product_name": "Finish Goods - Chilled/Frozen Teriyaki chicken 90gr - AK",
      "is_active": true
    }
  ],
  "message": "OK"
}
```

Rules:

- Query table `products`.
- Filter `is_active = true`.
- Order by `product_code` ascending.
- Jika kosong, return empty array.
- Tidak memakai dummy catalog.

### Active Batch

`GET /api/inspection/batches/active?sku=SKU-CHKN-001`

Dipanggil setelah staff memilih produk.

### Submit QC

Jika produk dipilih:

- `product_id`
- `product_name`
- `sku_code = product_code`
- `barcode = product_code`
- `batch_id` jika lanjut batch aktif
- `qc_stage`
- `qc_status`
- `temperature` untuk Cooking Check
- evidence fields

Backend memvalidasi `product_id` ke tabel `products` dan memakai `product_code/product_name` dari database, bukan mempercayai penuh payload frontend.

## Admin Product CRUD

Admin tambah/edit produk akan langsung mempengaruhi picker staff.

Produk nonaktif (`is_active=false`) tidak tampil di staff QC Check, tetapi report lama tetap aman karena `qc_reports` menyimpan snapshot `product_name`, `barcode`, dan `product_id`.

## Admin Report

Admin inspection report menampilkan:

- SKU / product_code
- product_name
- batch_code
- qc_stage
- staff
- status
- evidence photo

## Hasil Test

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q backend tests
```

Covered:

- `/api/inspection/products` membaca dari `products`.
- Produk inactive tidak muncul.
- Submit QC dengan `product_id` sukses dan memakai data DB.
- Submit QC manual SKU sukses.
- Submit tanpa produk/manual SKU gagal 400 jelas.
- Produk baru dari admin muncul di picker.
- Admin report menampilkan SKU dan nama produk.
