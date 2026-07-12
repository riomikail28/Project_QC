# ERD QC Central Kitchen

Dokumen ini menggambarkan rancangan relasi data utama pada QC Central Kitchen, sistem Quality Control Central Kitchen berbasis web.

## Entity Relationship Diagram

```mermaid
erDiagram
    USERS_STAFF_ACCOUNTS {
        uuid id PK
        string name
        string email
        string username
        string password_hash
        string role
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    PRODUCTS {
        uuid id PK
        string sku
        string product_name
        string category
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    PRODUCTION_BATCHES {
        uuid id PK
        uuid product_id FK
        date production_date
        int batch_sequence
        string batch_code
        string cook_name
        int quantity
        string production_shift
        uuid created_by FK
        datetime created_at
        datetime updated_at
    }

    QC_REPORTS {
        uuid id PK
        uuid batch_id FK
        uuid inspector_id FK
        string inspection_status
        int inspection_round
        uuid parent_inspection FK
        string evidence_photo_url
        boolean is_active
        datetime completed_at
        datetime created_at
        datetime updated_at
    }

    QC_FINDINGS {
        uuid id PK
        uuid qc_report_id FK
        string finding_type
        string description
        string severity
        string corrective_action
        datetime created_at
        datetime updated_at
    }

    FACILITY_LOGS {
        uuid id PK
        uuid submitted_by FK
        date monitoring_date
        string slot_time
        string device_id
        string room_id
        string status
        boolean is_late
        string schedule_status
        datetime submitted_at
    }

    TEMPERATURE_LOGS {
        uuid id PK
        uuid submitted_by FK
        date monitoring_date
        string slot_time
        string device_id
        string room_id
        float temperature
        string status
        boolean is_late
        string schedule_status
        datetime submitted_at
    }

    AUDIT_LOGS {
        uuid id PK
        uuid actor_id FK
        string action
        string entity
        uuid entity_id
        json metadata
        datetime created_at
    }

    PRODUCTS ||--o{ PRODUCTION_BATCHES : "memiliki batch"
    USERS_STAFF_ACCOUNTS ||--o{ PRODUCTION_BATCHES : "membuat batch"
    PRODUCTION_BATCHES ||--o{ QC_REPORTS : "diperiksa"
    QC_REPORTS ||--o{ QC_FINDINGS : "memiliki temuan"
    QC_REPORTS ||--o{ QC_REPORTS : "re-check dari"
    USERS_STAFF_ACCOUNTS ||--o{ QC_REPORTS : "melakukan inspeksi"
    USERS_STAFF_ACCOUNTS ||--o{ FACILITY_LOGS : "submit monitoring fasilitas"
    USERS_STAFF_ACCOUNTS ||--o{ TEMPERATURE_LOGS : "submit monitoring suhu"
    USERS_STAFF_ACCOUNTS ||--o{ AUDIT_LOGS : "melakukan aksi"
```

Diagram ini menunjukkan struktur data utama yang mendukung traceability QC Central Kitchen. Relasi penting meliputi produk ke batch produksi, batch ke QC report, QC report ke findings, user ke aktivitas monitoring suhu/fasilitas, serta catatan audit trail dari seluruh transaksi.
