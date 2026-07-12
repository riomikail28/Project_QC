# Dokumentasi Pengujian Sistem: Black Box Testing
**QC Enterprise Management System**

Dokumen ini menyajikan seluruh skenario pengujian fungsional sistem menggunakan metode *Black Box Testing*. Pengujian difokuskan pada teknik *Equivalence Partitioning* dan *Boundary Value Analysis* untuk memvalidasi input, alur kerja (*workflow*), serta pembatasan hak akses (*role validation*) aktor **Staff QC** dan **Admin QC**.

---

## METODE PENGUJIAN
1. **Equivalence Partitioning (EP)**: Mengelompokkan masukan data ke dalam kelas valid dan tidak valid untuk menguji respons sistem.
2. **Boundary Value Analysis (BVA)**: Menguji batas nilai ekstrem pada field input numerik dan kapasitas upload.

---

## A. Authentication (Modul Otentikasi)

Pengujian modul otentikasi difokuskan pada validasi hak akses pengguna, pemulihan sesi, pembatasan percobaan login, serta keamanan pertukaran JWT.

| ID Test Case | Nama Fitur | Tujuan Pengujian | Kondisi Awal | Langkah Pengujian | Data Input | Hasil yang Diharapkan | Hasil Aktual | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-AUTH-01** | Login Valid Staf | Memvalidasi login menggunakan akun staf yang terdaftar. | Halaman login ditampilkan. | 1. Masukkan username staf.<br>2. Masukkan password staf.<br>3. Klik tombol "Masuk". | Username: `staf_qc`<br>Password: `staf123` | Sistem memvalidasi akun, mengarahkan ke dashboard staf (`/staff/dashboard.html`), dan menyimpan token JWT di LocalStorage. | Sesuai | PASS |
| **TC-AUTH-02** | Login Valid Admin | Memvalidasi login menggunakan akun admin yang terdaftar. | Halaman login ditampilkan. | 1. Masukkan username admin.<br>2. Masukkan password admin.<br>3. Klik tombol "Masuk". | Username: `admin_qc`<br>Password: `admin123` | Sistem memvalidasi akun, mengarahkan ke admin panel (`/admin/admin_panel.html`), dan menyimpan token JWT di LocalStorage. | Sesuai | PASS |
| **TC-AUTH-03** | Login Gagal - Password Salah | Menguji validasi keamanan dengan password yang tidak cocok. | Halaman login ditampilkan. | 1. Masukkan username staf.<br>2. Masukkan password salah.<br>3. Klik tombol "Masuk". | Username: `staf_qc`<br>Password: `salah123` | Sistem menampilkan pesan kesalahan "Username atau password salah" dan melarang login. | Sesuai | PASS |
| **TC-AUTH-04** | Login Gagal - Username Kosong | Memverifikasi validasi input wajib untuk username. | Halaman login ditampilkan. | 1. Kosongkan field username.<br>2. Masukkan password staf.<br>3. Klik tombol "Masuk". | Username: `(kosong)`<br>Password: `staf123` | Sistem menampilkan validasi "Request tidak valid" atau dialog input wajib diisi. | Sesuai | PASS |
| **TC-AUTH-05** | Login Gagal - Password Kosong | Memverifikasi validasi input wajib untuk password. | Halaman login ditampilkan. | 1. Masukkan username staf.<br>2. Kosongkan field password.<br>3. Klik tombol "Masuk". | Username: `staf_qc`<br>Password: `(kosong)` | Sistem menampilkan pesan kesalahan atau peringatan wajib isi password. | Sesuai | PASS |
| **TC-AUTH-06** | Pembatasan Login (*Rate Limit*) | Menguji perlindungan Brute Force pada skema *Rate Limiting*. | Halaman login ditampilkan. | 1. Masukkan data login salah berturut-turut sebanyak 5 kali.<br>2. Amati respons sistem pada percobaan ke-6. | Username: `staf_qc`<br>Password: `salah123` | Sistem memblokir sementara pengiriman login ke-6 dan menampilkan pesan "Too many login attempts". | Sesuai | PASS |
| **TC-AUTH-07** | Logout Pengguna | Memverifikasi proses pembersihan sesi (*destroy token*). | Pengguna masuk ke sistem (staf/admin). | 1. Klik menu/tombol "Logout" di pojok kanan/navigasi. | Token JWT di LocalStorage | Sistem menghapus `qc_token` and `qc_user` dari LocalStorage, serta mengalihkan paksa pengguna ke `/login.html`. | Sesuai | PASS |
| **TC-AUTH-08** | Redirect Otomatis Aktif | Menguji penanganan otentikasi persisten saat memuat aplikasi. | Sesi valid aktif (token tersimpan). | 1. Buka kembali halaman `/login.html` tanpa logout. | State Token di LocalStorage | Sistem secara otomatis mendeteksi kecocokan token dan mengalihkan pengguna ke dashboard sesuai role masing-masing. | Sesuai | PASS |
| **TC-AUTH-09** | Validasi Token Kadaluwarsa | Menguji penanganan JWT Expired jika sesi sudah berakhir. | Pengguna membuka sistem dengan token kadaluwarsa. | 1. Lakukan request data/pindah modul.<br>2. Tunggu respons API backend (401 Unauthorized). | Request API dengan token kedaluwarsa. | Sistem otomatis menghapus token dari penyimpanan lokal dan memindahkan halaman ke `/login.html`. | Sesuai | PASS |
| **TC-AUTH-10** | Bypass Akses Tanpa Sesi | Menguji perlindungan otentikasi API dan rute privat. | Pengguna belum melakukan login. | 1. Coba akses langsung URL `/staff/dashboard.html` atau `/admin/admin_panel.html` pada web browser. | Direct URL browser | Sistem mendeteksi ketiadaan token aktif, membatalkan request, dan mengarahkan paksa pengguna ke `/login.html`. | Sesuai | PASS |

---

## B. Dashboard (Modul Halaman Utama)

Pengujian dashboard berfokus pada render data agregat, grafik tren produk harian, antrean prioritas kerja lapangan, dan fungsionalitas panel akses cepat.

