# Sequence Diagram QC Central Kitchen

Dokumen ini menggambarkan interaksi antar komponen pada workflow utama QC Central Kitchen.

## Staff Submit Monitoring

```mermaid
sequenceDiagram
    actor Staff as Staff QC
    participant FE as Frontend
    participant API as Flask API
    participant Service as Service Layer
    participant DB as Supabase PostgreSQL
    participant Audit as Audit Trail

    Staff->>FE: Buka monitoring suhu
    FE->>API: GET /api/facility/monitoring/schedule/today
    API->>Service: Ambil jadwal dan device
    Service->>DB: Query schedule, device, log hari ini
    DB-->>Service: Data monitoring
    Service-->>API: Jadwal monitoring
    API-->>FE: Response schedule
    Staff->>FE: Submit suhu device dan slot
    FE->>API: POST /api/facility/monitoring/submit
    API->>Service: Validasi payload dan duplicate
    Service->>DB: Cek monitoring_date, slot_time, device_id
    DB-->>Service: Duplicate status
    Service->>DB: Insert temperature log
    Service->>Audit: Catat submit monitoring
    Audit->>DB: Insert audit_logs
    API-->>FE: Submit berhasil
    FE-->>Staff: Tampilkan status berhasil
```

Sequence ini menunjukkan proses staff melakukan submit monitoring suhu. Validasi duplicate dilakukan berdasarkan tanggal, slot, dan device agar data monitoring tetap konsisten.

## Staff Buat Batch

```mermaid
sequenceDiagram
    actor Staff as Staff QC
    actor Cook as Production/Cook
    participant FE as Frontend
    participant API as Flask API
    participant Service as Service Layer
    participant DB as Supabase PostgreSQL
    participant Audit as Audit Trail

    Cook->>Staff: Memberikan informasi proses masak
    Staff->>FE: Buka form batch produksi
    Staff->>FE: Input product, tanggal, cook, quantity, shift
    FE->>API: GET /api/batch/next-code
    API->>Service: Hitung batch_sequence berikutnya
    Service->>DB: Query batch terakhir pada tanggal dan produk
    DB-->>Service: Batch terakhir
    Service-->>API: Batch code berikutnya
    API-->>FE: SKU-YYYYMMDD-001
    FE->>API: POST /api/batch
    API->>Service: Validasi batch dan batch_code
    Service->>DB: Insert production_batches
    Service->>Audit: Catat pembuatan batch
    Audit->>DB: Insert audit_logs
    API-->>FE: Batch berhasil dibuat
    FE-->>Staff: Tampilkan batch code
```

Sequence ini menjelaskan pembuatan batch produksi. Batch code membantu menghubungkan proses masak dengan QC inspection dan reports.

## Staff Submit QC Check

```mermaid
sequenceDiagram
    actor Staff as Staff QC
    participant FE as Frontend
    participant API as Flask API
    participant Storage as Supabase Storage
    participant Service as Service Layer
    participant DB as Supabase PostgreSQL
    participant Audit as Audit Trail

    Staff->>FE: Buka QC Check
    FE->>API: GET /api/batch
    API->>Service: Ambil batch aktif
    Service->>DB: Query production_batches
    DB-->>Service: Daftar batch
    API-->>FE: Daftar batch
    Staff->>FE: Isi inspection dan pilih PASS/HOLD/FAIL
    Staff->>FE: Upload evidence photo
    FE->>Storage: Upload evidence photo
    Storage-->>FE: evidence_photo_url
    FE->>API: POST /api/qc/submit
    API->>Service: Validasi status, lock, dan parent inspection
    Service->>DB: Cek concurrency lock
    DB-->>Service: Lock status
    Service->>DB: Insert qc_reports
    Service->>Audit: Catat QC check
    Audit->>DB: Insert audit_logs
    API-->>FE: QC report berhasil dibuat
    FE-->>Staff: Tampilkan hasil QC
```

Sequence ini menggambarkan submit QC check dengan evidence photo, status PASS/HOLD/FAIL, dan validasi concurrency lock untuk mencegah konflik update.

## Admin Export Google Sheets

```mermaid
sequenceDiagram
    actor Admin as Admin QC
    participant FE as Admin Frontend
    participant API as Flask API
    participant Service as Export Service
    participant DB as Supabase PostgreSQL
    participant GAS as Google Apps Script
    participant Sheets as Google Sheets
    participant Audit as Audit Trail

    Admin->>FE: Buka Google Sheets Export
    Admin->>FE: Pilih monitoring, QC, atau date range
    FE->>API: POST /api/admin/google-sheets/export/monitoring
    API->>Service: Validasi admin dan siapkan export
    Service->>DB: Query data sesuai filter
    DB-->>Service: Data export
    Service->>GAS: POST webhook payload
    GAS->>Sheets: Tulis data export
    Sheets-->>GAS: Data tersimpan
    GAS-->>Service: Response sukses
    Service->>Audit: Catat aktivitas export
    Audit->>DB: Insert audit_logs
    API-->>FE: Export berhasil
    FE-->>Admin: Tampilkan status export
```

Sequence ini menunjukkan export data ke Google Sheets melalui Google Apps Script. Admin dapat melakukan export data monitoring, QC, atau historical re-export berdasarkan filter.
