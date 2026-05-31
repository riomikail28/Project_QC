# Use Case Diagram QC Enterprise

Dokumen ini menggambarkan aktor dan use case utama pada QC Enterprise.

## Use Case Diagram

```mermaid
flowchart LR
    Admin([Admin])
    Staff([Staff QC])
    Cook([Production/Cook])
    Sheets([Google Sheets])
    System([System])

    subgraph QCEnterprise["QC Enterprise"]
        UC1((Login))
        UC2((Akses Admin Dashboard))
        UC3((Akses Staff Dashboard))
        UC4((Monitoring Suhu Harian))
        UC5((Monitoring Per Device))
        UC6((Buat Batch Produksi))
        UC7((QC Check PASS/HOLD/FAIL))
        UC8((Re-check Inspection))
        UC9((Lihat Reports))
        UC10((Lihat Audit Trail))
        UC11((Export Google Sheets))
        UC12((Kelola ITDV Learning))
        UC13((Ikuti Learning Center))
        UC14((Validasi Role))
        UC15((Catat Audit Log))
        UC16((Generate Monitoring Schedule))
    end

    Admin --> UC1
    Admin --> UC2
    Admin --> UC9
    Admin --> UC10
    Admin --> UC11
    Admin --> UC12

    Staff --> UC1
    Staff --> UC3
    Staff --> UC4
    Staff --> UC5
    Staff --> UC7
    Staff --> UC8
    Staff --> UC13

    Cook --> UC6
    Staff --> UC6

    UC11 --> Sheets

    System --> UC14
    System --> UC15
    System --> UC16

    UC1 --> UC14
    UC4 --> UC15
    UC6 --> UC15
    UC7 --> UC15
    UC8 --> UC15
    UC12 --> UC15
```

Diagram ini menjelaskan pembagian tanggung jawab antar aktor. Admin berfokus pada pengawasan, laporan, audit, export, dan pengelolaan learning. Staff QC berfokus pada input operasional seperti monitoring, QC check, batch, re-check, dan pembelajaran. System menjalankan validasi role, audit log, dan penjadwalan monitoring.
