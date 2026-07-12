# Activity Diagram QC Central Kitchen

Dokumen ini menggambarkan alur aktivitas utama dalam QC Central Kitchen.

## Login Role Redirect

```mermaid
flowchart TD
    A([Mulai]) --> B[Buka halaman login]
    B --> C[Input username dan password]
    C --> D{Kredensial valid?}
    D -- Tidak --> E[Tampilkan pesan login gagal]
    E --> C
    D -- Ya --> F{Role pengguna}
    F -- Admin --> G[Redirect ke Admin Dashboard]
    F -- Staff --> H[Redirect ke Staff Dashboard]
    G --> I([Selesai])
    H --> I
```

Alur ini menunjukkan proses login dan redirect berdasarkan role. Admin diarahkan ke dashboard admin, sedangkan staff diarahkan ke dashboard staff.

## Monitoring Suhu Harian (Dengan Clickable Slots & Recheck)

```mermaid
flowchart TD
    A([Mulai]) --> B[Staff membuka menu monitoring]
    B --> C[System menampilkan slot 07:00, 13:00, 16:00, 19:00]
    C --> D[Staff klik slot past/present yang ingin diisi]
    D --> E{Apakah slot masa depan / upcoming?}
    E -- Ya --> F[Tampilkan informasi slot belum waktunya]
    F --> C
    E -- No --> G[Pilih room dan device untuk slot terpilih]
    G --> H[Pilih foto evidence via Hybrid Picker]
    H --> I{Pilih Kamera atau Galeri?}
    I -- Kamera --> J[Buka aplikasi kamera langsung]
    I -- Galeri --> K[Buka galeri file pemilih foto]
    J --> L[Input nilai suhu dan kelembapan jika ruangan]
    K --> L
    L --> M{Apakah unit sudah diisi di slot ini?}
    M -- Ya --> N{Apakah mode recheck / allow_duplicate aktif?}
    N -- Tidak --> O[Tampilkan error: Unit sudah diinput]
    O --> Z([Selesai])
    N -- Ya --> P[Simpan log baru sebagai recheck]
    M -- Tidak --> Q[Simpan temperature log baru]
    P --> R[Update progress check & status slot]
    Q --> R
    R --> S[Catat ke audit trail]
    S --> Z
```

Alur ini memungkinkan staff memilih slot waktu secara fleksibel (07:00, 13:00, 16:00, 19:00). Duplicate prevention tetap berjalan, namun staff dapat menginput kembali (recheck) apabila sistem mengaktifkan parameter `allow_duplicate` untuk device tersebut.

## Buat Batch Produksi

```mermaid
flowchart TD
    A([Mulai]) --> B[Staff atau Production/Cook membuka form batch]
    B --> C[Pilih product]
    C --> D[Input production date, cook name, quantity, shift]
    D --> E[System menghitung batch_sequence]
    E --> F[Generate batch_code SKU-YYYYMMDD-001]
    F --> G{Batch code unik?}
    G -- Tidak --> H[Tampilkan error duplicate batch]
    H --> Z([Selesai])
    G -- Ya --> I[Simpan production batch]
    I --> J[Catat audit trail]
    J --> Z
```

Alur ini menjelaskan bahwa satu batch merepresentasikan satu kali proses masak. Batch code digunakan untuk traceability produksi dan QC.

## QC Check (Dengan Hybrid Photo Picker)

```mermaid
flowchart TD
    A([Mulai]) --> B[Staff membuka menu QC Check]
    B --> C[Pilih batch produksi aktif]
    C --> D[Input data inspeksi produk]
    D --> E[Pilih foto evidence via Hybrid Picker jika diperlukan]
    E --> F{Pilih Kamera atau Galeri?}
    F -- Kamera --> G[Buka kamera secara langsung]
    F -- Galeri --> H[Buka galeri penyimpanan file]
    G --> I[Pilih status keputusan PASS/HOLD/FAIL]
    H --> I
    I --> J{Record sedang dikunci user lain?}
    J -- Ya --> K[Tampilkan pesan concurrency warning]
    K --> Z([Selesai])
    J -- Tidak --> L[Simpan QC report]
    L --> M{Status HOLD?}
    M -- Ya --> N[Tandai perlu pemeriksaan ulang / re-check]
    M -- Tidak --> O[Tandai inspeksi selesai]
    N --> P[Catat ke audit trail]
    O --> P
    P --> Z
```

Alur ini mendukung keputusan QC dengan status PASS, HOLD, dan FAIL dengan dukungan opsi pengambilan foto fleksibel (Kamera / Galeri) dan concurrency lock pengaman.

## Re-check

```mermaid
flowchart TD
    A([Mulai]) --> B[Buka QC report aktif]
    B --> C{Perlu re-check?}
    C -- Tidak --> Z([Selesai])
    C -- Ya --> D[Buat inspection_round baru]
    D --> E[Hubungkan parent_inspection]
    E --> F[Input hasil re-check]
    F --> G[Upload evidence tambahan jika ada]
    G --> H[Pilih status terbaru PASS/HOLD/FAIL]
    H --> I[Simpan re-check history]
    I --> J[Update active inspection]
    J --> K[Catat audit trail]
    K --> Z
```

Alur re-check menyimpan riwayat pemeriksaan ulang tanpa menghapus hasil inspeksi sebelumnya. Ini penting untuk audit dan traceability.

## Speed Dial FAB Menu & Navigation

```mermaid
flowchart TD
    A([Mulai]) --> B[Pengguna klik tombol Speed Dial +]
    B --> C[System mendeteksi halaman saat ini]
    C --> D{Jenis Halaman?}
    D -- Monitoring --> E[Tampilkan menu: QC Temuan & QC Check]
    D -- QC Check --> F[Tampilkan menu: Monitoring & QC Temuan]
    D -- Dashboard / Temuan --> G[Tampilkan menu: QC Check & Monitoring]
    E --> H[Pengguna memilih salah satu menu]
    F --> H
    G --> H
    H --> I{Pilihan menu?}
    I -- Ke Halaman Lain --> J[Redirect ke halaman tujuan]
    I -- Klik QC Temuan dari luar Dashboard --> K[Redirect ke dashboard.html?openFinding=true]
    K --> L[Dashboard memuat halaman & auto-open Drawer QC Temuan]
    J --> Z([Selesai])
    L --> Z
```

Alur menu cepat (Speed Dial FAB) menampilkan opsi dinamis dengan menyembunyikan halaman aktif. Jika "QC Temuan" diklik dari luar dashboard, sistem melakukan redirect khusus agar drawer input temuan langsung terbuka di dashboard utama.

## Export Google Sheets

```mermaid
flowchart TD
    A([Mulai]) --> B[Admin membuka menu Google Sheets Export]
    B --> C[Pilih jenis data monitoring atau QC]
    C --> D[Pilih export all atau date range]
    D --> E[System menyiapkan payload]
    E --> F[Kirim webhook ke Google Apps Script]
    F --> G{Webhook berhasil?}
    G -- Tidak --> H[Tampilkan error dan catat log]
    H --> Z([Selesai])
    G -- Ya --> I[Google Apps Script menulis data ke Google Sheets]
    I --> J[Catat audit trail export]
    J --> Z
```