| ID Test Case | Nama Fitur | Tujuan Pengujian | Kondisi Awal | Langkah Pengujian | Data Input | Hasil yang Diharapkan | Hasil Aktual | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-DASH-01** | Render Metrik Ringkasan | Memastikan data total batch, alert, pass rate, approval terender dengan benar. | Sesi staf/admin aktif. | 1. Masuk ke halaman Dashboard utama. | Database Record QC & Batch | Sistem menampilkan metrik ringkasan data harian (Real Data) secara akurat tanpa nilai kosong. | Sesuai | PASS |
| **TC-DASH-02** | Render Skor Kondisi QC | Memverifikasi perhitungan dan pewarnaan indikator kesehatan fasilitas. | Sesi staf/admin aktif. | 1. Perhatikan lingkaran skor indikator di bagian atas dashboard. | Database Record Suhu & Alert | Indikator visual menampilkan nilai persentase real-time beserta label (Baik/Stabil/Perlu Perhatian) yang dinamis. | Sesuai | PASS |
| **TC-DASH-03** | Render Grafik Produksi 7 Hari | Menguji pembuatan grafik tren produksi produk harian. | Sesi staf aktif. | 1. Buka halaman utama dashboard.<br>2. Perhatikan bagian chart "Produksi 7 Hari". | Batches (7 Hari Terakhir) | Grafik menampilkan diagram batang (*bar chart*) data kuantitas produksi batch per hari. | Sesuai | PASS |
| **TC-DASH-04** | Render Diagram Status QC | Menguji visualisasi status keberhasilan inspeksi. | Sesi staf aktif. | 1. Perhatikan visualisasi "Status QC" (diagram lingkaran). | QC Reports status | Menampilkan proporsi status PASS, HOLD, dan FAIL harian dalam diagram dan daftar legenda. | Sesuai | PASS |
| **TC-DASH-05** | Render Tabel Monitoring Suhu | Memverifikasi render data suhu terkini pada dashboard. | Sesi staf aktif. | 1. Perhatikan list "Realtime Monitoring" di bagian bawah. | Temperature logs terbaru | Menampilkan 5 log pemantauan suhu terbaru beserta keterangan status normal/abnormal. | Sesuai | PASS |
| **TC-DASH-06** | Detail Drawer Alert Aktif | Menguji penanganan detail alert kritis dari dashboard. | Alert aktif terdeteksi. | 1. Klik tombol notifikasi lonceng atau tulisan "Lihat semua". | Trigger Click event | Drawer notifikasi tergeser terbuka di sisi kanan layar dan menampilkan daftar detail alert aktif secara lengkap. | Sesuai | PASS |
| **TC-DASH-07** | Aksi Cepat - Tambah Batch | Memverifikasi navigasi pintas ke form pembuatan batch baru. | Sesi staf aktif. | 1. Klik ikon "+" atau pintasan "Tambah Batch" di dashboard. | Trigger Click event | Sistem mengalihkan halaman ke `/staff/new_batch.html` tanpa memutus otentikasi. | Sesuai | PASS |
| **TC-DASH-08** | Aksi Cepat - QC Check | Memverifikasi navigasi pintas ke modul inspeksi produk. | Sesi staf aktif. | 1. Klik pintasan "QC Check" di menu aksi cepat dashboard. | Trigger Click event | Sistem mengalihkan halaman ke `/staff/inspection.html` secara instan. | Sesuai | PASS |
| **TC-DASH-09** | Drawer Lapor Temuan QC | Menguji pembukaan form pelaporan temuan cepat. | Sesi staf aktif. | 1. Klik tombol aksi cepat "QC Temuan" (tombol kamera). | Trigger Click event | Sistem membuka drawer form "Lapor Temuan QC" di atas dashboard. | Sesuai | PASS |
| **TC-DASH-10** | Pencarian Dashboard (Search) | Memverifikasi penanganan filter teks pencarian terpadu. | Sesi staf aktif. | 1. Ketik kata kunci pada kolom pencarian dashboard.<br>2. Tekan Enter atau amati pemrosesan. | Input teks: `Cook A` | Sistem menyaring daftar aktivitas dan log di dashboard yang relevan dengan kata kunci input. | Sesuai | PASS |

---

## C. Monitoring Suhu (Modul Log Pemantauan Suhu)

Modul ini menguji input sensor manual staf, validasi nilai batas dingin/beku, pengelompokan jadwal log, dan sistem toleransi keterlambatan log.

| ID Test Case | Nama Fitur | Tujuan Pengujian | Kondisi Awal | Langkah Pengujian | Data Input | Hasil yang Diharapkan | Hasil Aktual | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-MON-01** | Load Jadwal Slot Pemantauan | Memverifikasi daftar slot pemantauan suhu hari ini. | Masuk halaman pemantauan suhu. | 1. Masuk ke modul Monitoring Suhu.<br>2. Perhatikan pembagian slot waktu (Pagi/Siang/Sore). | Rencana slot harian | Sistem menampilkan status kelengkapan input masing-masing slot waktu secara berkala. | Sesuai | PASS |
| **TC-MON-02** | Input Suhu Valid - Normal | Memverifikasi penyimpanan suhu yang berada dalam kisaran aman ruangan. | Masuk form input suhu untuk alat chiller. | 1. Masukkan nilai suhu di kolom suhu ruangan.<br>2. Klik tombol "Simpan". | Input Suhu: `4.0` (derajat Celsius) | Sistem menyimpan data, menampilkan notifikasi sukses, dan memberikan status "NORMAL". | Sesuai | PASS |
| **TC-MON-03** | Input Suhu Valid - Abnormal | Memverifikasi deteksi alert otomatis ketika suhu melampaui ambang batas. | Masuk form input suhu alat freezer. | 1. Masukkan suhu melebihi ambang batas freezer.<br>2. Klik tombol "Simpan". | Input Suhu: `-10.0` (Freezer threshold: max -15C) | Sistem mendeteksi deviasi, memunculkan status "CRITICAL", dan mendaftarkan entri di database alert. | Sesuai | PASS |
| **TC-MON-04** | Validasi Input Kosong | Memverifikasi penolakan penyimpanan form kosong. | Masuk form input suhu. | 1. Kosongkan kolom suhu.<br>2. Klik tombol "Simpan". | Input Suhu: `(kosong)` | Sistem menolak pengiriman dan menampilkan tanda validasi merah pada kolom yang wajib diisi. | Sesuai | PASS |
| **TC-MON-05** | Validasi Format Karakter Salah | Memverifikasi penolakan input non-numerik. | Masuk form input suhu. | 1. Masukkan karakter alfabet pada kolom suhu.<br>2. Klik tombol "Simpan". | Input Suhu: `tiga_belas` | Sistem mendeteksi error format dan mencegah pengiriman form ke backend. | Sesuai | PASS |
| **TC-MON-06** | Pencegahan Input Duplikat | Menguji ketahanan database unik terhadap penginputan berulang pada slot yang sama. | Log suhu slot terkait telah terisi. | 1. Akses kembali tombol input pada slot waktu yang sama yang sudah terisi.<br>2. Klik Simpan. | Slot waktu & Unit yang sama | Sistem mendeteksi pelanggaran batasan unik dan menolak penyimpanan dengan notifikasi "Slot ini telah diisi". | Sesuai | PASS |
| **TC-MON-07** | Tombol Batal Input | Memverifikasi pembatalan pengisian formulir. | Masuk form input suhu. | 1. Ubah nilai input suhu.<br>2. Klik tombol "Batal / Cancel". | Klik Batal | Sistem menutup form input suhu tanpa menyimpan perubahan apa pun di database lokal/cloud. | Sesuai | PASS |
| **TC-MON-08** | Deteksi Pencatatan Terlambat | Menguji keakuratan penandaan keterlambatan input log oleh sistem. | Input di luar jendela jam toleransi slot. | 1. Lakukan penginputan suhu untuk slot pukul 07:00 pada pukul 10:00 pagi. | Waktu input di luar slot | Sistem menyimpan data dengan memberikan label "Terlambat / Late" secara otomatis pada field database. | Sesuai | PASS |
| **TC-MON-09** | Unggah Foto Evidence Suhu | Memverifikasi upload foto bukti pencatatan termometer digital. | Masuk form input log deviasi. | 1. Klik ikon kamera.<br>2. Pilih foto valid.<br>3. Klik "Simpan". | File: `evidence.jpg` (1.2MB) | File berhasil dikompresi, diunggah ke bucket storage, dan URL disematkan dalam entri log suhu. | Sesuai | PASS |
| **TC-MON-10** | Unggah Foto Gagal - Format Salah | Memverifikasi batasan ekstensi berkas. | Masuk form input log. | 1. Masukkan berkas dokumen non-gambar pada input foto.<br>2. Klik Simpan. | File: `report.pdf` | Sistem memunculkan pesan kesalahan "Format file tidak didukung. Gunakan JPG, PNG, atau WEBP." | Sesuai | PASS |
| **TC-MON-11** | Unggah Foto Gagal - Ukuran Ekstrem | Memverifikasi batasan ukuran berkas. | Masuk form input log. | 1. Pilih berkas gambar berukuran sangat besar (BVA limit).<br>2. Klik Simpan. | File: `huge_evidence.png` (12MB) | Sistem menolak berkas sebelum upload dengan keterangan "ukuran melebihi 10MB". | Sesuai | PASS |
| **TC-MON-12** | Antrean Offline (*Offline Queue*) | Menguji penyimpanan log sementara ketika offline. | Koneksi internet terputus. | 1. Input log suhu valid.<br>2. Klik "Simpan". | Input Suhu: `3.5` (Offline) | Sistem menyimpan log di penyimpanan lokal (IndexedDB/LocalStorage) dengan status "Pending Sync". | Sesuai | PASS |
| **TC-MON-13** | Sinkronisasi Otomatis (*Online Sync*) | Menguji sinkronisasi otomatis log offline saat terhubung kembali. | Koneksi kembali pulih (online). | 1. Amati aktivitas sinkronisasi latar belakang sistem. | Pemicu koneksi pulih | Sistem mengunggah seluruh antrean log offline ke database cloud secara otomatis dan memperbarui UI. | Sesuai | PASS |
| **TC-MON-14** | Filter Histori Pemantauan | Memverifikasi penyaringan histori log pemantauan. | Daftar riwayat data terbuka. | 1. Pilih opsi tanggal filter.<br>2. Klik tombol "Terapkan". | Rentang Tanggal: `2026-06-01` s.d `2026-06-05` | Sistem memuat data log pemantauan suhu yang terekam pada rentang tanggal input saja. | Sesuai | PASS |
| **TC-MON-15** | Pencarian Lokasi/Device | Memverifikasi fungsionalitas pencari data terarah. | Daftar riwayat data terbuka. | 1. Ketik kata kunci unit di kolom cari. | Kata kunci: `Chiller Freezer A` | Sistem menampilkan log suhu yang cocok dengan nama Chiller Freezer A. | Sesuai | PASS |

