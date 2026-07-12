# Arsitektur Proyek QC Central Kitchen

## 1. Gambaran Umum

QC Central Kitchen adalah sistem Quality Control berbasis web yang dirancang khusus untuk memenuhi kebutuhan dapur pusat (Central Kitchen). Aplikasi ini membantu pencatatan suhu area/alat secara terstruktur, pelacakan mutu batch produksi, pemeriksaan QC, pembuatan laporan temuan, audit trail aktivitas pengguna, serta ekspor data ke spreadsheet eksternal lewat Google Sheets.

Arsitektur aplikasi dirancang untuk memisahkan antarmuka pengguna (user interface), pemrosesan logika backend, penyimpanan database, dan integrasi pelaporan eksternal. Struktur ini mempermudah pemeliharaan operasional dapur, penyusunan dokumentasi akademis, peninjauan portofolio, serta pengembangan otomatisasi berbasis AI di masa mendatang.

---

## 2. Arsitektur Sistem

QC Central Kitchen menggunakan arsitektur aplikasi web modern yang terdiri dari komponen-komponen berikut:

*   **Frontend:** Dibangun menggunakan HTML5, CSS3, dan JavaScript murni (Vanilla JS) agar ringan dan responsif.
*   **Backend:** Menggunakan Python Flask yang andal untuk menangani routing API, bisnis logika, validasi data, dan manajemen hak akses (role-based access).
*   **Database:** Supabase PostgreSQL sebagai database relational utama untuk menyimpan data operasional seperti data pengguna, data suhu, batch produksi, laporan QC, temuan kendala, dan log audit.
*   **Deployment:** Vercel digunakan untuk mendistribusikan aplikasi secara cepat dan andal.
*   **Integrasi Eksternal:** Google Apps Script yang berperan sebagai jembatan webhook untuk mengekspor data operasional sistem ke Google Sheets.
*   **Dukungan PWA (Progressive Web App):** Dilengkapi dengan service worker khusus bermetode *Network-First* agar aplikasi dapat diinstal di HP staff dan tetap handal diakses di dalam area dapur yang minim sinyal.

---

## 3. Pembagian Peran Pengguna (Role)

### Admin
Admin berfokus pada pengawasan operasional dapur secara menyeluruh, analisis performa, dan pengelolaan konfigurasi sistem.
Akses utama Admin mencakup:
*   Dashboard pemantauan analitik (grafik kelulusan QC & suhu).
*   Peninjauan laporan dan detail log.
*   Pemeriksaan riwayat aktivitas sistem (audit trail).
*   Pengelolaan hak akses staff, daftar produk (SKU), dan ruangan dapur.
*   Pemicu sinkronisasi data ekspor ke Google Sheets.

### Staff
Staff berfokus pada pengisian data harian secara langsung di lapangan menggunakan HP/tablet.
Akses utama Staff mencakup:
*   Dashboard operasional staff.
*   Modul pengisian suhu ruangan/alat berdasarkan slot waktu harian.
*   Modul pembuatan batch masakan baru (automatic expiry calculation berdasarkan umur simpan SKU).
*   Modul pengisian checklist QC produk (PASS/HOLD/FAIL).
*   Modul pengisian temuan/deviasi di dapur beserta foto bukti (evidence).

---

## 4. Alur Kerja Utama (Core Workflow)

1.  Pengguna melakukan login menggunakan kredensial akun yang terdaftar.
2.  Sistem memverifikasi kredensial di backend, membaca hak aksesnya, dan mengarahkan ke dashboard yang sesuai (Admin atau Staff).
3.  Staff mengisi monitoring suhu ruangan dapur berdasarkan empat slot waktu harian yang fleksibel (07:00, 13:00, 16:00, 19:00). Staff dapat memilih slot waktu mana pun yang belum diisi untuk melengkapi data pemantauan harian.
4.  Staff dapur mencatat setiap aktivitas memasak produk sebagai batch produksi baru. Sistem otomatis membuatkan kode batch unik berdasarkan tanggal produksi dan urutan sequence produk.
5.  Staff QC mengecek batch produksi yang siap kirim, mengisi checklist parameter kualitas, mengambil foto bukti, menetapkan keputusan PASS/HOLD/FAIL, lalu menyimpan laporan QC.
6.  Setiap data yang masuk ke database akan tercatat di audit trail secara otomatis untuk menjamin integritas data dapur.

---

## 5. Arsitektur Pemilihan Foto (Hybrid Photo Picker)

