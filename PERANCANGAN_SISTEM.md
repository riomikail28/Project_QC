# Bab IV: Perancangan Sistem
**QC Enterprise Management System**

Dokumen ini menyajikan perancangan detail dari **QC Enterprise Management System** sebagai dokumentasi formal sistem informasi. Seluruh perancangan didasarkan pada aplikasi yang telah dibangun tanpa adanya modifikasi fungsional, database, maupun antarmuka pengguna. Perancangan ini disajikan dengan menggunakan standar pemodelan perangkat lunak modern untuk memenuhi kebutuhan dokumentasi akademis skripsi.

---

## 1. Arsitektur Sistem (System Architecture)

Sistem dirancang menggunakan arsitektur bertingkat (**Multi-Tier Architecture / Three-Tier Architecture**) dengan pemisahan tugas yang jelas antara antarmuka pengguna, logika bisnis, dan penyimpanan data.

```mermaid
flowchart TD
    subgraph PresentationLayer["Presentation Layer (Client Side)"]
        Browser["Web Browser (Desktop / Mobile PWA)"]
        LS["Session & Local Storage (JWT Token Storage)"]
        SW["Service Worker (Offline Caching)"]
        Browser <--> LS
        Browser <--> SW
    end

    subgraph ControllerLayer["Routing & Controller Layer (Backend API)"]
        Flask["Flask API App (app.py)"]
        JWTAuth["JWT Middleware (Auth Validation)"]
        Blueprints["Flask Blueprints (admin_routes, batch_routes, etc.)"]
        Flask <--> JWTAuth
        Flask <--> Blueprints
    end

    subgraph ServiceLayer["Business Logic Layer (Services)"]
        AuthServ["Auth Service"]
        BatchServ["Batch Service"]
        QCEng["QC Engine (Inspection & Re-check)"]
        MonServ["Monitoring Service"]
        GAServ["Google Apps Script Service"]
        AuditServ["Audit Service"]
    end

    subgraph DataAccessLayer["Data Access & Storage Layer"]
        SupaClient["Supabase Client Wrapper (supabase_client.py)"]
        Postgres["Supabase PostgreSQL Database"]
        SupaStore["Supabase Storage Bucket (Evidence Photos)"]
    end

    subgraph ExternalLayer["External Integration Layer"]
        GAS["Google Apps Script Webhook"]
        GSheets["Google Sheets Spreadsheet"]
    end

    Browser <-->|HTTP Request / JSON / JWT Header| Flask
    Blueprints <--> ServiceLayer
    ServiceLayer <--> SupaClient
    SupaClient <--> Postgres
    SupaClient <--> SupaStore
    GAServ <-->|HTTPS POST Webhook| GAS
    GAS <--> GSheets
```

### Deskripsi Tingkatan Arsitektur:
1. **Presentation Layer (Frontend)**: Berbasis HTML5, Vanilla CSS, dan Vanilla JavaScript dengan karakteristik *Responsive Layout* (mendukung tampilan Mobile Web dan Desktop). Menggunakan LocalStorage untuk autentikasi persisten via JWT dan Service Worker untuk mendukung mode kerja luring (*offline capability*).
2. **Routing & Controller Layer**: Menggunakan kerangka kerja **Python Flask** yang membagi fungsionalitas ke dalam modul-modul *Blueprint* (seperti `auth`, `monitoring`, `qc`, `batch`, `admin`). Dilengkapi dengan *Middleware* untuk validasi token keamanan JWT secara terpusat pada setiap *endpoint* privat.
3. **Business Logic Layer (Service Layer)**: Kumpulan kelas *Service* yang menangani aturan bisnis (*business rules*) secara khusus, seperti perhitungan runutan pembuatan kode batch (`BatchService`), validasi ambang batas parameter mutu produk (`QCEngine`), pemrosesan alarm deviasi suhu (`MonitoringService`), serta konversi payload data untuk integrasi eksternal (`GoogleAppsScriptService`).
4. **Data Access & Storage Layer**: Menggunakan **Supabase PostgreSQL** sebagai pangkalan data relasional dan **Supabase Storage** untuk menyimpan berkas foto bukti fisik inspeksi mutu (*evidence photo*). Interaksi data dibungkus menggunakan *Supabase Client Wrapper* berbasis REST.
5. **External Integration Layer**: Menggunakan *Webhook* HTTPS POST untuk mengirimkan data transaksi secara *real-time* ke **Google Apps Script** yang bertindak sebagai jembatan penulisan data langsung pada **Google Sheets**.