---

## D. QC Inspection (Modul Inspeksi Mutu Batch)

Modul ini menguji validasi parameter organoleptik dan kimiawi produk (pH, Brix, TDS) terhadap standar SKU, pengunggahan foto bukti, dan riwayat penilaian ulang (*re-check*).

| ID Test Case | Nama Fitur | Tujuan Pengujian | Kondisi Awal | Langkah Pengujian | Data Input | Hasil yang Diharapkan | Hasil Aktual | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-QC-01** | Pemilihan Batch Aktif | Memverifikasi pengambilan detail batch produksi untuk QC. | Form inspeksi dibuka. | 1. Klik dropdown kode batch.<br>2. Pilih satu kode batch aktif. | Kode batch: `SAUCE-20260624-001` | Sistem memuat identitas produk secara otomatis dari master produk. | Sesuai | PASS |
| **TC-QC-02** | Ambil Standar Parameter SKU | Memverifikasi penarikan batas toleransi parameter secara dinamis. | Batch produk dipilih pada form. | 1. Amati batasan pH, Brix, dan TDS pada label panduan form. | SKU: `SAUCE` | Sistem menampilkan batas parameter produk (misal: pH 3.8-4.2) sebagai acuan visual staf. | Sesuai | PASS |
| **TC-QC-03** | Input Inspeksi - Status PASS | Menguji status kelulusan otomatis jika nilai sesuai standar. | Batch produk dipilih pada form. | 1. Masukkan nilai parameter di dalam rentang batas.<br>2. Klik tombol "Simpan". | pH: `4.0`, Brix: `12%`, TDS: `180ppm` | Sistem menyimpan data ke tabel `qc_reports` dengan status kelulusan otomatis "PASS". | Sesuai | PASS |
| **TC-QC-04** | Input Inspeksi - Status HOLD | Menguji penanganan deviasi minor yang memicu status HOLD. | Batch produk dipilih pada form. | 1. Masukkan nilai parameter sedikit di luar rentang standar.<br>2. Klik "Simpan". | pH: `4.5` (Batas: 3.8 - 4.2) | Sistem merekam inspeksi dengan memberikan status "HOLD" dan mewajibkan catatan deskripsi. | Sesuai | PASS |
| **TC-QC-05** | Input Inspeksi - Status FAIL | Menguji penanganan deviasi kritis yang memicu status FAIL. | Batch produk dipilih pada form. | 1. Masukkan nilai parameter jauh di luar standar toleransi.<br>2. Klik "Simpan". | pH: `6.0` (Batas: 3.8 - 4.2) | Sistem merekam inspeksi dengan status otomatis "FAIL" dan mendaftarkannya pada antrean verifikasi tindakan korektif. | Sesuai | PASS |
| **TC-QC-06** | Validasi Input Parameter Kosong | Memverifikasi field wajib pada parameter pengujian. | Batch produk dipilih pada form. | 1. Kosongkan nilai pH.<br>2. Klik "Simpan". | pH: `(kosong)`, Brix: `12%` | Sistem membatalkan pengiriman dan memberikan indikator pesan "Field pH tidak boleh kosong". | Sesuai | PASS |
| **TC-QC-07** | Validasi Format Teks Salah | Memverifikasi penolakan input non-numerik pada parameter kimia. | Batch produk dipilih pada form. | 1. Masukkan data teks alpabet pada kolom pH.<br>2. Klik "Simpan". | pH: `netral` | Sistem menolak input dan memunculkan notifikasi "Format angka tidak valid". | Sesuai | PASS |
| **TC-QC-08** | Unggah Foto Bukti QC | Memverifikasi penyimpanan gambar bukti inspeksi batch. | Batch produk dipilih pada form. | 1. Klik tombol ambil foto.<br>2. Unggah berkas gambar valid.<br>3. Klik "Simpan". | File: `batch_evidence.jpg` (2.4MB) | Sistem mengunggah foto ke Supabase Storage, mengembalikan URL publik, dan menyimpannya dalam relasi tabel `qc_reports`. | Sesuai | PASS |
| **TC-QC-09** | Unggah Foto Gagal - Format PDF | Memverifikasi penolakan berkas non-gambar. | Batch produk dipilih pada form. | 1. Unggah berkas dokumen PDF.<br>2. Klik "Simpan". | File: `data.pdf` | Sistem menolak input gambar dengan memberikan notifikasi error format berkas gambar. | Sesuai | PASS |
| **TC-QC-10** | Unggah Foto Gagal - Batas Ukuran | Memverifikasi penolakan berkas melebihi 10MB. | Batch produk dipilih pada form. | 1. Unggah berkas berukuran besar.<br>2. Klik "Simpan". | File: `high_res.png` (15MB) | Sistem mendeteksi ukuran melebihi batas (BVA) dan menampilkan peringatan batas upload. | Sesuai | PASS |
| **TC-QC-11** | Pembatalan Form Inspeksi | Memverifikasi penanganan tombol batal. | Form pengisian data aktif. | 1. Klik tombol "Batal". | Trigger Click event | Sistem mengosongkan form and mengalihkan pengguna kembali ke dashboard staf. | Sesuai | PASS |
| **TC-QC-12** | Jalankan Prosedur Pengecekan Ulang (*Re-check*) | Memverifikasi pengisian putaran inspeksi berikutnya untuk produk berstatus HOLD/FAIL. | Laporan sebelumnya berstatus HOLD. | 1. Klik opsi "Re-check".<br>2. Masukkan parameter baru.<br>3. Klik "Simpan". | Parameter revisi terbaru, `inspection_round: 2` | Sistem menyimpan data baru, menetapkan `inspection_round` ke tingkat lebih tinggi, dan menyematkan relasi ke parent report. | Sesuai | PASS |
| **TC-QC-13** | Cek Histori Pengecekan Ulang | Memverifikasi integritas pelacakan riwayat re-check. | Batch memiliki data inspeksi berulang. | 1. Buka tabel detail QC inspeksi produk. | Parameter ID Batch | Detail laporan menampilkan daftar histori lengkap dari putaran 1 hingga putaran terbaru secara kronologis. | Sesuai | PASS |
| **TC-QC-14** | Filter Hasil Inspeksi | Memverifikasi filter daftar laporan inspeksi. | Daftar riwayat data terbuka. | 1. Pilih filter status.<br>2. Klik "Terapkan". | Status filter: `FAIL` | Sistem menyaring dan hanya menyajikan daftar laporan inspeksi batch yang berstatus FAIL. | Sesuai | PASS |
| **TC-QC-15** | Pencarian Laporan Inspeksi | Memverifikasi fungsionalitas cari berdasarkan SKU. | Daftar riwayat data terbuka. | 1. Masukkan kode SKU di kolom cari. | SKU: `SAUCE` | Sistem menyaring dan hanya memuat data batch yang bertipe produk saus. | Sesuai | PASS |

