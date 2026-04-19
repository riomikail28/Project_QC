# Intelligent QC Traceability System 🚀
### PT Astro Teknologi Indonesia — Central Kitchen Solutions

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

## 📁 Struktur Proyek
- `/main.py` - Core API Server (FastAPI).
- `/dashboard/` - Antarmuka Dashboard (Login, PWA, Monitoring).
- `/skills/` - Modul Pintar (OCR Reader, Auto Reporter, Parametric Checker).

---
*Proyek ini dikembangkan untuk tujuan komersialisasi B2B dan pemenuhan tugas akhir akademis.*
