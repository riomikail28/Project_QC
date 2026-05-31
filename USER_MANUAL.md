# User Manual QC Enterprise

## 1. Overview

QC Enterprise adalah sistem Quality Control berbasis web untuk operasional Central Kitchen. Sistem ini membantu admin dan staff dalam melakukan monitoring suhu, pencatatan batch produksi, QC check, upload evidence, laporan, audit trail, pembelajaran ITDV, dan export data ke Google Sheets.

QC Enterprise dibuat agar proses QC lebih rapi, terdokumentasi, mudah ditelusuri, dan dapat digunakan melalui browser maupun tampilan mobile.

## 2. User Roles

### Admin

Admin memiliki akses untuk mengelola dan memantau aktivitas QC secara menyeluruh.

Fitur utama Admin:

- Mengelola dashboard.
- Melihat monitoring.
- Melihat reports.
- Melihat audit trail.
- Mengelola learning.
- Melakukan Google Sheets export.

### Staff

Staff memiliki akses untuk melakukan input data operasional harian.

Fitur utama Staff:

- Input monitoring suhu.
- Melakukan QC check.
- Membuat batch.
- Upload evidence atau foto bukti.
- Melihat profile.

## 3. Cara Login

### Login Admin

1. Buka website QC Enterprise.
2. Masukkan akun admin.
3. Klik tombol login.
4. Jika berhasil, sistem akan membuka dashboard admin.

### Login Staff

1. Buka website QC Enterprise.
2. Masukkan akun staff.
3. Klik tombol login.
4. Jika berhasil, sistem akan membuka dashboard staff.

### Demo Account

Demo account digunakan untuk percobaan, presentasi, atau pengujian sistem.

Jika tersedia, gunakan akun demo sesuai role:

- Demo Admin untuk mencoba fitur admin.
- Demo Staff untuk mencoba fitur staff.

Jangan gunakan akun demo untuk menyimpan data produksi penting.

## 4. Panduan Admin

### Membuka Dashboard Admin

Setelah login sebagai admin, sistem akan menampilkan dashboard admin. Halaman ini digunakan untuk melihat ringkasan kondisi QC, monitoring, laporan, dan aktivitas sistem.

### Melihat KPI

Pada dashboard admin, lihat bagian KPI untuk memantau kondisi utama seperti jumlah monitoring, status QC, laporan, atau aktivitas penting lainnya.

### Melihat Monitoring

1. Buka menu monitoring.
2. Pilih tanggal atau filter jika tersedia.
3. Periksa data monitoring berdasarkan device, ruangan, suhu, dan slot waktu.
4. Pastikan data monitoring sudah sesuai dengan jadwal operasional.

### Melihat Reports

1. Buka menu reports.
2. Pilih jenis laporan yang ingin dilihat.
3. Gunakan filter tanggal atau kategori jika tersedia.
4. Periksa data monitoring, QC, batch, atau alert.

### Melihat Audit Trail

1. Buka menu audit trail.
2. Lihat daftar aktivitas pengguna.
3. Periksa informasi seperti siapa yang melakukan aksi, waktu aksi, dan data yang berubah.

Audit trail membantu admin menelusuri aktivitas penting di sistem.

### Mengelola Learning ITDV

1. Buka menu Learning ITDV atau Learning Management.
2. Tambahkan modul baru jika diperlukan.
3. Ubah materi, mini quiz, simulasi, atau quiz.
4. Nonaktifkan konten yang sudah tidak digunakan.
5. Pastikan materi mudah dipahami oleh staff.

### Export Google Sheets

1. Buka menu Google Sheets export.
2. Pilih jenis data yang ingin diexport.
3. Jalankan test export jika diperlukan.
4. Klik export.
5. Buka Google Sheets untuk memastikan data berhasil masuk.

### Re-Export Data Lama

1. Buka menu export atau reports.
2. Pilih rentang tanggal data lama.
3. Pilih jenis data, seperti monitoring atau QC reports.
4. Jalankan export.
5. Periksa hasilnya di Google Sheets.

### Logout

1. Klik menu profile atau tombol logout.
2. Pilih logout.
3. Pastikan sistem kembali ke halaman login.

## 5. Panduan Staff

### Membuka Dashboard Staff

Setelah login sebagai staff, sistem akan membuka dashboard staff. Dashboard ini berisi akses cepat untuk monitoring suhu, QC check, batch, dan profile.

