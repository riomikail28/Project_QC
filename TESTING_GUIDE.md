# Panduan Pengujian (Testing Guide) QC Central Kitchen

Dokumen ini menjelaskan strategi pengujian untuk QC Central Kitchen guna memastikan keandalan, stabilitas, dan keamanan sistem sebelum didistribusikan ke lingkungan produksi.

---

## 1. Unit Testing Backend (Pytest)

Aplikasi menggunakan `pytest` untuk menguji fungsionalitas backend Flask dan integrasinya dengan Supabase.

### Cara Menjalankan Tes:
Jalankan perintah berikut di terminal Anda:
```bash
pytest
```
Untuk menjalankan file pengujian spesifik secara terpisah:
```bash
python -m pytest tests/test_demo_accounts.py tests/test_admin_products.py
```

### Area yang Diuji:
*   **Autentikasi & Otorisasi:** Pengujian token JWT, pembatasan hak akses Admin/Staff, serta pengamanan ketat untuk akun demo admin.
*   **Monitoring Suhu Harian:** Validasi logika pencegahan duplikasi input suhu pada slot waktu yang sama, serta pengujian parameter `allow_duplicate` untuk fitur pengukuran ulang (recheck).
*   **Batch Produksi:** Verifikasi keunikan kode batch, pembuatan nomor sequence otomatis, dan perhitungan kedaluwarsa produk.
*   **Laporan QC:** Pengujian status kelulusan PASS/HOLD/FAIL, concurrency lock, dan penyimpanan referensi URL foto bukti.

---

## 2. Cakupan Uji Regresi Utama (Regression Tests)

Uji regresi berikut wajib dijalankan setiap kali ada perubahan kode guna mencegah bug baru pada workflow kritis:

### Hak Akses Pengguna (Role-based Security)
*   Akun Staff **harus ditolak** ketika mengakses API khusus Admin (misal: ekspor data, konfigurasi produk, CRUD ruangan).
*   Akun Admin **harus ditolak** jika mencoba menggunakan API khusus operasional dapur Staff yang memerlukan verifikasi unit kerja.
*   Endpoint yang terlindungi **wajib menolak** request yang tidak menyertakan token JWT valid.

### Alur Kerja Monitoring Harian
*   Pengecekan device harus membagi hari menjadi empat slot: `07:00`, `13:00`, `16:00`, dan `19:00`.
*   System harus mengizinkan staff mengisi slot waktu masa lalu atau saat ini yang terlewat (past/present slots).
*   System harus memblokir pengisian untuk slot waktu di masa depan (upcoming slots).
*   Validasi duplikasi harus menolak input berulang pada device-slot-tanggal yang sama, kecuali flag `allow_duplicate` aktif.

### Alur Kerja Pembuatan Batch
*   Format batch code wajib mengikuti pola `SKU-YYYYMMDD-00X` (misalnya: `SKU-20260712-001`).
*   Jika batch dengan sequence yang sama didaftarkan kembali, sistem harus menolak dan menyarankan sequence berikutnya secara dinamis.

### Pengambilan Foto Bukti (Hybrid Picker)
*   Ketika tombol kamera ditekan, pastikan browser mobile langsung membuka aplikasi kamera bawaan secara synchronous tanpa menampilkan pemilih file/galeri.
*   Ketika opsi galeri ditekan, browser harus membuka pemilih berkas untuk mengunggah foto yang sudah ada.
*   Proses kompresi gambar di sisi client wajib berjalan untuk mengecilkan resolusi berkas sebelum dikirim ke server.

### Tombol Pintas Speed Dial FAB
*   Tombol Speed Dial di pojok kanan bawah halaman staff harus menyembunyikan tautan ke halaman aktif saat ini.
*   Mengeklik opsi "QC Temuan" dari halaman **Monitoring** atau **QC Check** harus mengarahkan staff ke halaman dashboard utama dan otomatis membuka laci popup pengisian kendala dapur.

---

## 3. Checklist Uji Coba Manual (Manual QA Checklist)

Gunakan checklist ini sebelum melakukan presentasi demo atau rilis produksi.

### A. Pengujian Admin
- [ ] Login admin berhasil dan dialihkan ke Dashboard Admin.
- [ ] Diagram analitik dan statistik KPI termuat dengan benar.
- [ ] Riwayat audit trail mencatat aktivitas penambahan/perubahan terbaru.
- [ ] Menu Google Sheets Export berhasil melakukan test koneksi dan ekspor data ril berdasarkan filter tanggal.
- [ ] Akun demo admin (`demo_admin`) dibatasi hanya-baca (tindakan ubah/hapus memicu pesan error).

### B. Pengujian Staff (Tampilan HP)
- [ ] Login staff berhasil dan dialihkan ke Dashboard Staff.
- [ ] Halaman monitoring menampilkan slot harian dengan indikasi warna status yang tepat.
- [ ] Pengisian suhu slot berhasil disimpan dan memperbarui persentase progress monitoring di beranda.
- [ ] Pembuatan batch baru menghitung tanggal kedaluwarsa secara otomatis sesuai umur simpan SKU.
- [ ] Pengisian laporan QC check berhasil menyimpan status PASS/HOLD/FAIL.
- [ ] Pengambilan foto bukti via hybrid picker berfungsi dengan baik (Kamera vs Galeri).
- [ ] Menavigasi lewat tombol FAB menyembunyikan halaman aktif saat ini dengan benar.
- [ ] Mengklik "QC Temuan" dari menu FAB di halaman lain berhasil mengarahkan ke dashboard dan membuka drawer kendala.

### C. Pengujian PWA (Instalasi HP)
- [ ] Prompt "Add to Home Screen" muncul pada browser Chrome (Android) atau Safari (iOS).
- [ ] Aplikasi dapat dibuka dalam mode standalone (tanpa bilah alamat browser).
- [ ] Navigasi mobile bekerja lancar tanpa lag transisi.
- [ ] Asset statis (CSS/JS) tetap termuat secara offline berkat caching Service Worker.

---

## 4. Risiko Teknis & Mitigasi

*   **Kegagalan Webhook Google Sheets:** Jika Google Apps Script lambat atau mengalami masalah kuota harian, backend Flask tidak boleh menggagalkan proses penyimpanan transaksi utama di Supabase. Kegagalan webhook harus dicatat di log server sebagai peringatan non-blocking.
*   **Zona Waktu (Timezone Asia/Jakarta):** Seluruh perbandingan jam slot (07:00, 13:00, 16:00, 19:00) dan penentuan status keterlambatan input (late status) harus menggunakan zona waktu `Asia/Jakarta`, bukan zona waktu server lokal (UTC).
*   **Konflik Update QC Check (Concurrency Lock):** Jika dua staff QC mencoba menyunting laporan pemeriksaan yang sama secara bersamaan, sistem harus menampilkan peringatan penguncian transaksi agar data tidak saling menimpa.
