# QC Check Mobile UX Simplification

## Masalah UI Sebelumnya

Halaman staff QC Check sudah memakai data produk dari Admin Products, tetapi tampilan mobile masih terlalu padat:

- daftar SKU langsung tampil panjang saat halaman dibuka
- item produk terlalu besar
- user harus scroll banyak sebelum memilih stage dan submit
- input SKU manual terlalu dekat dengan daftar produk
- upload foto terlalu tinggi
- catatan opsional langsung memakan ruang
- bottom navigation berisiko menutup area bawah form

## Perubahan UX

Perubahan dilakukan hanya di frontend inspection:

- `frontend/staff/inspection.html`
- `frontend/js/inspection.js`
- `frontend/styles/qc.css`

Backend API, schema Supabase, dan admin report logic tidak diubah.

## Product Picker Ringkas

Saat halaman pertama dibuka, daftar SKU tidak langsung ditampilkan.

Staff melihat:

- search input
- teks bantuan `Ketik minimal 2 huruf untuk mencari produk.`

Hasil pencarian baru muncul setelah user mengetik minimal 2 karakter.

Hasil dibatasi maksimal 5 item supaya tidak memenuhi layar HP.

## Product Result Card

Result card dibuat compact:

- tinggi sekitar 64px
- SKU tebal
- nama produk maksimal 2 baris
- jarak antar item 8px
- tanpa shadow berat

Jika nama produk panjang, text dipotong dengan line clamp.

## Selected Product Preview

Setelah produk dipilih:

- daftar hasil disembunyikan
- muncul preview kecil:
  - Produk dipilih
  - SKU
  - nama produk
- tombol kecil `Ganti Produk`

## Batch Aktif

Batch aktif ditampilkan ringkas:

- batch code
- tahap terakhir
- status terakhir
- pilihan lanjut batch

Jika tidak ada batch aktif, tampil pesan:

`Belum ada batch aktif. Batch baru akan dibuat saat submit.`

## Stage Selection

Jenis pengecekan tetap dua pilihan:

- Cooking Check
- Final Check

Field yang tidak relevan disembunyikan:

- Cooking: suhu masak dan foto masakan/thermometer
- Final: foto barcode dan foto label cetak

## Upload Foto

Upload area diperkecil dan dibuat mobile-friendly:

- label jelas per foto
- tombol `Ambil Foto`
- setelah file dipilih tampil:
  - thumbnail kecil
  - nama file
  - tombol hapus foto

## Catatan Opsional

Catatan dibuat collapsible.

Default hanya menampilkan:

`+ Tambah catatan opsional`

Textarea baru muncul setelah diklik.

## Submit Dan Bottom Navigation

Halaman inspection mendapat padding bawah:

```css
.inspection-page {
  padding-bottom: 120px;
}
```

Submit button dibuat sticky di atas bottom navigation:

```css
.simple-submit {
  position: sticky;
  bottom: 94px;
}
```

Button disabled jika data wajib belum lengkap.

## Responsive QA

Target viewport:

- 320px
- 375px
- 390px
- 400px
- 430px

Kontrak yang dijaga:

- tidak ada product list panjang saat initial load
- search nyaman dipakai
- hasil produk maksimal 5 item
- stage Cooking/Final tetap mudah ditekan
- status PASS/HOLD/FAIL tetap rapi
- upload foto tidak terlalu tinggi
- notes tidak memakan ruang awal
- submit tidak tertutup bottom navigation

## Hasil Test

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q backend tests
```

Test frontend contract:

- `tests/test_inspection_mobile_ux.py`