---

## 2. Flowchart Sistem (System Flowchart)

Flowchart sistem menggambarkan runutan alur operasional umum dari awal pengguna berinteraksi dengan aplikasi hingga terjadinya pengolahan data transaksi dan pelaporan eksternal.

```mermaid
flowchart TD
    A([Mulai]) --> B[Buka Halaman Utama / Login]
    B --> C{Memiliki Sesi Aktif / Token JWT?}
    C -- Ya --> E{Periksa Hak Akses / Role}
    C -- Tidak --> D[Input Username & Password]
    D --> F{Validasi Kredensial Backend?}
    F -- Salah --> D
    F -- Benar --> G[Simpan JWT di LocalStorage]
    G --> E

    E -- Admin QC --> H[Halaman Admin Panel]
    E -- Staff QC --> I[Halaman Staff Dashboard]

    subgraph AdminWorkflow["Alur Kerja Admin QC"]
        H --> H1[Kelola Master Data User/Staff]
        H --> H2[Kelola Master SKU Produk & Fasilitas]
        H --> H3[Lihat Laporan & Histori Transaksi]
        H --> H4[Pantau Rekam Aktivitas / Audit Trail]
        H --> H5[Ekspor Data Manual ke Google Sheets]
    end

    subgraph StaffWorkflow["Alur Kerja Staff QC"]
        I --> I1[Catat Batch Produksi Baru]
        I --> I2[Input Log Pemantauan Suhu Ruang/Alat]
        I --> I3[Lakukan Inspeksi Mutu Batch / QC Check]
        I --> I4[Lakukan Inspeksi Ulang / Re-check]
        I --> I5[Laporkan Temuan Lapangan / QC Finding]
    end

    H1 & H2 & I1 & I2 & I3 & I4 & I5 --> J[Simpan Perubahan ke Supabase Database]
    I2 & I3 & I5 --> K[Upload Foto Bukti ke Supabase Storage]
    J & K --> L[Tulis Rekam Aktivitas ke Audit Logs]
    L --> M{Pemicu Ekspor Google Sheets?}
    M -- Ya (Otomatis/Manual) --> N[Kirim Payload Webhook HTTPS]
    N --> O[Google Sheets Terupdate]
    O --> P([Selesai])
    M -- Tidak --> P
```

---

## 3. Use Case Diagram

Use Case Diagram menggambarkan interaksi antara aktor pengguna dengan fungsionalitas sistem informasi yang disediakan oleh aplikasi.