### Input Monitoring Suhu

1. Buka menu monitoring.
2. Pilih device atau ruangan yang akan diperiksa.
3. Masukkan suhu sesuai hasil pengukuran.
4. Tambahkan catatan jika diperlukan.
5. Simpan data monitoring.

Pastikan suhu yang dimasukkan sesuai dengan kondisi aktual di lapangan.

### Jadwal Monitoring

Monitoring dilakukan pada slot waktu berikut:

- 07:00
- 13:00
- 16:00
- 19:00

Jika slot belum waktunya, sistem dapat membatasi input atau menampilkan informasi bahwa monitoring belum tersedia.

### Membuat Batch Baru

1. Buka menu batch.
2. Pilih produk.
3. Masukkan tanggal produksi.
4. Isi nama cook atau penanggung jawab masak.
5. Masukkan quantity.
6. Pilih shift produksi.
7. Simpan batch.

Satu batch berarti satu kali proses masak.

### QC Check

1. Buka menu QC Check.
2. Pilih batch yang akan diperiksa.
3. Isi data pemeriksaan.
4. Pilih status QC.
5. Upload foto evidence jika diperlukan.
6. Simpan hasil QC.

### Upload Foto

1. Pada form QC Check, pilih upload foto.
2. Ambil foto atau pilih foto dari perangkat.
3. Pastikan foto jelas.
4. Simpan bersama data QC.

Foto digunakan sebagai bukti pemeriksaan atau evidence.

### PASS/HOLD/FAIL

Status QC terdiri dari:

- **PASS:** Produk atau proses memenuhi standar QC.
- **HOLD:** Produk atau proses perlu dicek ulang atau menunggu keputusan.
- **FAIL:** Produk atau proses tidak memenuhi standar QC.

Pilih status sesuai hasil pemeriksaan aktual.

### Re-Check

Re-check digunakan ketika hasil QC perlu diperiksa ulang, biasanya pada status HOLD.

1. Buka data QC yang perlu dicek ulang.
2. Pilih aksi re-check jika tersedia.
3. Lakukan pemeriksaan ulang.
4. Simpan hasil re-check.

Riwayat re-check akan membantu menelusuri perubahan hasil pemeriksaan.

### Profile

1. Buka menu profile.
2. Lihat informasi akun.
3. Periksa nama, role, dan data pengguna.
4. Logout jika sudah selesai menggunakan sistem.

## 6. Panduan Learning ITDV

### Membuka Learning Center

1. Login ke sistem.
2. Buka menu Learning Center atau ITDV Learning.
3. Pilih modul yang ingin dipelajari.

### Mulai Modul

1. Pilih modul.
2. Klik mulai atau buka modul.
3. Ikuti materi sesuai urutan.

### Baca Materi

Baca materi dengan teliti. Materi dapat berisi penjelasan HACCP, QC, prosedur kerja, atau contoh kasus operasional.

### Kerjakan Mini Quiz

1. Setelah membaca materi, kerjakan mini quiz.
2. Pilih jawaban yang paling tepat.
3. Submit jawaban.
4. Periksa hasil atau feedback jika tersedia.

Mini quiz membantu memastikan staff memahami materi sebelum lanjut.

### Simulasi

1. Buka bagian simulasi.
2. Baca skenario.
3. Pilih tindakan yang sesuai.
4. Submit jawaban.
5. Baca feedback dari sistem.

### Quiz Utama

1. Buka quiz utama.
2. Jawab semua pertanyaan.
3. Submit quiz.
4. Lihat skor atau hasil.

### Sertifikat

Sertifikat dapat tersedia setelah pengguna menyelesaikan syarat pembelajaran, seperti modul, mini quiz, simulasi, dan quiz utama.

Jika sertifikat masih terkunci, selesaikan seluruh persyaratan terlebih dahulu.

### Career Recommendation

Career recommendation memberikan arahan pengembangan berdasarkan hasil belajar atau progress pengguna.

Gunakan rekomendasi ini sebagai panduan untuk meningkatkan kemampuan di bidang QC, food safety, atau operasional Central Kitchen.

## 7. Panduan Google Sheets Export

### Test Export

1. Login sebagai admin.
2. Buka menu Google Sheets export.
3. Klik test export.
4. Buka Google Sheets.
5. Pastikan data test berhasil masuk.