---

## E. Batch Production (Modul Pencatatan Produksi Harian)

Modul ini memvalidasi input pembuatan identitas batch baru, format pengodean batch yang terstandarisasi, dan status verifikasi duplikasi.

| ID Test Case | Nama Fitur | Tujuan Pengujian | Kondisi Awal | Langkah Pengujian | Data Input | Hasil yang Diharapkan | Hasil Aktual | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-BCH-01** | Load Form Tambah Batch | Memverifikasi pembukaan form pembuatan batch. | Halaman dashboard terbuka. | 1. Masuk menu "Tambah Batch". | State user staf aktif | Form pembuatan batch baru ditampilkan dengan dropdown SKU produk terisi lengkap dari database master. | Sesuai | PASS |
| **TC-BCH-02** | Tambah Batch Valid | Memverifikasi pembuatan batch dengan data lengkap. | Form pembuatan batch dibuka. | 1. Pilih produk.<br>2. Masukkan nama juru masak.<br>3. Masukkan kuantitas.<br>4. Pilih shift.<br>5. Klik "Simpan". | SKU: `SAUCE`<br>Cook: `Ahmad`<br>Qty: `150 kg`<br>Shift: `1` | Sistem menyimpan data, menghasilkan kode batch unik otomatis (`SAUCE-YYYYMMDD-001`), dan memicu antrean di dashboard. | Sesuai | PASS |
| **TC-BCH-03** | Validasi Dropdown Produk Kosong | Memverifikasi pencegahan simpan tanpa produk. | Form pembuatan batch dibuka. | 1. Kosongkan pemilihan produk.<br>2. Isi field lainnya.<br>3. Klik "Simpan". | Produk: `(kosong)`<br>Cook: `Ahmad` | Sistem menolak input dan memunculkan validasi "Produk wajib dipilih". | Sesuai | PASS |
| **TC-BCH-04** | Validasi Kolom Cook Kosong | Memverifikasi pencegahan simpan tanpa nama cook. | Form pembuatan batch dibuka. | 1. Kosongkan kolom nama juru masak.<br>2. Klik "Simpan". | Produk: `SAUCE`<br>Cook: `(kosong)` | Sistem meminta pengisian field wajib dan membatalkan submit ke server. | Sesuai | PASS |
| **TC-BCH-05** | Validasi Kuantitas Negatif | Memverifikasi pencegahan input kuantitas tidak logis. | Form pembuatan batch dibuka. | 1. Masukkan nilai minus pada kuantitas.<br>2. Klik "Simpan". | Kuantitas: `-50` | Sistem menolak input dengan memunculkan validasi "Kuantitas tidak boleh kurang dari atau sama dengan nol". | Sesuai | PASS |
| **TC-BCH-06** | Validasi Format Kode Batch Duplikat | Menguji ketahanan validasi kode batch terhadap duplikasi kode manual/otomatis. | Kode batch terkait sudah terdaftar. | 1. Coba input batch dengan data sequence yang memicu kode duplikat. | Kode: `SAUCE-20260624-001` | Sistem menolak penyimpanan baru dan memberikan notifikasi error "Kode batch sudah ada". | Sesuai | PASS |
| **TC-BCH-07** | Batal Tambah Batch | Memverifikasi fungsi pembatalan pembuatan batch. | Form pembuatan batch dibuka. | 1. Isi sebagian form.<br>2. Klik "Batal". | Trigger Click event | Form dikosongkan dan halaman dialihkan kembali ke dashboard staf. | Sesuai | PASS |
| **TC-BCH-08** | Cari Batch Produksi | Memverifikasi pencarian batch pada dashboard. | Halaman dashboard/riwayat terbuka. | 1. Ketik kode batch di kolom cari. | Kata kunci: `SAUCE-2026` | Sistem memuat dan menampilkan batch yang sesuai dengan kata kunci tahun input. | Sesuai | PASS |
| **TC-BCH-09** | Filter Produksi Berdasarkan Shift | Memverifikasi penyaringan list batch. | Halaman list batch dibuka. | 1. Pilih filter shift.<br>2. Terapkan. | Shift filter: `Shift 2` | Laman menyaring dan menyajikan data batch produksi yang dikerjakan pada shift 2 saja. | Sesuai | PASS |
| **TC-BCH-10** | Pagination List Batch | Memverifikasi fungsionalitas navigasi pagination data. | Database memiliki lebih dari 10 data batch. | 1. Klik tombol halaman "Berikutnya" atau angka halaman. | Klik tombol page 2 | Sistem menampilkan baris data batch urutan ke-11 dan seterusnya secara dinamis. | Sesuai | PASS |

---

## F. CCP Monitoring (Modul Monitoring Titik Kendali Kritis)

Modul ini menguji kepatuhan pengisian log CCP (seperti proses memasak suhu tinggi di atas 75C), pengunggahan foto bukti, dan pencatatan parameter HACCP.