```mermaid
flowchart LR
    Admin([Admin QC])
    Staff([Staff QC])
    System([Sistem Backend])
    GAS([Google Sheets Webhook])

    subgraph UCEnt["QC Enterprise System Boundary"]
        UC1((Login & Otentikasi))
        UC2((Kelola Akun Staf))
        UC3((Kelola Master SKU Produk))
        UC4((Kelola Layout Fasilitas & Device))
        UC5((Catat Batch Produksi))
        UC6((Catat Pemantauan Suhu Ruang))
        UC7((Input QC Inspection PASS/HOLD/FAIL))
        UC8((Input Re-check Inspeksi))
        UC9((Laporkan Temuan Mutu / QC Finding))
        UC10((Lihat Dashboard Ringkasan))
        UC11((Lihat Riwayat & Laporan))
        UC12((Lihat Audit Trail))
        UC13((Ekspor Data Google Sheets))
        
        UC16((Validasi Token JWT & Otorisasi))
        UC17((Catat Jejak Aktivitas / Audit Log))
        UC18((Kirim Notifikasi Deviasi))
    end

    Admin --> UC1
    Admin --> UC2
    Admin --> UC3
    Admin --> UC4
    Admin --> UC10
    Admin --> UC11
    Admin --> UC12
    Admin --> UC13

    Staff --> UC1
    Staff --> UC5
    Staff --> UC6
    Staff --> UC7
    Staff --> UC8
    Staff --> UC9
    Staff --> UC10
    Staff --> UC11

    UC13 -.-> GAS
    
    System --> UC16
    System --> UC17
    System --> UC18

    UC1 ..> UC16 : "<<include>>"
    UC5 ..> UC17 : "<<include>>"
    UC6 ..> UC17 : "<<include>>"
    UC7 ..> UC17 : "<<include>>"
    UC8 ..> UC17 : "<<include>>"
    UC9 ..> UC17 : "<<include>>"
    UC15 ..> UC17 : "<<include>>"
```

---

## 4. Activity Diagram

Activity Diagram merinci alur kerja dinamis sistem untuk beberapa proses bisnis yang paling krusial.

### A. Login & Penentuan Halaman (Role Redirect)
Menggambarkan bagaimana sistem memverifikasi kredensial pengguna dan mengarahkannya ke dashboard yang tepat berdasarkan hak akses (*role*).

```mermaid
flowchart TD
    start([Mulai]) --> B[Buka Halaman Utama / Login]
    B --> C[Input Username & Password]
    C --> D[Klik Tombol Masuk]
    D --> E{Apakah Kolom Terisi?}
    E -- Tidak --> F[Tampilkan Peringatan Input Wajib]
    F --> C
    E -- Ya --> G[Kirim API Request POST /api/auth/login]
    G --> H{Kredensial Valid di Database?}
    H -- Tidak --> I[Tampilkan Pesan 'Username/Password Salah']
    I --> C
    H -- Ya --> J[Generate Token JWT & Sesi User]
    J --> K[Simpan qc_token & qc_user di LocalStorage]
    K --> L{Apakah Role = Admin?}
    L -- Ya --> M[Redirect ke /admin/admin_panel.html]
    L -- Tidak --> N[Redirect ke /staff/dashboard.html]
    M --> ending([Selesai])
    N --> ending
```

### B. Pencatatan Pemantauan Suhu Harian (Daily Temperature Monitoring)
Menggambarkan proses pencatatan suhu ruang/chiller oleh Staff QC dengan validasi pengisian slot dan pencegahan data duplikat harian.

```mermaid
flowchart TD
    start([Mulai]) --> B[Buka Menu Pemantauan Suhu]
    B --> C[Request Jadwal Slot & Daftar Alat Hari Ini]
    C --> D[System menampilkan status Slot Pagi/Siang/Sore/Malam]
    D --> E[Pilih Ruangan & Alat target]
    E --> F[Klik Input Suhu]
    F --> G{Slot Waktu Aktif & Sesuai Toleransi?}
    G -- Tidak --> H[Tampilkan Peringatan Di luar Jam Toleransi]
    H --> ending([Selesai])
    G -- Ya --> I[Input Angka Suhu Celsius & Catatan]
    I --> J{Apakah Perlu Upload Foto Bukti?}
    J -- Ya --> K[Unggah Gambar Termometer Digital]
    K --> L[Proses Kompresi Gambar di Sisi Klien]
    L --> M[Simpan Gambar ke Supabase Storage & dapatkan URL]
    M --> N[Simpan Log Suhu via API]
    J -- Tidak --> N
    N --> O{Apakah Data Device-Slot-Tanggal Sudah Ada?}
    O -- Ya --> P[Tolak Input & Tampilkan Pesan Duplikat]
    P --> ending
    O -- -- Tidak --> Q[Simpan Log Suhu Baru ke Supabase DB]
    Q --> R{Suhu di Luar Batas Threshold Alat?}
    R -- Ya --> S[Set Status = CRITICAL & Buat Alert Entri]
    R -- Tidak --> T[Set Status = NORMAL]
    S & T --> U[Picu Webhook Sinkronisasi Google Sheets]
    U --> V[Catat Aksi ke Audit Trail]
    V --> ending
```

