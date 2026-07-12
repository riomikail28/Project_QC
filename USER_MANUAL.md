# Panduan Penggunaan QC Central Kitchen

## 1. Pendahuluan

QC Central Kitchen adalah aplikasi berbasis web yang dirancang khusus untuk mempermudah operasional Quality Control di dapur pusat (Central Kitchen). Aplikasi ini membantu mendokumentasikan serta memantau data suhu area, pencatatan batch produksi, pengecekan QC (QC check) dengan lampiran foto bukti, pengelolaan temuan/kendala lapangan, audit trail aktivitas pengguna, serta ekspor data ke spreadsheet eksternal lewat Google Sheets.

Sistem ini memiliki tampilan yang ramah diakses lewat HP (mobile-friendly) maupun desktop, serta mendukung teknologi PWA (Progressive Web App) agar staff di area produksi dapat menggunakannya secara praktis.

---

## 2. Peran Pengguna (Roles)

### Admin
Admin memegang kendali penuh untuk memantau performa QC, meninjau kepatuhan dapur, dan melakukan analisis data.
*   **Akses Utama:** Dashboard utama, log monitoring, laporan QC, riwayat aktivitas (audit trail), serta ekspor data ke Google Sheets.
*   **Tanggung Jawab:** Memantau tren deviasi suhu, memvalidasi dan menyetujui batch produksi (approve/reject/hold), mendaftarkan SKU produk, mengatur ruangan dapur, serta memantau operasional harian.

### Staff
Staff bertugas langsung di dapur untuk melakukan pengisian data secara real-time.
*   **Akses Utama:** Dashboard staff, modul input monitoring suhu harian, modul input QC check produk, form pembuatan batch baru, serta halaman profil.
*   **Tanggung Jawab:** Mencatat suhu ruangan dan peralatan sesuai slot waktu yang ditentukan, merekam aktivitas pembuatan batch produk, mengisi checklist QC produk, mengambil foto bukti (evidence), serta mencatat temuan deviasi di lapangan.

---

## 3. Cara Masuk ke Aplikasi (Login)

1.  Buka tautan aplikasi QC Central Kitchen di browser Anda.
2.  Masukkan username dan password akun Anda.
3.  Klik tombol **Login**.
4.  Sistem secara otomatis akan mengarahkan Anda ke halaman yang sesuai dengan peran Anda (Dashboard Admin atau Dashboard Staff).

### Akun Demo (Untuk Uji Coba)
*   **Admin Demo (Hanya Lihat):**
    *   **Username:** `demo_admin`
    *   **Password:** `demoadmin123`
*   **Staff Demo (Bisa Input & Edit):**
    *   **Username:** `demo_staff`
    *   **Password:** `demostaff123`

---

## 4. Panduan untuk Admin

### Memantau Dashboard & KPI
Setelah masuk, halaman utama menampilkan ringkasan performa dapur, seperti persentase kelulusan QC, jumlah deviasi suhu yang terdeteksi, serta daftar produk yang saat ini sedang ditahan (HOLD).

### Meninjau Laporan & Riwayat Log
1.  Pilih menu **Laporan** atau **Monitoring** pada bilah navigasi.
2.  Gunakan filter tanggal atau jenis ruangan untuk menyaring data yang ingin Anda cari.
3.  Anda dapat melihat riwayat suhu di setiap ruangan dapur serta status penyelesaian checklist QC untuk setiap batch.

### Menelusuri Audit Trail (Aktivitas Sistem)
Sistem mencatat setiap perubahan data untuk menjamin transparansi operasional.
1.  Buka menu **Audit Trail**.
2.  Anda dapat melihat siapa yang memasukkan data, kapan data tersebut diubah, serta nilai data sebelum dan sesudahnya.

### Ekspor Data ke Google Sheets
1.  Buka halaman **Google Sheets Export**.
2.  Pilih jenis data yang ingin disinkronkan (data Monitoring Suhu atau Laporan QC).
3.  Gunakan pilihan **Export All** atau tentukan rentang tanggal tertentu (Date Range) untuk mengekspor data historis.
4.  Klik tombol **Export** dan buka tautan spreadsheet Anda untuk memeriksa data yang masuk.

---

## 5. Panduan untuk Staff

### Pengisian Monitoring Suhu Harian (Sistem Slot Waktu)
Aplikasi menampilkan empat slot waktu pemantauan harian:
*   **07:00**
*   **13:00**
*   **16:00**
*   **19:00**

**Cara melakukan input:**
1.  Buka menu **Monitor** pada navigasi bawah.
2.  **Klik slot kartu waktu** yang ingin Anda isi (misalnya, jika sekarang jam 13:00 namun slot jam 07:00 masih kosong, Anda dapat mengeklik slot jam 07:00 untuk melengkapi datanya).
3.  Sistem melarang pengisian slot waktu di masa mendatang (upcoming slot).
4.  Pilih ruangan atau peralatan yang ingin diukur.
5.  Masukkan suhu hasil pengukuran termometer fisik Anda (serta kelembapan jika mengukur ruangan kering).
6.  Tekan **Simpan**.

**Melakukan Pengukuran Ulang (Recheck):**
Jika nilai suhu sebelumnya berada di luar standar (terlalu panas/dingin), Anda diperbolehkan mengirimkan data pengukuran ulang pada slot yang sama. Data baru akan otomatis masuk sebagai log recheck untuk melacak tindakan perbaikan.

---

