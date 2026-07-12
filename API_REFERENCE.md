# Referensi API QC Central Kitchen

Dokumen ini menjelaskan daftar endpoint API utama yang digunakan dalam aplikasi QC Central Kitchen. API ini mendukung autentikasi, pembagian hak akses (role-based access), input monitoring suhu harian, pencatatan batch produksi, pengecekan QC, manajemen temuan lapangan, audit trail, serta ekspor data ke Google Sheets.

---

## 1. Autentikasi & Sesi

### Login Pengguna
Digunakan untuk memverifikasi kredensial pengguna dan mengembalikan token sesi (JWT).
*   **Endpoint:** `POST /api/auth/login`
*   **Payload Request:**
    ```json
    {
      "username": "demo_staff",
      "password": "demostaff123"
    }
    ```
*   **Response Sukses (200 OK):**
    ```json
    {
      "success": true,
      "token": "eyJhbGciOi...",
      "user": {
        "id": "e4b3c2...",
        "name": "Demo Staff",
        "username": "demo_staff",
        "role": "staff"
      }
    }
    ```

### Memeriksa Status Sesi
Digunakan untuk memvalidasi token sesi yang saat ini aktif di browser.
*   **Endpoint:** `GET /api/auth/session`
*   **Headers:** `Authorization: Bearer <token>`
*   **Response Sukses (200 OK):**
    ```json
    {
      "success": true,
      "user": {
        "id": "e4b3c2...",
        "name": "Demo Staff",
        "role": "staff"
      }
    }
    ```

---

## 2. Profil Pengguna

### Mengambil Data Profil
*   **Endpoint:** `GET /api/profile`
*   **Headers:** `Authorization: Bearer <token>`
*   **Response Sukses (200 OK):**
    ```json
    {
      "success": true,
      "profile": {
        "id": "e4b3c2...",
        "name": "Demo Staff",
        "email": "staff@qccentralkitchen.id",
        "username": "demo_staff",
        "role": "staff"
      }
    }
    ```

### Memperbarui Data Profil
*   **Endpoint:** `POST /api/profile/save`
*   **Headers:** `Authorization: Bearer <token>`
*   **Payload Request:**
    ```json
    {
      "name": "Nama Baru Staff",
      "email": "email.baru@qccentralkitchen.id",
      "password": "passwordBaru123"
    }
    ```
*   **Response Sukses (200 OK):**
    ```json
    {
      "success": true,
      "message": "Profil berhasil diperbarui."
    }
    ```

---

## 3. Dashboard Ringkasan (Admin & Staff)

### Mengambil Data Statistik Dashboard
Mengembalikan ringkasan Key Performance Indicators (KPI) dan data grafik.
*   **Endpoint:** `GET /api/dashboard`
*   **Headers:** `Authorization: Bearer <token>`
*   **Response Sukses (200 OK):**
    ```json
    {
      "success": true,
      "statistics": {
        "qc_pass_rate": 94.5,
        "anomalies_detected": 3,
        "active_batches_today": 12,
        "unresolved_findings": 2
      }
    }
    ```

---

## 4. Pemantauan Suhu & Fasilitas (Monitoring)

### Mengambil Jadwal & Status Slot Monitoring Hari Ini
Mendapatkan daftar alat/ruangan dapur serta status pengisian untuk masing-masing slot waktu (07:00, 13:00, 16:00, 19:00).
*   **Endpoint:** `GET /api/facility/monitoring/schedule/today`
*   **Headers:** `Authorization: Bearer <token>`
*   **Response Sukses (200 OK):**
    ```json
    {
      "success": true,
      "date": "2026-07-12",
      "slots": [
        { "time": "07:00", "status": "completed" },
        { "time": "13:00", "status": "active" },
        { "time": "16:00", "status": "upcoming" },
        { "time": "19:00", "status": "upcoming" }
      ],
      "devices": [
        {
          "id": "room-cold-1",
          "name": "Cold Storage 1",
          "type": "room_temp",
          "room_id": "area-1",
          "slots_status": {
            "07:00": { "completed": true, "temperature": 4.2 },
            "13:00": { "completed": false }
          }
        }
      ]
    }
    ```

### Mengirimkan Log Pengukuran Suhu (Submit)
Mengirimkan data pembacaan termometer fisik staff ke database.
*   **Endpoint:** `POST /api/facility/monitoring/submit`
*   **Headers:** `Authorization: Bearer <token>`
*   **Payload Request:**
    ```json
    {
      "monitoring_date": "2026-07-12",
      "slot_time": "13:00",
      "device_id": "room-cold-1",
      "room_id": "area-1",
      "temperature": 3.8,
      "humidity": 65.0,
      "notes": "Suhu normal dan stabil.",
      "allow_duplicate": false
    }
    ```