### Buka Google Sheets

Gunakan link Google Sheets yang sudah disiapkan oleh admin atau tim pengelola sistem.

### Export All Monitoring

1. Buka menu Google Sheets export.
2. Pilih monitoring.
3. Pilih export all monitoring.
4. Tunggu proses selesai.
5. Periksa data di Google Sheets.

### Export All QC Reports

1. Buka menu Google Sheets export.
2. Pilih QC reports.
3. Pilih export all QC reports.
4. Tunggu proses selesai.
5. Periksa data di Google Sheets.

### Export by Date Range

1. Buka menu export.
2. Pilih tanggal mulai.
3. Pilih tanggal akhir.
4. Pilih jenis data.
5. Klik export.
6. Periksa hasil export di Google Sheets.

## 8. PWA / Install ke HP

QC Enterprise dapat digunakan seperti aplikasi melalui fitur PWA.

### Install di Chrome Android

1. Buka website QC Enterprise di Chrome Android.
2. Buka menu browser.
3. Pilih Add to Home Screen.
4. Konfirmasi nama aplikasi.
5. Buka aplikasi dari home screen.

Setelah terpasang, QC Enterprise dapat dibuka seperti aplikasi biasa.

## 9. Troubleshooting User

### Login Gagal

Kemungkinan penyebab:

- Username atau password salah.
- Akun belum aktif.
- Koneksi internet bermasalah.
- Server sedang error.

Solusi:

- Periksa kembali username dan password.
- Hubungi admin jika akun belum aktif.
- Coba refresh halaman atau login ulang.

### Data Tidak Muncul

Kemungkinan penyebab:

- Filter tanggal tidak sesuai.
- Data belum pernah dibuat.
- Koneksi internet bermasalah.
- User tidak memiliki akses ke data tersebut.

Solusi:

- Periksa filter.
- Refresh halaman.
- Login ulang jika diperlukan.
- Hubungi admin jika data tetap tidak muncul.

### Upload Foto Gagal

Kemungkinan penyebab:

- Ukuran file terlalu besar.
- Format foto tidak didukung.
- Koneksi internet tidak stabil.
- Storage sedang bermasalah.

Solusi:

- Gunakan foto dengan ukuran lebih kecil.
- Gunakan format umum seperti JPG atau PNG.
- Coba upload ulang.

### Monitoring Slot Belum Waktunya

Monitoring hanya dapat dilakukan sesuai slot yang tersedia, seperti 07:00, 13:00, 16:00, dan 19:00.

Jika slot belum waktunya, tunggu sampai jadwal monitoring aktif.

### Batch Duplicate

Batch duplicate terjadi jika batch dengan kode yang sama sudah pernah dibuat.

Solusi:

- Periksa batch code.
- Buat batch dengan sequence berikutnya.
- Hubungi admin jika batch code tidak otomatis berubah.

### Google Sheets Export Gagal

Kemungkinan penyebab:

- Google Apps Script belum aktif.
- Link webhook salah.
- Izin Google Sheets belum sesuai.
- Koneksi internet bermasalah.

Solusi:

- Jalankan test export.
- Periksa Google Sheets.
- Hubungi admin atau pengelola sistem.

## 10. FAQ

### Apa itu batch?

Batch adalah satu kali proses masak. Setiap batch digunakan untuk menelusuri produk, tanggal produksi, cook, quantity, dan hasil QC.

### Apa itu monitoring slot?

Monitoring slot adalah jadwal waktu monitoring. Di QC Enterprise, slot monitoring utama adalah 07:00, 13:00, 16:00, dan 19:00.

### Apa itu re-check?

Re-check adalah pemeriksaan ulang terhadap hasil QC yang perlu diverifikasi kembali, biasanya untuk status HOLD.

### Apa itu PASS/HOLD/FAIL?

- **PASS:** Produk atau proses memenuhi standar.
- **HOLD:** Produk atau proses perlu ditahan sementara dan dicek ulang.
- **FAIL:** Produk atau proses tidak memenuhi standar.

### Apakah data masuk Google Sheets otomatis?

Data dapat masuk ke Google Sheets jika fitur export dijalankan dan integrasi Google Apps Script sudah aktif. Beberapa export dapat dilakukan secara manual oleh admin, termasuk export semua data atau export berdasarkan rentang tanggal.