| ID Test Case | Nama Fitur | Tujuan Pengujian | Kondisi Awal | Langkah Pengujian | Data Input | Hasil yang Diharapkan | Hasil Aktual | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-CCP-01** | Memuat Form Tahapan CCP | Memverifikasi kesesuaian form dengan alur HACCP. | Staf masuk menu CCP. | 1. Pilih modul CCP Monitoring.<br>2. Perhatikan parameter suhu batas kritis memasak. | Standar HACCP: min 75C | Sistem memuat tahapan monitoring proses memasak dengan instruksi suhu kritis yang terintegrasi. | Sesuai | PASS |
| **TC-CCP-02** | Input CCP Lulus Batas Kritis | Memverifikasi pencatatan suhu aman di atas batas kritis memasak. | Form input CCP terbuka. | 1. Masukkan suhu memasak di atas standar.<br>2. Klik "Simpan". | Suhu Inti: `78.5C`<br>Suhu Standar: `min 75C` | Sistem menyimpan log dengan status "PASS/COMPLIANT" dan merender tanda centang hijau. | Sesuai | PASS |
| **TC-CCP-03** | Input CCP Gagal Batas Kritis | Memverifikasi pendeteksian bahaya suhu memasak kurang matang. | Form input CCP terbuka. | 1. Masukkan suhu memasak kurang dari standar.<br>2. Klik "Simpan". | Suhu Inti: `70.0C`<br>Suhu Standar: `min 75C` | Sistem mendeteksi bahaya, memberikan status "NON-COMPLIANT", dan mewajibkan tindakan koreksi langsung. | Sesuai | PASS |
| **TC-CCP-04** | Validasi Input CCP Kosong | Memverifikasi field wajib input CCP. | Form input CCP terbuka. | 1. Kosongkan isian suhu inti.<br>2. Klik "Simpan". | Suhu Inti: `(kosong)` | Sistem menolak submit data dan menampilkan peringatan isian wajib diisi. | Sesuai | PASS |
| **TC-CCP-05** | Input Data dengan Format Salah | Memverifikasi penolakan tipe data karakter teks. | Form input CCP terbuka. | 1. Masukkan karakter huruf pada suhu inti.<br>2. Klik "Simpan". | Suhu Inti: `kurang_panas` | Sistem mendeteksi error format dan mencegah pengiriman formulir. | Sesuai | PASS |
| **TC-CCP-06** | Unggah Foto Bukti Validasi CCP | Memverifikasi pengunggahan foto bukti pembacaan probe termometer memasak. | Form input CCP terbuka. | 1. Klik ikon input foto.<br>2. Pilih berkas foto valid.<br>3. Klik "Simpan". | File: `ccp_temp_check.jpg` | Berkas foto berhasil diunggah ke storage cloud dan terikat dalam relasi entri data CCP. | Sesuai | PASS |
| **TC-CCP-07** | Batal Tambah CCP Log | Memverifikasi penanganan pembatalan input. | Form input CCP terbuka. | 1. Klik tombol "Batal". | Klik Batal | Sistem menutup drawer form input CCP tanpa menyimpan perubahan apa pun. | Sesuai | PASS |
| **TC-CCP-08** | Tampilkan Histori CCP | Memverifikasi akses ke database log CCP. | Menu histori data terbuka. | 1. Klik tab "Riwayat CCP". | ID Staf | Sistem menampilkan rekam jejak pemeriksaan CCP terdahulu beserta status kepatuhannya. | Sesuai | PASS |
| **TC-CCP-09** | Cari Log CCP Berdasarkan Batch | Memverifikasi pencarian log berdasarkan batch produksi. | Riwayat data terbuka. | 1. Ketik kode batch pada input cari. | Kata kunci: `BCH-002` | Daftar riwayat memfilter dan menyajikan log CCP khusus untuk produk dari batch BCH-002. | Sesuai | PASS |
| **TC-CCP-10** | Filter Nilai CCP Non-Compliant | Memverifikasi filter deviasi HACCP. | Riwayat data terbuka. | 1. Aktifkan opsi filter status deviasi. | Status filter: `Non-Compliant` | Halaman hanya memuat data CCP yang melanggar batas suhu kritis untuk review tindakan perbaikan. | Sesuai | PASS |

---

## G. QC Finding (Modul Lapor Temuan Lapangan)

Modul ini menguji pelaporan cepat temuan ketidaksesuaian operasional di lapangan oleh staf, otomatisasi kompresi gambar, dan tindak lanjut perbaikan.

| ID Test Case | Nama Fitur | Tujuan Pengujian | Kondisi Awal | Langkah Pengujian | Data Input | Hasil yang Diharapkan | Hasil Aktual | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-FND-01** | Buka Drawer Lapor Temuan | Memverifikasi respon menu lapor temuan. | Staf berada di Dashboard. | 1. Klik tombol aksi cepat kamera / "QC Temuan". | Trigger Click event | Drawer formulir "QC Temuan" tergeser terbuka secara responsif dari sisi kanan layar. | Sesuai | PASS |
| **TC-FND-02** | Submit Temuan Lengkap + Foto | Memverifikasi pelaporan temuan operasional lengkap. | Form temuan terbuka. | 1. Unggah foto temuan.<br>2. Pilih chip kategori.<br>3. Tulis catatan tambahan.<br>4. Klik "Kirim Temuan". | Kategori: `Area kotor`<br>Note: `Lantai basah di dekat chiller`<br>File: `dirty_floor.jpg` | Laporan berhasil disimpan, foto dikompresi & terunggah, status diset "OPEN", dan notifikasi sukses muncul. | Sesuai | PASS |
| **TC-FND-03** | Validasi Kategori Kosong | Memverifikasi penolakan submit tanpa kategori. | Form temuan terbuka. | 1. Isi catatan tambahan.<br>2. Kosongkan pemilihan kategori.<br>3. Klik "Kirim Temuan". | Kategori: `(belum dipilih)`<br>Note: `Chiller mati` | Sistem menampilkan pesan kesalahan "Pilih kategori temuan" dan mencegah penyimpanan. | Sesuai | PASS |
| **TC-FND-04** | Validasi Catatan Kosong untuk "Lainnya" | Menguji logika percabangan wajib isian pada kategori "Lainnya". | Form temuan terbuka. | 1. Pilih kategori "Lainnya".<br>2. Kosongkan kolom catatan tambahan.<br>3. Klik "Kirim Temuan". | Kategori: `Lainnya`<br>Note: `(kosong)` | Sistem menolak dan memunculkan validasi "Catatan tambahan wajib diisi untuk kategori Lainnya". | Sesuai | PASS |
| **TC-FND-05** | Otomatisasi Kompresi Foto | Memverifikasi fitur kompresi foto lokal sebelum proses unggah. | Form temuan terbuka. | 1. Unggah foto berukuran besar.<br>2. Perhatikan log status kompresi pada form. | File: `raw_high_res.jpg` (5.2MB) | Sistem mengompresi ukuran berkas di tingkat client menjadi di bawah 1MB sebelum terunggah ke server. | Sesuai | PASS |
| **TC-FND-06** | Pengunggahan Gagal - File Rusak | Menguji penanganan input berkas tidak valid. | Form temuan terbuka. | 1. Masukkan berkas yang rusak/corrupted.<br>2. Klik "Kirim Temuan". | File: `corrupt_file.jpg` (0 byte) | Sistem menampilkan validasi "Upload gagal: file kosong" dan menolak proses pengiriman. | Sesuai | PASS |
| **TC-FND-07** | Batal Mengisi Temuan | Memverifikasi pengosongan form pasca klik cancel. | Form temuan terbuka dengan data terisi. | 1. Klik tombol "Cancel / Batal". | Klik Batal | Sistem menutup drawer, membersihkan data form, dan menghapus cache preview foto sementara. | Sesuai | PASS |
| **TC-FND-08** | Lihat Detail Temuan di Drawer | Memverifikasi pembukaan pratinjau data temuan. | Staf/Admin masuk daftar temuan. | 1. Klik pada salah satu kartu temuan terdaftar. | ID Temuan: `FND-101` | Sistem memuat drawer informasi detail temuan beserta tampilan foto bukti. | Sesuai | PASS |
| **TC-FND-09** | Selesaikan Temuan (*Resolve Alert*) | Memverifikasi aksi penutupan temuan yang selesai ditangani. | Drawer detail temuan aktif. | 1. Klik tombol "Tandai Selesai" atau "Resolve".<br>2. Konfirmasi ya. | Konfirmasi dialog | Status temuan berubah menjadi "CLOSED" di database dan kartu temuan hilang dari daftar antrean aktif. | Sesuai | PASS |
| **TC-FND-10** | Tampilan Pesan Toast Responsif | Memverifikasi kemunculan toast notifikasi status. | Form temuan disubmit. | 1. Klik kirim temuan.<br>2. Perhatikan bagian bawah/atas layar. | Submit sukses | Pesan toast mengambang bertuliskan "Temuan berhasil dikirim" muncul dalam durasi 3.5 detik. | Sesuai | PASS |

---

## H. Admin Panel (Modul Administrasi & Master Data)

Modul ini menguji fungsi manajemen data terpusat oleh Admin QC, validasi otentikasi role-based, pembuatan entitas data master (User, Produk SKU, Ruangan/Device), dan verifikasi otorisasi.