### C. Pembuatan Batch Produksi (Production Batch Creation)
Menggambarkan proses pencatatan proses masak harian guna menghasilkan kode unik *traceability* produk pangan.

```mermaid
flowchart TD
    start([Mulai]) --> B[Buka Form Tambah Batch Produksi]
    B --> C[Ambil Daftar SKU Produk Aktif dari Database]
    C --> D[Pilih SKU Produk]
    D --> E[Input Nama Juru Masak, Jumlah Qty, Shift Kerja]
    E --> F[Klik Simpan Batch]
    F --> G{Apakah Kolom Valid & Kuantitas > 0?}
    G -- Tidak --> H[Tampilkan Peringatan Validasi Form]
    H --> E
    G -- Ya --> I[System melakukan Query Batch Terakhir di Tanggal Terkait]
    I --> J[Kalkulasi Urutan Nomor: batch_sequence + 1]
    J --> K[Generate Kode Batch: SKU-YYYYMMDD-[Sequence]]
    K --> L{Apakah Kode Batch Unik di Database?}
    L -- Tidak --> M[Ulangi Kalkulasi Nomor Urut berikutnya]
    M --> J
    L -- Ya --> N[Simpan Data Batch ke Tabel production_batches]
    N --> O[Catat Aksi Pembuatan ke Audit Logs]
    O --> ending([Selesai])
```

### D. Inspeksi Mutu & Proses Pengecekan Ulang (QC Inspection & Re-check)
Menggambarkan alur pengambilan keputusan kelayakan produk pangan (PASS, HOLD, FAIL) dan pencatatan riwayat penanganan ulang produk.

```mermaid
flowchart TD
    start([Mulai]) --> B[Buka Modul QC Check / Inspeksi]
    B --> C[Pilih Kode Batch Produksi Aktif]
    C --> D[Ambil Standar Parameter Mutu SKU dari DB]
    D --> E[Input Hasil Uji Parameter pH, Brix, TDS]
    E --> F[Unggah Foto Bukti Fisik Produk]
    F --> G[Klik Kirim Inspeksi]
    G --> H{Apakah Parameter Sesuai Toleransi SKU?}
    H -- Ya --> I[Set Status Mutu = PASS]
    H -- Tidak (Minor Deviasi) --> J[Set Status Mutu = HOLD]
    H -- Tidak (Mayor Deviasi) --> K[Set Status Mutu = FAIL]
    I & J & K --> L[Simpan Laporan ke qc_reports]
    L --> M{Apakah Status = HOLD / FAIL?}
    M -- Tidak --> N[Batch Lulus & Siap Didistribusikan]
    N --> Q[Catat Audit Trail]
    M -- Ya --> O[Kirim Alert ke Panel Admin & Kunci Status Batch]
    O --> P{Dilakukan Tindakan Koreksi & Pengecekan Ulang?}
    P -- Tidak --> Q
    P -- Ya --> R[Klik Tombol Re-check pada Laporan Terkait]
    R --> S[Buat Rekam Inspeksi Baru: inspection_round + 1]
    S --> T[Sematkan ID Laporan Pertama ke parent_inspection]
    T --> U[Input Uji Parameter Baru & Keterangan Perbaikan]
    U --> G
    Q --> ending([Selesai])
```

---

## 5. Sequence Diagram

Sequence Diagram memodelkan interaksi pesan (*messages*) kronologis antar objek di dalam sistem pada skenario operasional penting.