### Membuat Batch Produksi Baru
Setiap kali proses memasak selesai, staff harus membuat catatan batch baru.
1.  Buka menu **Home** lalu tekan tombol **+** di sudut kanan bawah, atau akses lewat menu navigasi.
2.  Pilih produk (SKU) yang dimasak.
3.  Masukkan tanggal produksi dan nama juru masak (cook).
4.  Isi jumlah porsi/kuantitas hasil masak serta shift kerja yang berjalan.
5.  Sistem akan otomatis menghitung nomor urut dan membuat kode batch unik dengan format `SKU-YYYYMMDD-00X`.

---

### Melakukan Pemeriksaan QC (QC Check)
Setelah batch terdaftar, staff QC wajib memeriksa kualitas produk sebelum dikemas atau didistribusikan.
1.  Buka menu **QC Check** di navigasi bawah.
2.  Pilih kode batch produk yang ingin diperiksa.
3.  Isi parameter kualitas produk (suhu masakan wajib diisi untuk masakan panas, pH, brix, tds, serta berat produk).
4.  Tentukan status kelulusan produk:
    *   **PASS:** Produk lulus uji dan siap didistribusikan.
    *   **HOLD:** Produk bermasalah atau meragukan (misalnya suhu kurang panas). Status ini memerlukan tindakan perbaikan dan recheck ulang sebelum boleh dilepas.
    *   **FAIL:** Produk gagal dan tidak layak dikonsumsi.
5.  Lampirkan foto bukti (evidence) yang memadai.

---

### Pengambilan Foto Bukti (Hybrid Camera & Gallery)
Saat mengunggah foto di menu **QC Temuan, Monitoring, maupun QC Check**, sistem akan menampilkan popup menu di bagian bawah layar:
1.  **Ambil Foto Baru (Kamera):** Opsi ini akan membuka aplikasi kamera bawaan HP Anda secara langsung agar Anda bisa langsung memotret kondisi aktual makanan atau ruangan.
2.  **Pilih dari Galeri / Upload:** Opsi ini membuka galeri HP atau folder file Anda untuk mengunggah foto yang sudah diambil sebelumnya.

*Sistem secara otomatis akan mengompres ukuran foto di sisi perangkat (client-side compression) sebelum dikirim untuk menghemat kuota internet dan mempercepat proses penyimpanan di area dapur yang sinyalnya kurang stabil.*

---

### Fitur Navigasi Cepat (Speed Dial FAB Menu)
Tombol lingkaran biru berikon **+** di sudut kanan bawah adalah menu pintasan cepat:
*   Menu ini hanya akan menampilkan opsi navigasi ke halaman lain (opsi halaman yang sedang Anda buka akan otomatis disembunyikan untuk menghindari kebingungan).
*   Jika Anda sedang berada di halaman **QC Check** atau **Monitoring** dan mengeklik **QC Temuan**, sistem akan otomatis mengarahkan Anda ke beranda utama dan langsung membukakan laci popup pengisian kendala dapur secara instan.

---

## 6. Masalah yang Sering Terjadi (Troubleshooting)

### Kenapa tombol Kamera langsung membuka File Chooser/Galeri?
Pastikan Anda mengeklik opsi **Ambil Foto Baru (Kamera)** pada menu popup bawah. Jika Anda menggunakan HP dengan browser yang sangat lama atau WebView aplikasi pihak ketiga (seperti WhatsApp/Telegram browser), sistem mungkin akan menampilkan pemilih file sebagai alternatif keamanan sistem operasi Anda. Disarankan menggunakan Google Chrome di Android atau Safari di iOS.

### Kenapa Halaman Monitoring Kosong atau Room Tidak Tampil?
Masalah ini biasanya terjadi karena kesalahan format data identitas (UUID) ruangan di database. Pastikan koneksi internet Anda stabil, lalu lakukan refresh halaman. Jika data tetap kosong, hubungi administrator untuk menyelaraskan konfigurasi ruangan di panel admin.

### Mengapa Input Monitoring Terkunci atau Ditolak?
Sistem akan memblokir pengisian jika:
*   Anda mencoba mengeklik slot waktu di masa mendatang (misalnya mencoba mengisi slot 19:00 padahal jam saat ini baru menunjukkan pukul 13:00).
*   Slot waktu yang Anda pilih sudah pernah diisi dan admin menonaktifkan pengaturan recheck/duplikasi untuk peralatan tersebut.

---

## 7. Pertanyaan yang Sering Diajukan (FAQ)

**Apa perbedaan status HOLD dan FAIL pada QC check?**
Status **HOLD** menandakan produk sedang ditahan sementara karena ada parameter yang kurang sesuai (misalnya suhu saat matang kurang tinggi), namun masih bisa diperbaiki (misal dimasak kembali) untuk kemudian diuji ulang (recheck). Status **FAIL** menandakan produk rusak total atau tidak memenuhi syarat mendasar sehingga harus dibuang (discard).

**Apakah foto yang saya ambil akan menghabiskan kuota internet dapur?**
Tidak. Aplikasi ini dilengkapi modul kompresi otomatis berkualitas tinggi di browser. Sebelum foto diunggah ke server, ukurannya akan dikecilkan tanpa merusak kejelasan gambar, sehingga menghemat kuota internet dapur secara signifikan.

**Bagaimana cara menginstall aplikasi ini di HP saya?**
Karena aplikasi ini mendukung PWA, Anda tidak perlu mengunduhnya dari Play Store atau App Store. Cukup buka aplikasi lewat browser Google Chrome (Android) atau Safari (iOS), lalu klik tombol menu browser dan pilih opsi **Tambahkan ke Layar Utama (Add to Home Screen)**. Aplikasi akan terpasang di HP Anda dan dapat dibuka langsung melalui ikon di layar utama.