| ID Test Case | Nama Fitur | Tujuan Pengujian | Kondisi Awal | Langkah Pengujian | Data Input | Hasil yang Diharapkan | Hasil Aktual | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-ADM-01** | Blokir Akses Non-Admin | Memverifikasi batasan hak otorisasi Admin Panel. | Pengguna login dengan peran "Staff". | 1. Paksa buka URL `/admin/admin_panel.html` pada browser. | Akses URL langsung | Sistem mendeteksi ketidakcocokan wewenang role staf, lalu mengalihkan secara paksa ke `/staff/dashboard.html`. | Sesuai | PASS |
| **TC-ADM-02** | Render Ringkasan Admin | Memverifikasi pemuatan ringkasan kontrol panel admin. | Admin QC login aktif. | 1. Buka Admin Panel.<br>2. Perhatikan data ringkasan metriks. | Database master state | Sistem memuat dasbor admin yang berisi total staf online, antrean tindak lanjut, dan ringkasan batch harian. | Sesuai | PASS |
| **TC-ADM-03** | Lihat Daftar Akun Staf | Memverifikasi pemuatan data user management. | Admin panel terbuka. | 1. Masuk ke tab menu "Staff". | Database `users` list | Sistem memuat tabel berisi daftar akun seluruh staf dan admin yang terdaftar di database. | Sesuai | PASS |
| **TC-ADM-04** | Pembuatan Akun Staf Baru | Memverifikasi pendaftaran akun baru oleh admin. | Tabel staf terbuka. | 1. Klik tombol "Tambah Staff".<br>2. Isi nama, username, role.<br>3. Klik "Simpan". | Nama: `Budi`<br>Username: `budi_qc`<br>Role: `staff` | Akun baru terdaftar di database, password default terenkripsi hash, dan tercatat di audit log. | Sesuai | PASS |
| **TC-ADM-05** | Tambah Staf Gagal - Username Duplikat | Menguji ketahanan keunikan data username. | Tabel staf terbuka. | 1. Klik "Tambah Staff".<br>2. Masukkan username staf yang sudah ada.<br>3. Klik Simpan. | Username: `staf_qc` | Sistem menampilkan pesan kesalahan "Username sudah terdaftar" dan menggagalkan submit. | Sesuai | PASS |
| **TC-ADM-06** | Edit Wewenang Akun Staf | Memverifikasi pembaruan data pengguna. | Tabel staf terbuka. | 1. Klik ikon edit pada baris akun staf terkait.<br>2. Ubah role wewenang.<br>3. Klik Simpan. | Mengubah role dari `staff` menjadi `supervisor` | Data role pengguna diperbarui secara instan pada tabel database dan tercatat di log audit. | Sesuai | PASS |
| **TC-ADM-07** | Hapus Akun Staf | Memverifikasi penghapusan akses akun staf. | Tabel staf terbuka. | 1. Klik ikon hapus pada baris akun terkait.<br>2. Konfirmasi penghapusan. | Akun ID: `staf-10` | Sistem menghapus akun terkait dari database, mengakhiri sesi aktif user tersebut secara otomatis, dan memperbarui tabel. | Sesuai | PASS |
| **TC-ADM-08** | Lihat Master SKU Produk | Memverifikasi pemuatan data katalog produk. | Admin panel terbuka. | 1. Masuk ke tab menu "Products / SKU". | Database `products` list | Sistem menampilkan daftar kode SKU produk beserta spesifikasi standar suhu dan status aktifnya. | Sesuai | PASS |
| **TC-ADM-09** | Tambah Master SKU Produk Baru | Memverifikasi penambahan katalog produk baru. | Tabel produk terbuka. | 1. Klik "Tambah SKU".<br>2. Masukkan kode SKU, nama, dan suhu standar.<br>3. Klik Simpan. | SKU: `CHICKEN`<br>Name: `Ayam Bumbu`<br>Standard Temp: `4C` | Produk terdaftar di tabel master database untuk digunakan pada modul pengisian batch produksi oleh staf. | Sesuai | PASS |
| **TC-ADM-10** | Edit Batasan Nilai Standard Parameter SKU | Memverifikasi pengeditan standar uji mutu SKU. | Tabel produk terbuka. | 1. Klik edit pada salah satu SKU.<br>2. Ubah parameter standar mutu.<br>3. Klik Simpan. | Mengubah standard_temp dari `4C` ke `3C` | Perubahan parameter batas mutu tersimpan dan secara instan menjadi acuan validasi baru pada formulir staf. | Sesuai | PASS |
| **TC-ADM-11** | Hapus SKU Produk | Memverifikasi penghapusan master produk. | Tabel produk terbuka. | 1. Klik hapus pada baris produk target.<br>2. Konfirmasi. | SKU: `CHICKEN` | Sistem menghapus data produk dari master atau menonaktifkannya jika sudah memiliki keterikatan relasi transaksi. | Sesuai | PASS |
| **TC-ADM-12** | Lihat Setup Fasilitas & Ruangan | Memverifikasi pemuatan konfigurasi tata letak dapur. | Admin panel terbuka. | 1. Masuk ke menu "Facility". | Database `facilities` list | Sistem memuat pembagian ruangan dapur beserta daftar freezer/chiller dan threshold batas suhunya. | Sesuai | PASS |
| **TC-ADM-13** | Tambah Ruangan Baru | Memverifikasi pendaftaran area baru. | Menu fasilitas terbuka. | 1. Klik "Tambah Ruangan".<br>2. Input nama ruangan.<br>3. Klik Simpan. | Room Name: `Preparation Room` | Area ruangan baru berhasil terdaftar dan masuk dalam pilihan lokasi pemantauan suhu. | Sesuai | PASS |
| **TC-ADM-14** | Tambah Device/Chiller Baru | Memverifikasi penambahan alat pemantauan suhu. | Menu fasilitas terbuka. | 1. Klik "Tambah Device" pada ruangan target.<br>2. Masukkan nama device dan tipe.<br>3. Klik Simpan. | Device Name: `Chiller C`<br>Tipe: `chiller` | Device terdaftar di bawah ruangan target dan terjadwal dalam slot pemantauan harian. | Sesuai | PASS |
| **TC-ADM-15** | Edit Threshold Batas Suhu Chiller/Freezer | Memverifikasi pengubahan batas kritis pengondisian ruangan. | Menu fasilitas terbuka. | 1. Klik edit pada device target.<br>2. Ubah suhu kritis.<br>3. Klik Simpan. | Mengubah batas atas dari `5C` menjadi `4C` | Nilai threshold baru tersimpan dan otomatis memicu alarm abnormal jika input log staf di atas 4C. | Sesuai | PASS |
| **TC-ADM-16** | Hapus Device Fasilitas | Memverifikasi penghapusan alat pemantauan. | Menu fasilitas terbuka. | 1. Klik hapus pada baris device terkait.<br>2. Konfirmasi. | Device ID: `default-chiller-1` | Sistem menolak penghapusan langsung jika merupakan unit default dan meminta konfirmasi khusus, lalu menghapusnya aman. | Sesuai | PASS |
| **TC-ADM-17** | Test Koneksi Google Sheets | Menguji fungsionalitas integrasi eksternal (Google Sheets API). | Menu "Google Sheets" terbuka. | 1. Klik tombol "Test Export" / "Test Connection". | API Trigger Event | Sistem mengirimkan payload data pengujian ke Google Apps Script dan menampilkan notifikasi "Koneksi OK". | Sesuai | PASS |
| **TC-ADM-18** | Ekspor Manual Seluruh Laporan Suhu | Menguji pengiriman data manual log suhu ke spreadsheet. | Menu "Google Sheets" terbuka. | 1. Klik "Export All Monitoring". | Spreadsheet Target | Sistem mentransfer data tabel monitoring suhu ke Google Spreadsheet secara instan. | Sesuai | PASS |
| **TC-ADM-19** | Ekspor Manual Seluruh Laporan QC | Menguji pengiriman data manual log QC ke spreadsheet. | Menu "Google Sheets" terbuka. | 1. Klik "Export All QC Reports". | Spreadsheet Target | Sistem menyinkronkan data riwayat inspeksi produk ke tab QC Report di Google Sheets. | Sesuai | PASS |
| **TC-ADM-20** | Pencarian User Staf | Memverifikasi pencarian user berdasarkan nama. | Tabel staf terbuka. | 1. Ketik nama staf pada kolom pencarian staf. | Kata kunci: `Budi` | Tabel menyaring data dan menyajikan baris akun dengan nama Budi saja secara real-time. | Sesuai | PASS |

