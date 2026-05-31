# Activity Diagram QC Enterprise

Dokumen ini menggambarkan alur aktivitas utama dalam QC Enterprise.

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

## Monitoring Suhu Harian

```mermaid
flowchart TD
    A([Mulai]) --> B[Staff membuka menu monitoring]
    B --> C[System menampilkan slot 07:00, 13:00, 16:00, 19:00]
    C --> D[Pilih device dan room]
    D --> E{Slot sudah tersedia?}
    E -- Tidak --> F[Tampilkan informasi slot belum waktunya]
    F --> Z([Selesai])
    E -- Ya --> G[Input suhu dan catatan]
    G --> H{Data device-slot-date sudah ada?}
    H -- Ya --> I[Tolak sebagai duplicate monitoring]
    I --> Z
    H -- Tidak --> J[Simpan temperature log]
    J --> K[Update progress total device x slot]
    K --> L[Catat audit trail]
    L --> Z
```

Alur ini memastikan monitoring suhu dilakukan berdasarkan slot harian dan per-device. Duplicate prevention menjaga agar satu device tidak disubmit lebih dari satu kali pada slot dan tanggal yang sama.

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

## QC Check

```mermaid
flowchart TD
    A([Mulai]) --> B[Staff membuka QC Check]
    B --> C[Pilih batch produksi]
    C --> D[Input data inspeksi]
    D --> E[Upload evidence photo jika diperlukan]
    E --> F[Pilih status PASS/HOLD/FAIL]
    F --> G{Record sedang dikunci user lain?}
    G -- Ya --> H[Tampilkan concurrency warning]
    H --> Z([Selesai])
    G -- Tidak --> I[Simpan QC report]
    I --> J{Status HOLD?}
    J -- Ya --> K[Tandai perlu re-check]
    J -- Tidak --> L[Tandai inspeksi selesai]
    K --> M[Catat audit trail]
    L --> M
    M --> Z
```

Alur ini mendukung keputusan QC dengan status PASS, HOLD, dan FAIL. Evidence photo dan concurrency lock membantu menjaga validitas data inspeksi.

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

Alur ini menjelaskan proses export data dari QC Enterprise ke Google Sheets melalui Google Apps Script webhook. Export dapat dilakukan untuk data monitoring, QC, maupun re-export data lama berdasarkan rentang tanggal.