### A. Staff QC Melakukan Submit Monitoring Suhu harian

```mermaid
sequenceDiagram
    actor Staff as Staff QC
    participant FE as Frontend (JS App)
    participant API as Flask API Engine
    participant Service as Monitoring Service
    participant DB as Supabase PostgreSQL
    participant GAS as Google Apps Script Webhook

    Staff->>FE: Buka halaman Monitoring Suhu
    FE->>API: GET /api/facility/monitoring/schedule/today
    API->>Service: get_today_schedule()
    Service->>DB: Query tabel temperature_logs & facilities
    DB-->>Service: Data ruangan, alat, dan status log hari ini
    Service-->>API: Format jadwal log harian
    API-->>FE: HTTP 200 OK (Data JSON)
    FE-->>Staff: Tampilkan status slot waktu & tombol input
    
    Staff->>FE: Input suhu, catatan & unggah foto
    FE->>DB: Upload foto ke Supabase Storage Bucket
    DB-->>FE: Simpan URL gambar (evidence_photo_url)
    FE->>API: POST /api/facility/monitoring/submit
    API->>Service: submit_temperature(payload)
    Service->>Service: Validasi input & deteksi duplikat slot-device-tanggal
    Service->>DB: Cek eksistensi record di database
    DB-->>Service: Status (0 record found)
    Service->>DB: INSERT INTO temperature_logs
    DB-->>Service: Success
    Service->>GAS: POST webhook (Data Monitoring Suhu Baru)
    GAS-->>Service: HTTP 200 OK
    Service->>DB: INSERT INTO audit_logs (Log audit submit)
    DB-->>Service: Success
    Service-->>API: Status Success
    API-->>FE: HTTP 200 OK (Success Message)
    FE-->>Staff: Tampilkan notifikasi "Pencatatan Berhasil disimpan"
```

### B. Staff QC Membuat Batch Produksi Baru

```mermaid
sequenceDiagram
    actor Staff as Staff QC
    participant FE as Frontend (JS App)
    participant API as Flask API Engine
    participant Service as Batch Service
    participant DB as Supabase PostgreSQL

    Staff->>FE: Buka Form Batch Baru
    FE->>API: GET /api/products/active
    API->>DB: Query products WHERE is_active = true
    DB-->>API: Daftar SKU produk
    API-->>FE: HTTP 200 OK
    FE-->>Staff: Tampilkan dropdown pilihan SKU Produk
    
    Staff->>FE: Pilih SKU, input Juru Masak, Qty, Shift, & klik Simpan
    FE->>API: POST /api/batch/create
    API->>Service: create_batch(payload)
    Service->>DB: Query batch terakhir pada production_date & product_id
    DB-->>Service: Record batch terakhir (batch_sequence: 02)
    Service->>Service: Hitung batch_sequence baru = 03
    Service->>Service: Generate batch_code (misal: SAUCE-20260626-003)
    Service->>DB: INSERT INTO production_batches (Data batch baru)
    DB-->>Service: Success
    Service->>DB: INSERT INTO audit_logs (Log audit create batch)
    DB-->>Service: Success
    Service-->>API: Success (batch_code terbuat)
    API-->>FE: HTTP 201 Created (JSON detail batch)
    FE-->>Staff: Tampilkan kode batch unik hasil cetak sistem
```

### C. Staff QC Mengirimkan QC Inspection Report

