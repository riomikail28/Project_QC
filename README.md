# Intelligent QC Traceability System 🚀
### Study kasus PT Astro Teknologi Indonesia — Central Kitchen Solutions

Sistem manajemen mutu (Quality Control) berbasis digital yang dirancang khusus untuk operasional **Central Kitchen** skala industri. Proyek ini mengintegrasikan pemantauan fasilitas cerdas dengan pelacakan batch produksi yang ketat untuk memastikan standar keamanan pangan tertinggi.

---

## ✨ Fitur Utama
*   **Secure Role-Based Access:** Login eksklusif untuk Manager (Analitik) dan Operator (Input Lapangan).
*   **Smart Facility Monitoring:** Pemantauan suhu chiller, freezer, dan ambient secara real-time dengan sistem alert otomatis jika melanggar SOP.
*   **Automated Batch Tracking (MFG/EXP):** Input produksi yang intuitif dengan auto-generation Kode Batch berdasarkan tanggal manufaktur dan kedaluwarsa.
*   **AI-Powered OCR Integration:** Pembacaan otomatis nilai pH dan Brix dari foto alat ukur digital untuk meminimalisir *human error*.
*   **PWA (Progressive Web App):** Dapat diinstal di HP/Tablet dan memiliki fitur **Offline-First** (sinkronisasi data otomatis saat sinyal kembali di area produksi).
*   **FastAPI & Supabase Backbone:** Arsitektur backend yang cepat, tangguh, dan skalabel dengan manajemen database cloud.

## 🛠️ Tech Stack
- **Backend:** Python, FastAPI, Uvicorn.
- **Database & Storage:** Supabase (PostgreSQL & Object Storage).
- **Frontend:** HTML5, Vanilla CSS (Tailwind Optimized), JavaScript.
- **Mobile Integration:** PWA, Service Workers, LocalForage.
- **Tools:** OCR Digital Reader, QR/Barcode Scanner Integration.

## 📁 Struktur Proyek (Updated)
```
Project_QC/
├── frontend/                  # All UI files
│   ├── assets/
│   ├── landing.html
│   └── dashboard/
│       ├── index.html
│       ├── login.html
│       ├── camera-module.js
│       ├── manifest.json
│       └── sw.js
├── backend/                   # Python backend
│   ├── main.py
│   ├── product_catalog.py
│   ├── staff_manager.py
│   ├── qc_validator.py
│   └── skills/
├── db/                        # SQL schema
│   ├── schema.sql
│   └── facility_expansion.sql
├── integrations/
│   └── google_apps_script.js
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
**Run:** `cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`


---
*Proyek ini dikembangkan untuk tujuan pemenuhan tugas akhir akademis.bisa dikembangkan lebih lanjut*


Username: admin | Password: admin123 -> Mendapatkan akses Admin (kendali penuh)
Username: staff | Password: 1234 -> Mendapatkan akses Staff (mengerjakan tugas QC)
