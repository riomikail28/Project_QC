# Use Case Diagram QC Central Kitchen

Dokumen ini menggambarkan aktor dan use case utama pada QC Central Kitchen.

## Use Case Diagram

```mermaid
flowchart LR
    Admin([Admin])
    Staff([Staff QC])
    Cook([Production/Cook])
    Sheets([Google Sheets])
    System([System])

    subgraph QCCentralKitchen["QC Central Kitchen"]
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
        UC14((Validasi Role))
        UC15((Catat Audit Log))
        UC16((Generate Monitoring Schedule))
    end

    Admin --> UC1
    Admin --> UC2
    Admin --> UC9
    Admin --> UC10
    Admin --> UC11

    Staff --> UC1
    Staff --> UC3
    Staff --> UC4
    Staff --> UC5
    Staff --> UC7
    Staff --> UC8

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
```

Diagram ini menjelaskan pembagian tanggung jawab antar aktor. Admin berfokus pada pengawasan, laporan, audit, dan export data. Staff QC berfokus pada input operasional seperti monitoring harian, QC check, pembuatan batch, dan re-check. System menjalankan fungsi internal otomatis seperti validasi role, pencatatan audit log, dan penjadwalan monitoring otomatis.
