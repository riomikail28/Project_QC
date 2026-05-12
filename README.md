# AstroQC

**Enterprise Quality Control & Traceability System untuk central kitchen, food production, dan operasional QC modern.**

AstroQC membantu tim operasional memantau kualitas produksi secara real time, mencatat bukti inspeksi, melacak batch dengan barcode, mengelola approval, dan menjaga audit trail dalam satu dashboard yang siap dipakai untuk produksi.

## Kenapa AstroQC?

Operasional QC sering tersebar di form manual, foto WhatsApp, spreadsheet, dan laporan yang terlambat. AstroQC menyatukan proses itu menjadi sistem digital yang rapi, cepat, dan mudah diaudit.

- Monitoring suhu freezer, chiller, dan ruangan
- Inspeksi batch dengan bukti foto
- Traceability berbasis barcode
- Dashboard analytics untuk admin QC
- Approval dan rejection flow
- Audit trail aktivitas staff
- Penyimpanan foto QC di Supabase Storage
- Deploy ringan di Vercel

## Fitur Utama

### Admin Dashboard

Admin mendapatkan tampilan enterprise untuk memantau:

- Total batch hari ini
- Batch gagal
- Suhu abnormal
- Pending approval
- Staff aktif
- QC reports
- Traceability batch
- Audit trail

### Realtime Monitoring

Pantau suhu kritikal dari area produksi:

- Freezer
- Chiller
- Ruang preparation
- Area produksi

Setiap data suhu dapat dikaitkan dengan staff, waktu pencatatan, status abnormal, dan foto pengecekan.

### QC Reports

Setiap inspeksi dapat menyimpan:

- Foto pengecekan suhu
- Foto label barcode
- Foto produk
- Hasil inspeksi
- Status approval atau rejection

### Traceability

Cari histori batch dari barcode untuk melihat:

- Produk
- Staff yang menangani
- Riwayat suhu
- Riwayat inspeksi
- Bukti foto
- Audit aktivitas

## Stack Produksi

AstroQC dirancang untuk stack cloud yang simpel dan efisien:

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Flask API
- **Database:** Supabase Postgres
- **Storage:** Supabase Storage
- **Deployment:** Vercel
- **CI/CD:** GitHub Actions

Tidak bergantung pada Kubernetes, Helm, Docker deployment, AWS S3, atau workflow lama yang rumit.

## Cocok Untuk

- Central kitchen
- Catering skala besar
- Food manufacturing
- Cloud kitchen
- QA/QC production team
- Operasional cold-chain
- Tim audit internal

## Quick Preview

Setelah deploy:

- Staff Login: `/login.html`
- Staff Dashboard: `/dashboard.html`
- Admin Dashboard: `/admin_panel.html`
- API Health: `/api/qc/health`

## Production Ready

Project ini sudah disiapkan untuk:

- Vercel deployment
- Supabase database migration
- Supabase storage buckets
- Role-based admin access
- JWT authentication
- GitHub Actions validation, test, dan deploy
- Struktur clean architecture


## Dibangun Untuk QC Yang Lebih Cepat, Rapi, dan Terukur

AstroQC membantu tim QC bergerak dari pencatatan manual menuju sistem digital yang lebih transparan, terdokumentasi, dan siap audit.

**PROJECT INI DI BUAT OLEH RIO..**

USERNAME admin  
PASSWORD admin123
