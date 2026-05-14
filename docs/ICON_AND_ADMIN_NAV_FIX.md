# Icon And Admin Navigation Fix

## Halaman Diperiksa

- `frontend/staff/dashboard.html`
- `frontend/staff/monitoring.html`
- `frontend/staff/inspection.html`
- `frontend/staff/profile.html`
- `frontend/staff/alerts.html`
- `frontend/admin/admin_panel.html`
- `frontend/styles/global.css`
- `frontend/styles/dashboard.css`
- `frontend/styles/profile.css`
- `frontend/css/admin_enterprise.css`
- `frontend/js/dashboard.js`
- `frontend/js/admin_app.js`

## Penyebab Icon Tidak Muncul

- Frontend memakai campuran Font Awesome, CSS mask, dan icon class yang tidak selalu tersedia.
- Beberapa icon dinamis dibuat setelah DOM load, tetapi tidak ada proses render ulang icon.
- Admin bergantung ke Font Awesome CDN saja, sehingga saat CDN lambat/blocked icon dapat terlihat kosong.
- Sebagian CSS menyembunyikan `<i>` untuk mengganti icon dengan mask, sehingga class yang tidak dipetakan bisa tampak blank.

## Perbaikan Icon

- Admin distandardisasi ke Lucide via CDN.
- `lucide.createIcons()` dipanggil saat init admin dan setelah render dinamis.
- Icon sidebar admin, topbar, metric card, tombol CRUD, evidence, dan modal diganti ke `data-lucide`.
- CSS global menambahkan ukuran konsisten untuk `.nav-icon`, `.menu-icon`, `.card-icon`, dan `[data-lucide]`.
- Halaman staff utama ditambahkan Lucide loader sebagai fallback modern.
- Dashboard staff tetap menjaga CSS mask lama untuk kompatibilitas, namun dynamic render sekarang memanggil refresh icon.

## Perbaikan Navigasi Admin

- Admin panel tetap single-page di `admin_panel.html`.
- Klik sidebar admin tidak reload dan tidak redirect.
- Section admin disembunyikan/ditampilkan melalui JS.
- Active state sidebar diperbarui jelas.
- `lucide.createIcons()` dijalankan setelah section berubah.
- Logout tetap satu-satunya aksi yang boleh redirect.

## Mobile Admin

- Sidebar admin berubah menjadi drawer pada layar kecil.
- Tombol hamburger membuka drawer.
- Overlay menutup drawer.
- Klik menu menutup drawer dan tetap di halaman admin yang sama.
- Body diberi `admin-drawer-open` agar tidak scroll di belakang drawer.

## Routing

- `/admin` dan `/admin/` sekarang melayani `admin_panel.html`.
- `/admin_panel.html` tetap dilayani oleh fallback HTML app.
- Link admin dari staff Monitor, Inspection, dan Profile diarahkan ke `dashboard.html#admin` supaya tidak masuk ke layer admin penuh secara tidak sengaja.
- Dashboard membuka panel admin inline saat hash `#admin` terdeteksi.

## File Diubah

- `backend/__init__.py`
- `frontend/admin/admin_panel.html`
- `frontend/css/admin_enterprise.css`
- `frontend/js/admin_app.js`
- `frontend/js/dashboard.js`
- `frontend/staff/dashboard.html`
- `frontend/staff/monitoring.html`
- `frontend/staff/inspection.html`
- `frontend/staff/profile.html`
- `frontend/staff/alerts.html`
- `frontend/styles/global.css`

## QA Desktop/Mobile

Target viewport:

- Desktop: 1440px, 1024px
- Mobile: 430px, 390px, 375px, 320px

Checklist:

- Semua icon admin memakai Lucide dan muncul setelah render.
- Admin menu tidak reload halaman.
- Admin section berubah smooth dengan `fadeIn`.
- Sidebar admin mobile menjadi drawer.
- Overlay drawer dan body no-scroll aktif.
- Staff bottom navigation tetap bekerja.
- Tidak ada horizontal overflow dari admin drawer.
- Route `/admin`, `/admin/`, `/admin_panel.html`, dan halaman staff tetap valid.

## Verifikasi

- `py -m pytest tests\test_api.py tests\test_dashboard.py`
- Hasil: 10 passed.

