# ERD QC Enterprise

Dokumen ini menggambarkan rancangan relasi data utama pada QC Enterprise, sistem Quality Control Central Kitchen berbasis web.

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

    ITDV_MODULES {
        uuid id PK
        string slug
        string title
        string description
        string content
        int order_index
        boolean is_active
        datetime deleted_at
        datetime created_at
        datetime updated_at
    }

    ITDV_MODULE_MINI_QUIZZES {
        uuid id PK
        uuid module_id FK
        string question
        json options
        string correct_answer
        string explanation
        int order_index
        boolean is_active
        datetime deleted_at
    }

    ITDV_QUIZ_QUESTIONS {
        uuid id PK
        string question
        json options
        string correct_answer
        string category
        string difficulty
        boolean is_active
        datetime deleted_at
    }

    ITDV_SIMULATIONS {
        uuid id PK
        string title
        string scenario
        json choices
        string expected_answer
        string feedback
        boolean is_active
        datetime deleted_at
    }

    ITDV_CERTIFICATES {
        uuid id PK
        uuid user_id FK
        string certificate_code
        float score
        string status
        json metadata
        datetime issued_at
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
    ITDV_MODULES ||--o{ ITDV_MODULE_MINI_QUIZZES : "memiliki mini quiz"
    USERS_STAFF_ACCOUNTS ||--o{ ITDV_CERTIFICATES : "mendapat sertifikat"
```

Diagram ini menunjukkan struktur data utama yang mendukung traceability QC Enterprise. Relasi penting meliputi produk ke batch produksi, batch ke QC report, QC report ke findings, user ke aktivitas monitoring, serta modul ITDV ke mini quiz dan sertifikat.
