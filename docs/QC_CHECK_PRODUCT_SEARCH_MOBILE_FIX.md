# QC Check Product Search Mobile Fix

## Scope

Perubahan hanya pada frontend QC Check:

- `frontend/staff/inspection.html`
- `frontend/js/inspection.js`
- `frontend/styles/qc.css`
- `tests/test_inspection_mobile_ux.py`

Backend API, schema Supabase, dan admin report logic tidak diubah.

## Product / SKU Source

Produk dan SKU berasal dari Admin Products melalui:

`GET /api/inspection/products`

Data yang dipakai adalah tabel `products`. Picker tidak memakai dummy data.

## Search Flow

User bisa mengetik cepat di field `Pilih Produk / SKU` dengan placeholder `Cari SKU atau nama produk`.

Search result baru muncul setelah input minimal 2 huruf. Filter dilakukan di frontend terhadap:

- `product_code`
- `product_name`
- `barcode` jika tersedia

Hasil pencarian dibatasi maksimal 5 item supaya tidak memenuhi layar mobile.

Helper text `Ketik minimal 2 huruf untuk mencari produk.` hanya tersedia satu kali di markup dan tidak dirender ulang sebagai elemen kedua.

## Manual SKU Fallback

Manual SKU bukan mode utama.

Tombol `Input SKU manual` muncul saat produk tidak ditemukan. Jika dipakai:

- `product_id` kosong
- `sku_code` berasal dari input manual
- `product_name` dikirim sebagai `Manual SKU`

Jika user belum memilih produk dan input manual kosong, submit gagal dengan pesan `Pilih produk terlebih dahulu.`

## Progressive Form

QC Check dibuat bertahap agar halaman tidak memanjang sejak awal:

1. Pilih Produk / SKU
2. Batch
3. Jenis Pengecekan
4. Field sesuai jenis pengecekan
5. Status QC
6. Catatan opsional
7. Simpan QC

Jenis pengecekan baru tampil setelah produk dipilih atau manual SKU fallback diisi.

## Stage-Specific Fields

`Cek Masakan` hanya menampilkan:

- Suhu Masak
- Foto Masakan / Termometer
- Status QC
- Catatan opsional
- Simpan QC

`Cek Label Akhir` hanya menampilkan:

- Foto Barcode
- Foto Label Cetak
- Status QC
- Catatan opsional
- Simpan QC

## Responsive QA

Kontrak mobile yang dijaga:

- Tidak ada horizontal scroll pada 320px, 375px, 390px, 400px, dan 430px.
- Search result dibatasi maksimal 5 item.
- Helper text tidak dobel.
- Upload card compact dengan thumbnail, nama file, dan tombol hapus.
- Catatan default collapsed lewat `+ Tambah Catatan`.
- Halaman memakai `padding-bottom: 120px` agar bottom nav tidak menutupi form.

## Verification

Command yang dijalankan:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q backend tests
```

Frontend contract test terkait:

- `tests/test_inspection_mobile_ux.py`
