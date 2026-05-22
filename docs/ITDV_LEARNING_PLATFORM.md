# ITDV Learning Platform

Modul ITDV ditambahkan sebagai platform pendidikan digital di atas sistem QC Central Kitchen tanpa mengubah workflow utama monitoring, QC check, approval, audit trail, dan dashboard.

## Struktur Folder

```text
backend/
  api/learning_routes.py
  repositories/learning_repository.py
  services/learning_service.py

frontend/
  learning/index.html
  learning/learning.css
  learning/learning.js

supabase/
  migrations/016_itdv_learning_platform.sql
```

## Flask Route

Blueprint baru:

```text
/api/learning
```

Frontend baru:

```text
/learning/
```

## API Endpoint

```text
GET  /api/learning/modules
POST /api/learning/modules/<module_slug>/complete
GET  /api/learning/progress
GET  /api/learning/simulations
POST /api/learning/simulations/<simulation_id>/submit
GET  /api/learning/quizzes
POST /api/learning/quizzes/<quiz_id>/submit
POST /api/learning/certificate
```

Semua endpoint menggunakan JWT yang sama dengan role admin/staff existing.

## Supabase Schema

Tabel baru memakai prefix `itdv_` agar terpisah dari tabel QC operasional:

```text
itdv_modules
itdv_progress
itdv_simulations
itdv_simulation_attempts
itdv_quizzes
itdv_quiz_attempts
itdv_certificates
```

Migration juga menambahkan seed awal untuk modul HACCP, Food Safety, QC Dasar, Traceability, Monitoring Suhu, simulasi PPIC Chiller, dan quiz QC Dasar.

## Clean Architecture

```text
HTTP layer       backend/api/learning_routes.py
Business logic   backend/services/learning_service.py
Persistence      backend/repositories/learning_repository.py
Database schema  supabase/migrations/016_itdv_learning_platform.sql
UI               frontend/learning/*
```

Jika Supabase belum memiliki tabel `itdv_*`, service tetap bisa menampilkan konten seed lokal dan menyimpan progress sementara di memori proses untuk mode development.