*   **Response Sukses (200 OK):**
    ```json
    {
      "success": true,
      "message": "Log suhu berhasil disimpan."
    }
    ```

---

## 5. Manajemen Produk (SKU)

### Mengambil Daftar Produk Aktif (Staff)
Mendapatkan produk yang terdaftar untuk pembuatan batch produksi.
*   **Endpoint:** `GET /api/products`
*   **Headers:** `Authorization: Bearer <token>`

### Mengelola Produk (Admin CRUD)
Mengelola daftar produk, kategori, dan lama hari penyimpanan (shelf life).
*   `GET /api/admin/products` - Mengambil semua produk (termasuk tidak aktif).
*   `POST /api/admin/products` - Mendaftarkan produk baru.
*   `PUT /api/admin/products/<id>` - Memperbarui produk.
*   `DELETE /api/admin/products/<id>` - Menonaktifkan produk.

---

## 6. Batch Produksi

### Membuat Batch Produksi Baru
*   **Endpoint:** `POST /api/batch`
*   **Headers:** `Authorization: Bearer <token>`
*   **Payload Request:**
    ```json
    {
      "product_id": "sku-abc-123",
      "production_date": "2026-07-12",
      "cook_name": "Chef Budi",
      "quantity": 150,
      "production_shift": "Pagi"
    }
    ```
*   **Response Sukses (200 OK):**
    ```json
    {
      "success": true,
      "batch_code": "SKU-20260712-001",
      "message": "Batch produksi berhasil dibuat."
    }
    ```

### Mendapatkan Kode Urutan Berikutnya
Mendapatkan nomor urutan masakan selanjutnya untuk tanggal produksi tertentu guna mencegah tabrakan kode batch.
*   **Endpoint:** `GET /api/batch/next-code?product_id=<id>&date=YYYY-MM-DD`
*   **Headers:** `Authorization: Bearer <token>`

---

## 7. Pemeriksaan Kualitas (QC Check)

### Mengirimkan Laporan QC (Submit QC Report)
*   **Endpoint:** `POST /api/qc/submit`
*   **Headers:** `Authorization: Bearer <token>`
*   **Payload Request:**
    ```json
    {
      "batch_id": "batch-uuid-999",
      "inspection_status": "PASS",
      "cooking_temp": 82.5,
      "ph": 6.2,
      "brix": 12.4,
      "tds": 150,
      "gramasi": [100.5, 101.0, 99.8, 100.2, 100.0],
      "evidence_photo_url": "https://storage.supabase.co/qc-evidence/cooking.jpg",
      "recheck": false
    }
    ```
*   **Response Sukses (200 OK):**
    ```json
    {
      "success": true,
      "message": "Laporan pemeriksaan QC berhasil disimpan."
    }
    ```

---

## 8. Laporan Temuan Kendala (QC Findings)

### Mengambil Daftar Temuan Aktif
*   **Endpoint:** `GET /api/findings`
*   **Headers:** `Authorization: Bearer <token>`

### Menyelesaikan Temuan Kendala (Resolve)
*   **Endpoint:** `POST /api/findings/resolve`
*   **Headers:** `Authorization: Bearer <token>`
*   **Payload Request:**
    ```json
    {
      "finding_id": "finding-uuid-888",
      "corrective_action": "Suhu pendingin disesuaikan kembali, produk dipindahkan ke Cold Storage 2."
    }
    ```
*   **Response Sukses (200 OK):**
    ```json
    {
      "success": true,
      "message": "Temuan berhasil diselesaikan."
    }
    ```

---

## 9. Sinkronisasi Data & Ekspor Google Sheets (Admin Only)

### Ekspor Log Monitoring Suhu
*   **Endpoint:** `POST /api/admin/google-sheets/export/monitoring`
*   **Headers:** `Authorization: Bearer <token>`
*   **Payload Request (Opsional rentang tanggal):**
    ```json
    {
      "start_date": "2026-07-01",
      "end_date": "2026-07-12"
    }
    ```

### Ekspor Laporan QC
*   **Endpoint:** `POST /api/admin/google-sheets/export/qc`
*   **Headers:** `Authorization: Bearer <token>`

---

## 10. Format Response Error Konsisten

Setiap kesalahan validasi atau kegagalan transaksi akan mengembalikan format JSON berikut dengan kode status HTTP yang sesuai (400, 401, 403, 409, atau 500):
```json
{
  "success": false,
  "error": {
    "code": "DUPLICATE_SUBMISSION",
    "message": "Unit ini sudah diinput untuk slot 13:00."
  }
}
```