```mermaid
sequenceDiagram
    actor Staff as Staff QC
    participant FE as Frontend (JS App)
    participant API as Flask API Engine
    participant Service as Inspection Service
    participant DB as Supabase PostgreSQL
    participant Audit as Audit Service

    Staff->>FE: Buka Halaman QC Check
    FE->>API: GET /api/batch/active
    API->>DB: Query production_batches WHERE id NOT IN (SELECT batch_id FROM qc_reports)
    DB-->>API: Daftar batch yang belum diperiksa QC
    API-->>FE: HTTP 200 OK
    FE-->>Staff: Tampilkan list batch produksi aktif
    
    Staff->>FE: Pilih batch, isi parameter uji, upload gambar, & pilih status
    FE->>DB: Simpan gambar bukti di Supabase Storage
    DB-->>FE: Kembalikan URL publik gambar
    FE->>API: POST /api/qc/submit
    API->>Service: submit_inspection(payload)
    Service->>Service: Validasi status kelulusan (PASS/HOLD/FAIL)
    Service->>Service: Periksa concurrency lock (apakah batch sudah diproses user lain)
    Service->>DB: INSERT INTO qc_reports
    DB-->>Service: Success (report_id terbuat)
    Service->>DB: INSERT INTO qc_findings (jika status = HOLD/FAIL)
    DB-->>Service: Success
    Service->>Audit: log_action(actor_id, 'create', 'qc_report', ...)
    Audit->>DB: INSERT INTO audit_logs
    DB-->>Audit: Success
    Service-->>API: Success status
    API-->>FE: HTTP 200 OK
    FE-->>Staff: Tampilkan pesan hasil penentuan mutu berhasil direkam
```

### D. Admin QC Mengekspor Data ke Google Sheets

```mermaid
sequenceDiagram
    actor Admin as Admin QC
    participant FE as Admin Panel UI
    participant API as Flask API Engine
    participant Service as Google Apps Script Service
    participant DB as Supabase PostgreSQL
    participant GAS as Google Apps Script Webhook
    participant GSheets as Google Sheets Spreadsheet

    Admin->>FE: Buka Menu Integrasi Google Sheets & Klik Export Data
    FE->>API: POST /api/admin/export/monitoring-logs
    API->>Service: export_monitoring_logs(payload)
    Service->>DB: Query temperature_logs terfilter (rentang tanggal)
    DB-->>Service: Kumpulan baris data log suhu
    Service->>Service: Konstruksi JSON Payload Terstruktur
    Service->>GAS: HTTPS POST Webhook (Data Log Suhu)
    GAS->>GSheets: Tulis data (APPEND baris / update sheet)
    GSheets-->>GAS: Penulisan Selesai
    GAS-->>Service: Response HTTP 200 OK (Status: Success)
    Service->>DB: INSERT INTO audit_logs (Aksi export admin)
    DB-->>Service: Success
    Service-->>API: Export Success status
    API-->>FE: HTTP 200 OK (Export Sukses)
    FE-->>Admin: Tampilkan pop-up "Sinkronisasi Google Sheets Berhasil!"
```

---

## 6. Entity Relationship Diagram (ERD)