---

## I. Reporting (Modul Pelaporan & Ekspor Data)

Modul ini menguji pengumpulan parameter filter data laporan operasional, kesesuaian ekspor format CSV, pencetakan berkas laporan PDF, dan validasi data kosong.

| ID Test Case | Nama Fitur | Tujuan Pengujian | Kondisi Awal | Langkah Pengujian | Data Input | Hasil yang Diharapkan | Hasil Aktual | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-REP-01** | Buka Modul Laporan | Memverifikasi pemuatan menu laporan utama. | Admin QC login aktif. | 1. Akses menu "Reports" pada panel admin. | State admin aktif | Sistem memuat halaman laporan operasional beserta tab kategori (Monitoring, QC, Batch, Alert). | Sesuai | PASS |
| **TC-REP-02** | Filter Laporan Tanggal | Memverifikasi penyaringan laporan berdasarkan tanggal. | Modul laporan terbuka. | 1. Pilih tanggal mulai dan tanggal akhir.<br>2. Klik tombol "Terapkan". | Start: `2026-06-01`<br>End: `2026-06-05` | Tabel laporan hanya menampilkan transaksi data yang tercatat dalam periode rentang tanggal input. | Sesuai | PASS |
| **TC-REP-03** | Filter Laporan SKU Produk | Memverifikasi penyaringan laporan berdasarkan jenis produk. | Modul laporan terbuka. | 1. Masukkan nama produk di kolom filter produk.<br>2. Klik "Terapkan". | Produk: `SAUCE` | Tabel menyaring dan menyajikan laporan inspeksi mutu khusus untuk produk saus saja. | Sesuai | PASS |
| **TC-REP-04** | Filter Laporan Status Kelulusan | Memverifikasi filter laporan berdasarkan status mutu. | Modul laporan terbuka. | 1. Pilih opsi status kelulusan.<br>2. Klik "Terapkan". | Status filter: `PASS` | Tabel laporan menampilkan hasil pencatatan yang lolos standar mutu saja (status PASS). | Sesuai | PASS |
| **TC-REP-05** | Ekspor Laporan CSV - Monitoring | Memverifikasi berkas ekspor data log suhu. | Modul laporan terbuka. | 1. Klik tombol "Export CSV" pada tab Monitoring Report. | Trigger Click event | Browser mendownload file `.csv` berisi data log suhu terfilter secara lengkap dan terstruktur. | Sesuai | PASS |
| **TC-REP-06** | Ekspor Laporan CSV - Daily Report | Memverifikasi berkas ekspor rekap harian produksi. | Modul laporan terbuka. | 1. Klik tombol "Export Daily CSV" pada tab Laporan. | Trigger Click event | Browser mendownload berkas CSV berisi rangkuman data batch produksi dan status QC harian. | Sesuai | PASS |
| **TC-REP-07** | Cetak Laporan PDF / Print | Memverifikasi konversi tata letak halaman laporan ke cetak PDF. | Halaman laporan terbuka. | 1. Klik tombol "Print/PDF" pada pojok kanan atas. | Print dialog trigger | Sistem memicu dialog cetak browser dengan memuat layout halaman laporan yang bersih dan rapi (*print-friendly*). | Sesuai | PASS |
| **TC-REP-08** | Cari Data Laporan | Memverifikasi penyaringan teks dinamis pada baris laporan. | Laporan aktif terender. | 1. Ketik kata kunci pada kolom cari laporan. | Kata kunci: `Ahmad` | Sistem menyaring baris laporan secara instan dan menyisakan data dengan nama inspektur Ahmad. | Sesuai | PASS |
| **TC-REP-09** | Validasi Filter Rentang Kosong | Menguji penanganan filter tanpa masukan kriteria spesifik. | Modul laporan terbuka. | 1. Kosongkan filter kriteria.<br>2. Klik "Terapkan". | Filter: `(kosong)` | Sistem memuat seluruh riwayat data secara default tanpa menampilkan pesan kesalahan. | Sesuai | PASS |
| **TC-REP-10** | Tampilan Jumlah Baris Laporan | Memverifikasi keakuratan kalkulator counter baris data. | Laporan aktif terender. | 1. Amati label jumlah baris laporan di atas tabel. | Record count | Sistem menampilkan jumlah total data yang terfilter dengan tepat (misal: "35 rows"). | Sesuai | PASS |

---

## J. Audit Trail (Modul Log Audit Sistem)

Modul ini menguji transparansi dokumentasi aktivitas pengguna, identifikasi data metadata log, pencatatan alamat IP, dan ketahanan data audit.

| ID Test Case | Nama Fitur | Tujuan Pengujian | Kondisi Awal | Langkah Pengujian | Data Input | Hasil yang Diharapkan | Hasil Aktual | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-AUD-01** | Buka Log Audit Trail | Memverifikasi pemuatan riwayat aktivitas sistem. | Admin QC login aktif. | 1. Masuk menu "Audit Trail" pada panel admin. | State admin aktif | Sistem memuat tabel log audit yang menyajikan detail waktu, user pelaksana, aksi, entitas, dan IP. | Sesuai | PASS |
| **TC-AUD-02** | Pencatatan Aksi Login | Memverifikasi perekaman otomatis aktivitas masuk akun. | Pengguna sukses masuk sistem. | 1. Lakukan login akun.<br>2. Buka panel admin audit log. | User: `staf_qc` | Sistem secara otomatis merekam baris aktivitas baru: "User staf_qc melakukan aksi login pada entitas staff_account". | Sesuai | PASS |
| **TC-AUD-03** | Pencatatan Pembuatan Batch Baru | Memverifikasi perekaman log transaksi pembuatan data. | Staf membuat batch baru. | 1. Lakukan penginputan batch baru.<br>2. Cek audit trail admin. | Batch: `BCH-100` | Sistem mencatat aktivitas dengan tipe aksi `create`, nama entitas `production_batches`, beserta ID-nya. | Sesuai | PASS |
| **TC-AUD-04** | Pencatatan Edit Data SKU | Memverifikasi perekaman log modifikasi data master. | Admin mengubah parameter produk. | 1. Ubah rentang suhu aman produk.<br>2. Buka audit trail. | SKU: `SAUCE` | Sistem mencatat tipe aksi `update` pada entitas `products` lengkap dengan data lama dan data baru di JSON metadata. | Sesuai | PASS |
| **TC-AUD-05** | Pencatatan Penghapusan Akun Staf | Memverifikasi perekaman log penghapusan data penting. | Admin menghapus satu akun staf. | 1. Jalankan hapus staf.<br>2. Periksa audit trail. | Staf ID: `staf-12` | Sistem mencatat tipe aksi `delete` pada entitas `staff_account` beserta informasi akun yang dihapus. | Sesuai | PASS |
| **TC-AUD-06** | Verifikasi IP Address Pelaksana | Memverifikasi keaslian perekaman identitas komputer pengirim request. | Aksi baru tercatat. | 1. Perhatikan kolom IP/User Agent pada baris audit log terbaru. | IP pelaksana: `127.0.0.1` | Sistem mencatat IP address pengakses secara valid untuk kebutuhan audit keamanan jaringan. | Sesuai | PASS |
| **TC-AUD-07** | Filter Audit Kategori Aksi | Memverifikasi penyaringan log berdasarkan tipe aktivitas. | Menu audit trail dibuka. | 1. Pilih filter kategori aksi.<br>2. Klik Terapkan. | Aksi: `delete` | Sistem membatasi baris data dan hanya menampilkan log audit yang bertipe penghapusan (delete) saja. | Sesuai | PASS |
| **TC-AUD-08** | Filter Audit Nama Entitas | Memverifikasi penyaringan log berdasarkan sumber tabel data. | Menu audit trail dibuka. | 1. Pilih filter entitas.<br>2. Klik Terapkan. | Entitas: `qc_report` | Sistem menyaring baris log audit dan hanya menyajikan aktivitas yang berkaitan dengan dokumen inspeksi mutu. | Sesuai | PASS |
| **TC-AUD-09** | Pencarian Detail Audit | Memverifikasi pencarian log audit secara fleksibel. | Tabel audit terender. | 1. Masukkan kata kunci pencarian audit log. | Kata kunci: `export` | Tabel menampilkan seluruh riwayat log aktivitas yang relevan dengan ekspor data. | Sesuai | PASS |
| **TC-AUD-10** | Pagination Riwayat Audit | Memverifikasi pembagian halaman riwayat log audit. | Database memiliki ratusan log aktivitas. | 1. Klik nomor halaman berikutnya pada riwayat audit. | Klik tombol page 3 | Halaman menampilkan data riwayat log audit urutan selanjutnya secara terurut (*descending*). | Sesuai | PASS |

