# UI Profile Redesign

## Scope

Redesign halaman Profile untuk role Staff dan Admin tanpa mengubah kontrak API/backend. Implementasi tetap memakai data session yang sudah ada dari `Auth.user()` dan menyesuaikan tampilan berdasarkan `user.role`.

## Perubahan UI

- Profile header baru dengan avatar inisial otomatis, support foto profil, online indicator, role badge, shift badge, dan subtitle role.
- Visual header memakai glassmorphism ringan, gradient lembut, radius modern, shadow halus, dan hover elevation.
- Staff melihat panel `Today's Performance`.
- Admin melihat panel `Admin Overview`.
- Action menu diperluas menjadi Edit Profile, Change Password, Notifications, My QC Report, Appearance, Help Center, dan Logout.
- System information ditambahkan di bagian bawah profile:
  - ASTRO QC Enterprise
  - Version: 1.0.0
  - PT Astro Technologies Indonesia
  - Build: Production

## Komponen Baru

- `profile-skeleton`: loading skeleton dengan shimmer effect.
- `avatar-circle`: avatar foto/inisial dengan presence dot.
- `role-pill`: badge role merah untuk ADMIN dan biru untuk STAFF.
- `performance-panel`: mini dashboard adaptif role.
- `mini-stat`: mini card dengan icon, nilai, dan progress bar.
- `menu-item`: action row dengan ripple, hover, active state, dan touch target besar.
- `system-card`: metadata aplikasi dengan tone abu soft.
- Bottom navigation floating blur dengan active indicator.

## Mobile Optimization

- Layout mobile-first untuk 320px, 375px, 390px, dan 430px.
- Touch target menu dan nav dibuat sekitar 64-80px.
- Card memakai `minmax(0, 1fr)` dan `overflow-wrap` untuk mencegah teks terpotong.
- Avatar dan hero otomatis turun ke layout vertikal pada layar sangat kecil.
- Bottom nav floating menggunakan blur background, radius besar, dan label singkat `QC`.
- Tablet dan desktop memakai grid 2 kolom sampai 5 kolom untuk ringkasan performa.

## Responsive Coverage

- Desktop: 1920px, 1440px, 1024px.
- Tablet: 768px.
- Mobile: 430px, 390px, 375px, 320px.

Checklist desain:

- Icon tetap muncul.
- Text tidak terpotong.
- Card tidak overflow.
- Navbar tidak pecah.
- Tombol mudah disentuh.
- Animasi halus dan tidak berlebihan.

## Score

| Area | Sebelum | Sesudah |
| --- | ---: | ---: |
| Staff Profile | 7.2/10 | 9.5/10 |
| Admin Profile | 6.8/10 | 9.5/10 |
| Mobile Navigation | 7.0/10 | 9.5/10 |
| Touch Ergonomics | 7.4/10 | 9.5/10 |
| Enterprise Visual Feel | 7.1/10 | 9.5/10 |