ERD di bawah ini memodelkan struktur tabel, tipe data, kunci utama (*primary key*), kunci asing (*foreign key*), serta hubungan kardinalitas relasional data pada sistem.

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
        string sku UK
        string product_name
        string category
        float standard_temperature
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    PRODUCTION_BATCHES {
        uuid id PK
        uuid product_id FK
        date production_date
        int batch_sequence
        string batch_code UK
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
        string notes
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

    PRODUCTS ||--o{ PRODUCTION_BATCHES : "menghasilkan banyak batch"
    USERS_STAFF_ACCOUNTS ||--o{ PRODUCTION_BATCHES : "mencatat batch"
    PRODUCTION_BATCHES ||--o{ QC_REPORTS : "diperiksa dalam"
    QC_REPORTS ||--o{ QC_FINDINGS : "memiliki detail temuan"
    QC_REPORTS ||--o{ QC_REPORTS : "pengecekan ulang / recheck dari"
    USERS_STAFF_ACCOUNTS ||--o{ QC_REPORTS : "melakukan inspeksi"
    USERS_STAFF_ACCOUNTS ||--o{ FACILITY_LOGS : "mengisi monitoring"
    USERS_STAFF_ACCOUNTS ||--o{ TEMPERATURE_LOGS : "mengisi pencatatan"
    USERS_STAFF_ACCOUNTS ||--o{ AUDIT_LOGS : "melakukan operasi"
```

---

## 7. Class Diagram

Class Diagram menggambarkan komponen utama kode Python Flask di tingkat backend, mencakup pembagian controller (*API Blueprints*), komponen bisnis (*Services*), dan komponen utilitas.

```mermaid
classDiagram
    class SupabaseClient {
        +string supabase_url
        +string supabase_key
        +object client
        +query_table(table_name)
        +insert_record(table_name, data)
        +update_record(table_name, filters, data)
        +delete_record(table_name, filters)
        +upload_file(bucket_name, file_path, file_object)
    }

    class AuthService {
        +login_user(username, password)
        +validate_jwt_token(token)
        +invalidate_session(token)
    }

    class BatchService {
        +create_production_batch(product_id, cook_name, quantity, shift, user_id)
        +calculate_next_batch_sequence(product_id, date)
        +get_batch_by_code(batch_code)
        +filter_batches(filters)
    }

    class QCEngine {
        +validate_product_thresholds(sku, ph, brix, tds)
        +check_critical_control_points(temp, threshold)
    }

    class InspectionService {
        +save_qc_report(batch_id, inspector_id, status, notes, photo_url)
        +save_recheck_report(parent_id, inspector_id, status, notes, photo_url)
        +get_inspection_history(batch_id)
    }

    class MonitoringService {
        +submit_temperature_reading(device_id, room_id, temperature, slot, user_id)
        +get_today_schedule_progress()
        +get_historical_logs(filters)
    }

    class GoogleAppsScriptService {
        +sync_monitoring_data(log_data)
        +sync_inspection_data(qc_data)
        +send_webhook_request(payload)
    }

    class AuditService {
        +write_audit_log(actor_id, action, entity, entity_id, metadata)
        +list_audit_logs(filters)
    }

    class AdminService {
        +create_staff_account(username, password, name, role)
        +register_new_sku(sku, name, temp_std)
        +register_new_facility_device(device_name, type, threshold)
        +generate_dashboard_metrics()
    }

    class LearningService {
        +list_learning_modules()
        +submit_mini_quiz_answer(user_id, question_id, answer)
        +verify_certification_readiness(user_id)
        +generate_certificate(user_id, score)
    }

    %% Controller / Route Layers
    class AuthRoutes {
        +POST /api/auth/login
        +POST /api/auth/logout
    }

    class BatchRoutes {
        +POST /api/batch/create
        +GET /api/batch/next-code
        +GET /api/batch/list
    }

    class QCRoutes {
        +POST /api/qc/submit
        +POST /api/qc/recheck
        +GET /api/qc/history
    }

    class MonitoringRoutes {
        +POST /api/monitoring/submit
        +GET /api/monitoring/schedule
    }

    class AdminRoutes {
        +POST /api/admin/users
        +POST /api/admin/skus
        +POST /api/admin/export/sheets
        +GET /api/admin/audit-logs
    }

    %% Relationships
    AuthRoutes ..> AuthService : "calls"
    BatchRoutes ..> BatchService : "calls"
    QCRoutes ..> InspectionService : "calls"
    QCRoutes ..> QCEngine : "utilizes"
    MonitoringRoutes ..> MonitoringService : "calls"
    AdminRoutes ..> AdminService : "calls"
    AdminRoutes ..> GoogleAppsScriptService : "calls"

    AuthService --> SupabaseClient : "uses"
    BatchService --> SupabaseClient : "uses"
    InspectionService --> SupabaseClient : "uses"
    MonitoringService --> SupabaseClient : "uses"
    AdminService --> SupabaseClient : "uses"
    LearningService --> SupabaseClient : "uses"
    AuditService --> SupabaseClient : "uses"
```

---

## 8. Deployment Diagram

Deployment Diagram memodelkan infrastruktur fisik dan virtual tempat QC Enterprise Management System dideploy dan diakses di lingkungan produksi (*production environment*).

```mermaid
flowchart TB
    subgraph ClientDevice["Client Tier (User Hardware)"]
        PC["Web Browser (Chrome / Safari / Edge)"]
        Mobile["Mobile Web App (Installed PWA)"]
    end

    subgraph CDN["Edge & DNS Routing Tier"]
        VercelCDN["Vercel Edge Network (CDN)"]
        DNS["DNS Server / SSL Handshake"]
    end

    subgraph VercelCloud["Cloud Hosting Tier (Vercel Serverless)"]
        subgraph FEHost["Static Hosting Host"]
            HTMLStatic["HTML, CSS, Client JS"]
        end
        subgraph BEHost["Serverless Runtime"]
            FlaskRuntime["Flask Backend Application (Python 3.9+)"]
        end
    end

    subgraph DatabaseTier["Managed Backend Tier (Supabase Cloud)"]
        subgraph PostgresHost["AWS Hosted Postgres Instance"]
            PostgreSQLDB[("Supabase PostgreSQL Database")]
        end
        subgraph StorageHost["Object Storage"]
            SupaStorageBucket[("Supabase Storage (Evidence Photos)")]
        end
    end

    subgraph GoogleCloudTier["External Spreadsheet Sync Tier (Google Cloud)"]
        GASWebhook["Google Apps Script Engine"]
        GoogleSheets[("Google Sheets Spreadsheet Document")]
    end

    %% Network Connections
    PC & Mobile <-->|HTTPS / SSL| DNS
    DNS <--> VercelCDN
    VercelCDN <-->|Serve Static Assets| HTMLStatic
    VercelCDN <-->|Proxy API Requests /api/*| FlaskRuntime
    FlaskRuntime <-->|Secure PostgreSQL Link (TLS 1.3)| PostgreSQLDB
    FlaskRuntime <-->|API Multipart Form Upload| SupaStorageBucket
    FlaskRuntime <-->|HTTPS Webhook Call| GASWebhook
    GASWebhook <-->|Google internal API| GoogleSheets
```

### Keterangan Infrastruktur:
1. **Client Tier**: Perangkat keras komputer (Desktop) milik Admin/Staff QC dan perangkat seluler (Smartphone/Tablet) yang menjalankan PWA di lingkungan dapur. Klien berkomunikasi hanya melalui protokol terenkripsi HTTPS (SSL/TLS).
2. **CDN & Routing Tier**: Vercel Edge CDN mengarahkan request secara efisien. Aset statis disajikan secara instan dari lokasi server CDN terdekat, sedangkan request dinamis di bawah rute `/api/*` diteruskan ke serverless runtime.
3. **Cloud Hosting Tier (Vercel)**:
   - **Static Hosting**: Tempat mendistribusikan kode markup HTML, stylesheet CSS, dan JavaScript tanpa server overhead.
   - **Serverless Runtime**: Menjalankan program Python Flask di atas kontainer serverless sekali pakai (*on-demand orchestration*) yang secara otomatis diskalakan oleh Vercel.
4. **Managed Backend Tier (Supabase Cloud)**:
   - **Supabase PostgreSQL**: Pangkalan data relasional PostgreSQL yang dihosting di AWS dengan koneksi aman terenkripsi TLS.
   - **Supabase Storage**: Server file *Object Storage* yang menyimpan dokumentasi visual inspeksi batch mutu dan deviasi suhu dalam format JPG/PNG/WEBP.
5. **External Spreadsheet Sync Tier (Google Cloud)**:
   - **Google Apps Script**: Program berbasis cloud JavaScript milik Google yang didesain menerima payload webhook HTTPS dan menulis secara aman (*appending record*) pada file Google Sheets.
   - **Google Sheets**: Dokumen spreadsheet yang menampung laporan mutu dan suhu untuk dibagikan secara mudah ke divisi eksternal perusahaan.