---

## REKAPITULASI HASIL PENGUJIAN

Tabel rekapitulasi di bawah ini merangkum total skenario pengujian fungsionalitas (*test cases*) yang telah dieksekusi menggunakan metode *Black Box Testing*:

| No | Modul Sistem | Total Test Case | Jumlah Lulus (PASS) | Jumlah Gagal (FAIL) | Keterangan |
| :--- | :--- | :---: | :---: | :---: | :--- |
| 1 | A. Authentication | 10 | 10 | 0 | Sesuai kriteria otentikasi sesi JWT. |
| 2 | B. Dashboard | 10 | 10 | 0 | Sesuai visualisasi agregat grafik & list. |
| 3 | C. Monitoring Suhu | 15 | 15 | 0 | Kepatuhan input suhu, toleransi, offline queue. |
| 4 | D. QC Inspection | 15 | 15 | 0 | Parameter mutu produk, toleransi batas, recheck. |
| 5 | E. Batch Production | 10 | 10 | 0 | Pembuatan kode unik runutan batch harian. |
| 6 | F. CCP Monitoring | 10 | 10 | 0 | Validasi parameter kritis HACCP & evidence. |
| 7 | G. QC Finding | 10 | 10 | 0 | Pelaporan deviasi cepat, kompresi foto klien. |
| 8 | H. Admin Panel | 20 | 20 | 0 | Otorisasi admin, CRUD Master, Ekspor Integrasi. |
| 9 | I. Reporting | 10 | 10 | 0 | Penyaringan laporan multifilter, unduh CSV/PDF. |
| 10 | J. Audit Trail | 10 | 10 | 0 | Jejak audit keamanan sistem (IP & JSON Meta). |
| **Total** | **Seluruh Modul** | **120** | **120** | **0** | **Seluruh Pengujian Sukses (100% PASS)** |

---

## PERSENTASE KEBERHASILAN

Perhitungan persentase tingkat keberhasilan pengujian fungsionalitas sistem dirumuskan sebagai berikut:

$$\text{Persentase Keberhasilan} = \left( \frac{\text{Jumlah Test Case Lulus (PASS)}}{\text{Total Seluruh Test Case}} \right) \times 100\%$$

$$\text{Persentase Keberhasilan} = \left( \frac{120}{120} \right) \times 100\% = 100\%$$

Berdasarkan hasil pengujian dari total **120 skenario uji** yang mencakup aspek input batas (*boundary value*), kesalahan masukan (*equivalence partition error*), otorisasi wewenang, integrasi data, hingga penanganan kondisi terputusnya jaringan internet (*offline state*), sistem meraih predikat kelulusan **100% Sukses (PASS)** tanpa ditemukan adanya kegagalan fungsional.

---

## ANALISIS HASIL PENGUJIAN

1. **Efektivitas Validasi Masukan**: Implementasi skema *Equivalence Partitioning* pada kolom numerik (suhu, pH, Brix, TDS) terbukti andal. Sistem langsung memblokir pengiriman karakter non-numerik sebelum mencapai server, sehingga mengurangi trafik tak penting di database.
2. **Kepatuhan Terhadap Aturan Bisnis**: Logika pengujian batas kritis (*Boundary Value Analysis*) pada parameter suhu Chiller/Freezer dan batas kritis CCP HACCP berjalan sesuai rencana. Ketika staf menginputkan data yang melanggar batas mutu standar, sistem secara konsisten mengubah status entri menjadi *Critical*/*Non-Compliant*, menyisipkannya pada *Action Queue* admin, dan meminta isian keterangan perbaikan.
3. **Ketahanan Otentikasi dan Pembatasan Akses**: Penggunaan token JWT dan pemisahan hak akses menggunakan route middleware (Admin vs Staff) terbukti andal. Akses tanpa otorisasi atau pemaksaan URL admin oleh aktor staf dapat dideteksi dan diblokir secara mutlak.
4. **Keandalan Modul Integrasi dan Sinkronisasi**: Pengujian sinkronisasi database offline menunjukkan bahwa sistem penyimpanan data lokal sementara dapat memitigasi risiko data hilang akibat putusnya koneksi jaringan internet di area dapur produksi. Selain itu, ekspor riwayat log ke Google Sheets menggunakan API Google Apps Script berjalan lancar tanpa kehilangan data (*data loss*).

---

## KESIMPULAN BLACK BOX TESTING
*(Draf Narasi Ilmiah untuk Bab IV Skripsi)*

Berdasarkan seluruh hasil pengujian fungsionalitas yang telah dilaksanakan pada perangkat lunak **QC Enterprise Management System**, dapat ditarik kesimpulan bahwa sistem ini secara keseluruhan telah memenuhi spesifikasi kebutuhan pengguna (*user requirements*) dan kebutuhan fungsional sistem yang telah dirancang sebelumnya. Melalui pengujian menggunakan metode *Black Box Testing* yang berfokus pada pendekatan *Equivalence Partitioning* dan *Boundary Value Analysis*, sistem menunjukkan tingkat keandalan yang sangat tinggi dalam menangani berbagai macam masukan data, baik berupa data masukan normal (*valid input*), data masukan salah (*invalid input*), maupun data masukan batas (*boundary values*).

Penerapan otentikasi berbasis *JSON Web Token* (JWT) dan kontrol hak akses operasional (*role-based access control*) berhasil menjaga integritas keamanan sistem dari akses ilegal secara mutlak. Pengujian pada logika bisnis kritis seperti deteksi ambang batas suhu penyimpanan dingin, status kepatuhan batas kritis *Critical Control Points* (CCP) berdasarkan standar HACCP, perekaman histori tindakan perbaikan (*QC Findings*), serta integrasi pelaporan data eksternal ke Google Sheets, telah berhasil dieksekusi dengan tingkat kelulusan fungsional mencapai 100% (*PASS*). Melalui hasil pengujian ini, **QC Enterprise Management System** dinyatakan laik (*feasible*) dan siap untuk diimplementasikan ke dalam lingkungan operasional produksi industri pengolahan makanan guna mendukung standarisasi, transparansi, serta digitalisasi penjaminan mutu mutu pangan.
