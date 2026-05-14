# Admin Route Separation Fix

## Masalah

Dashboard staff pernah memakai hash routing `#admin` dan menampilkan panel admin inline di `dashboard.html`. Akibatnya URL:

`/dashboard.html#admin`

masih terasa seperti dashboard staff/admin gabungan, bukan Admin Panel khusus.

## Perbaikan

- Semua link `dashboard.html#admin` diganti menjadi `/admin/`.
- Menu Admin di staff dashboard sekarang berupa link biasa ke `/admin/`.
- Section admin inline di `frontend/staff/dashboard.html` dihapus.
- Fungsi JS `toggleInlineAdmin` dan `showAdminQuickInfo` dihapus.
- `dashboard.html#admin` sekarang otomatis redirect ke `/admin/`.
- CSS inline admin dashboard dibersihkan dari `frontend/styles/dashboard.css`.
- Flask route admin dipastikan melayani:
  - `/admin`
  - `/admin/`
  - `/admin/admin_panel.html`

## File Diubah

- `frontend/staff/dashboard.html`
- `frontend/staff/monitoring.html`
- `frontend/staff/inspection.html`
- `frontend/staff/profile.html`
- `frontend/styles/dashboard.css`
- `backend/__init__.py`

## Route Final

- `/dashboard.html` = staff dashboard
- `/dashboard.html#admin` = redirect ke `/admin/`
- `/admin/` = admin panel
- `/admin` = admin panel
- `/admin/admin_panel.html` = admin panel

## QA Result

- Staff dashboard hanya berisi home, monitor, inspection/check, profile, alerts.
- Admin panel berdiri sendiri dengan sidebar dan topbar admin.
- `dashboard.js` tidak render admin section.
- `admin_app.js` hanya dipakai oleh `admin_panel.html`.
- Vercel tetap mengarahkan semua route ke Flask app, lalu Flask memilih file frontend yang benar.