Untuk memfasilitasi kebutuhan staff di lapangan, sistem dilengkapi modul picker foto hibrida di sisi client:
*   Popup menu bawah (bottom sheet) memberikan pilihan kepada pengguna untuk memotret langsung (**Kamera**) atau memilih gambar yang sudah ada (**Galeri / Upload**).
*   **Masalah Mobile Browser:** Browser bawaan mobile (seperti Chrome di Android atau Safari di iOS) seringkali menonaktifkan fitur kamera langsung apabila input file memiliki atribut `multiple` aktif.
*   **Solusi Teknis:** Modul JavaScript [ui-mobile.js](file:///c:/Users/rio/.gemini/antigravity/scratch/Project_QC/frontend/js/ui-mobile.js) mendeteksi pilihan pengguna secara real-time. Jika pengguna memilih **Kamera**, sistem akan menghapus atribut `multiple` dan menyetel `.multiple = false` pada element DOM secara synchronous, lalu menambahkan atribut `capture="environment"` sebelum memicu event `.click()`. Jika memilih **Galeri**, sistem mengembalikan parameter `multiple` sehingga pengguna dapat memilih banyak berkas dari galeri penyimpanan HP mereka.
*   **Kompresi Sisi Client:** Semua foto yang dipilih akan dikompresi ukurannya di browser staff sebelum dikirim ke server. Ini mempercepat proses penyimpanan data evidence di database meskipun koneksi internet dapur lambat.

---

## 6. Penanganan Duplikasi Suhu (Recheck & Duplication)

Untuk mengamankan validitas log pemantauan harian:
*   Sistem melarang pengisian ganda (duplicate) pada slot waktu yang sama untuk device yang sama pada hari tersebut, guna mencegah ketidaksengajaan klik ganda oleh staff.
*   Namun, jika terjadi penyimpangan suhu (suhu kritis) dan staff melakukan tindakan perbaikan, staff diperbolehkan mengirimkan data baru (recheck) pada slot tersebut.
*   Backend service [monitoring_schedule_service.py](file:///c:/Users/rio/.gemini/antigravity/scratch/Project_QC/backend/services/monitoring_schedule_service.py) memvalidasi status kelulusan. Apabila parameter `allow_duplicate` diset ke `True` oleh client, backend mengizinkan penulisan log suhu baru dan menyimpannya sebagai catatan audit recheck historis tanpa menimpa data sebelumnya.

---

## 7. Desain Navigasi Cepat (Speed Dial FAB & Redirect)

Tombol melayang Speed Dial FAB (Floating Action Button) mempermudah akses silang antarmodul di layar HP staff:
*   **Opsi Kontekstual Dinamis:** Komponen [quick-actions.js](file:///c:/Users/rio/.gemini/antigravity/scratch/Project_QC/frontend/js/quick-actions.js) mendeteksi lokasi halaman saat ini dan menyembunyikan tombol navigasi yang merujuk ke halaman tersebut untuk menghindari kebingungan.
*   **Navigasi Lintas Halaman Terbuka Langsung:** Laci popup input kendala (**QC Temuan**) hanya terpasang di kerangka DOM dashboard utama (`dashboard.html`). Jika staff berada di halaman **QC Check** atau **Monitoring** dan menekan menu **QC Temuan**, sistem melakukan redirect ke `dashboard.html?openFinding=true`. 
*   Saat dashboard dimuat, parameter URL dibaca secara otomatis untuk membuka drawer pengisian temuan lapangan secara instan, lalu menyembunyikan parameter URL dari riwayat browser menggunakan `window.history.replaceState`.

---

## 8. Ekspor Integrasi Google Sheets

Ekspor data operasional diintegrasikan ke spreadsheet eksternal menggunakan Google Apps Script sebagai perantara webhook.
Kemampuan ekspor meliputi:
*   Sinkronisasi data suhu monitoring harian.
*   Sinkronisasi laporan pemeriksaan QC.
*   Sinkronisasi laporan kendala dapur (QC Temuan).
*   Ekspor historis berdasarkan rentang tanggal tertentu yang dipilih admin.

Setiap payload ekspor dikirimkan secara asinkron dari backend Flask menuju URL webhook Apps Script, yang kemudian menulis baris data baru ke lembar Google Sheets yang ditentukan.

---

## 9. Keamanan & Kestabilan Sistem

*   **Pemisahan Akses (Role-Based Access):** Logika verifikasi hak akses divalidasi di setiap endpoint API Flask. Tampilan antarmuka hanya menyesuaikan visibilitas elemen, namun hak eksekusi tetap diamankan oleh backend.
*   **Keamanan Token Sesi:** Sesi login divalidasi menggunakan token JWT. Akun demo admin dibatasi secara ketat sehingga hanya dapat membaca data tanpa memodifikasi isi database.
*   **Variabel Lingkungan (Environment Variables):** Kunci API, URL database Supabase, kunci enkripsi JWT, dan alamat webhook Google Apps Script disimpan secara aman di variabel lingkungan server, bukan di dalam kode aplikasi.

---

## 10. Strategi Pengujian (Testing)

Kestabilan operasional dapur dijamin oleh suite pengujian otomatis menyeluruh:
*   **Pytest backend:** Mengetes integritas API, validasi token, aturan duplikasi data suhu harian, alur recheck, dan hak akses demo.
*   **Pengujian regresi:** Memastikan modifikasi antarmuka baru tidak merusak alur pengisian checklist QC dan pengiriman laporan harian.
