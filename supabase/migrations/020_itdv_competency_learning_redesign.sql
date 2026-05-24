-- ITDV QC LearnHub competency content refresh.
-- Uses internal training language only; no official certification claim.

alter table if exists public.itdv_modules
  add column if not exists learning_material text,
  add column if not exists case_study text,
  add column if not exists competencies jsonb not null default '[]'::jsonb;

insert into public.itdv_modules (
  slug, title, category, summary, objectives, duration_minutes, sort_order,
  learning_material, case_study, competencies
)
values
('food-safety-hygiene','Dasar Food Safety dan Hygiene','Food Safety','Fondasi keamanan pangan, hygiene area, dan pencegahan kontaminasi pada central kitchen.','["Memahami risiko food safety","Mengenali sumber kontaminasi","Menjaga hygiene area kerja"]'::jsonb,25,10,'Food safety berfokus pada pengendalian bahaya yang dapat membuat produk tidak aman dikonsumsi. Staff QC perlu membaca kondisi area, hygiene pekerja, alur bahan, suhu, dan kebersihan alat sebelum produk dilepas.','Area preparation menerima bahan dingin dengan kemasan basah. Staff QC menilai kebersihan kemasan, suhu penerimaan, dan risiko kontaminasi silang sebelum bahan masuk proses.','["Menilai risiko keamanan pangan dasar","Mencatat temuan hygiene","Menentukan tindakan pencegahan awal"]'::jsonb),
('gmp-personal-hygiene','GMP dan Personal Hygiene','GMP','Praktik GMP, kebersihan personel, sanitasi alat, dan disiplin area produksi.','["Memahami GMP","Mengecek personal hygiene","Mencegah kontaminasi silang"]'::jsonb,25,20,'GMP mengatur praktik produksi yang konsisten dan higienis. Pemeriksaan meliputi APD, cuci tangan, kondisi alat, pemisahan area bersih/kotor, dan perilaku pekerja di area produksi.','Operator masuk area packing tanpa hairnet lengkap. QC perlu melakukan hold sementara pada proses, koreksi APD, dan mencatat temuan hygiene.','["Melakukan checklist GMP","Mengidentifikasi pelanggaran hygiene","Memberi rekomendasi perbaikan area"]'::jsonb),
('haccp-principles','Prinsip HACCP','HACCP','Prinsip HACCP mulai dari analisis bahaya, CCP, critical limit, monitoring, corrective action, verification, dan dokumentasi.','["Memahami alur HACCP","Menghubungkan bahaya dengan CCP","Membaca dokumen monitoring"]'::jsonb,35,30,'HACCP adalah pendekatan sistematis untuk mengidentifikasi, mengevaluasi, dan mengendalikan bahaya signifikan dalam proses pangan. Di central kitchen, HACCP membantu QC membuat keputusan berbasis risiko.','Suhu chiller naik ke 11°C saat produk menunggu rilis. QC menentukan apakah titik tersebut termasuk kontrol kritis dan bagaimana produk ditahan.','["Menjelaskan prinsip HACCP","Membaca alur proses","Menghubungkan deviasi dengan risiko produk"]'::jsonb),
('hazard-identification','Identifikasi Bahaya Pangan','HACCP','Identifikasi bahaya biologis, kimia, fisik, dan alergen pada proses central kitchen.','["Mengenali bahaya biologis","Mengenali bahaya kimia/fisik","Mengenali risiko alergen"]'::jsonb,35,40,'Bahaya biologis mencakup mikroba, kimia mencakup residu bahan pembersih, fisik mencakup serpihan benda asing, dan alergen mencakup kontaminasi silang bahan pemicu alergi.','Produk seafood diproses dekat menu non-seafood. QC menilai risiko alergen, alat yang dipakai, dan label pemisahan bahan.','["Mengklasifikasi bahaya pangan","Menentukan sumber risiko","Menulis temuan bahaya dalam checklist"]'::jsonb),
('ccp-determination','Penentuan CCP','HACCP','Cara menentukan titik kendali kritis berdasarkan risiko dan kemampuan proses mengendalikan bahaya.','["Memahami konsep CCP","Membedakan CP dan CCP","Menentukan titik kendali proses"]'::jsonb,30,50,'CCP adalah titik proses yang wajib dikendalikan untuk mencegah, menghilangkan, atau menurunkan bahaya signifikan ke tingkat aman. Tidak semua kontrol mutu adalah CCP.','Proses chilling setelah cooking perlu dikaji apakah menjadi CCP karena memengaruhi pertumbuhan mikroba pada produk matang.','["Menganalisis titik kendali","Membedakan CP dan CCP","Memberi alasan penentuan CCP"]'::jsonb),
('critical-limit','Critical Limit','HACCP','Batas kritis untuk suhu, waktu, visual, dan parameter proses yang harus dipenuhi.','["Membaca batas kritis","Menilai deviasi","Mengambil keputusan hold"]'::jsonb,25,60,'Critical limit adalah batas terukur yang memisahkan kondisi aman dan tidak aman. Contohnya target suhu chiller 5°C, suhu cooking minimum, atau waktu pendinginan tertentu.','Chiller target 5°C tercatat 11°C. QC menilai bahwa limit terlewati dan produk perlu ditahan sampai evaluasi selesai.','["Membaca parameter kritis","Menentukan status deviasi","Mencatat limit yang dilanggar"]'::jsonb),
('ccp-monitoring','Monitoring CCP','Monitoring','Teknik monitoring CCP, frekuensi cek, evidence, dan pencatatan hasil monitoring.','["Menjalankan monitoring","Mencatat evidence","Mengeskalasi hasil abnormal"]'::jsonb,30,70,'Monitoring CCP memastikan batas kritis dipantau secara konsisten. Catatan harus berisi waktu, area, parameter, hasil, petugas, dan tindakan bila terjadi deviasi.','Staff mencatat suhu PPIC Chiller pada slot 07:00, 13:00, 16:00, dan 19:00 untuk memastikan cold chain terkendali.','["Melakukan pencatatan monitoring","Membaca tren suhu","Membuat evidence monitoring"]'::jsonb),
('corrective-action','Corrective Action','CAPA','Tindakan korektif saat critical limit terlewati, termasuk hold product, investigasi, dan eskalasi.','["Menahan produk terdampak","Investigasi penyebab","Menentukan tindakan perbaikan"]'::jsonb,30,80,'Corrective action harus mengendalikan produk terdampak dan memperbaiki penyebab deviasi. Tindakan dicatat agar keputusan rilis/reject dapat diaudit.','Saat suhu chiller 11°C, QC menahan produk, memindahkan ke chiller aman, memeriksa pintu/sensor, dan meminta maintenance mengecek unit.','["Menentukan hold product","Menyusun tindakan korektif","Mencatat eskalasi dan hasil verifikasi"]'::jsonb),
('verification-documentation','Verification dan Documentation','Documentation','Verifikasi hasil monitoring, review dokumen, audit trail, dan kelengkapan evidence.','["Memverifikasi catatan QC","Mengecek kelengkapan evidence","Membaca audit trail"]'::jsonb,30,90,'Verification memastikan sistem kontrol berjalan efektif. Dokumentasi menjadi bukti bahwa monitoring, deviasi, dan corrective action dilakukan secara konsisten.','Supervisor mereview log suhu, foto evidence, jam input, dan catatan corrective action sebelum menutup deviasi.','["Melakukan review dokumen","Menilai kelengkapan evidence","Menyiapkan data untuk audit internal"]'::jsonb),
('traceability-recall','Traceability dan Recall','Traceability','Pelacakan batch, bahan baku, proses, distribusi, dan simulasi recall produk.','["Melacak batch","Menghubungkan bahan dan produk","Menyiapkan data recall"]'::jsonb,35,100,'Traceability memungkinkan tim menelusuri produk dari bahan baku sampai distribusi. Saat ada deviasi, data batch membantu menentukan produk terdampak.','Komplain muncul dari batch tertentu. QC menelusuri supplier, waktu produksi, suhu penyimpanan, dan area distribusi.','["Membaca alur batch","Menentukan produk terdampak","Menyusun data recall internal"]'::jsonb),
('chiller-freezer-monitoring','Monitoring Suhu Chiller/Freezer','Cold Chain','Monitoring suhu chiller/freezer, deviasi cold chain, dan pengendalian produk dingin.','["Membaca suhu chiller/freezer","Menilai deviasi cold chain","Mengambil tindakan cepat"]'::jsonb,25,110,'Cold chain menjaga produk tetap pada suhu aman. Deviasi harus dilihat dari suhu aktual, durasi, produk terdampak, dan kondisi unit penyimpanan.','Freezer menunjukkan -9°C dari target -18°C. QC mengecek durasi, kondisi produk, pintu, dan eskalasi maintenance.','["Menginterpretasi suhu cold chain","Menentukan prioritas eskalasi","Mencatat log suhu harian"]'::jsonb),
('central-kitchen-case','Studi Kasus Central Kitchen','Case Study','Simulasi keputusan QC dari penerimaan bahan, proses, penyimpanan, sampai rilis produk.','["Menganalisis kasus nyata","Menggabungkan HACCP dan GMP","Membuat keputusan QC"]'::jsonb,40,120,'Studi kasus menggabungkan food safety, GMP, HACCP, monitoring suhu, corrective action, dokumentasi, dan traceability dalam satu alur kerja QC.','Produk ready meal melewati cooking, chilling, packing, dan penyimpanan. Peserta menentukan titik risiko dan tindakan QC di setiap tahap.','["Membuat analisis kasus QC","Menyusun keputusan berbasis risiko","Menentukan evidence yang wajib dicatat"]'::jsonb)
on conflict (slug) do update set
  title = excluded.title,
  category = excluded.category,
  summary = excluded.summary,
  objectives = excluded.objectives,
  duration_minutes = excluded.duration_minutes,
  sort_order = excluded.sort_order,
  learning_material = excluded.learning_material,
  case_study = excluded.case_study,
  competencies = excluded.competencies;

insert into public.itdv_simulations (id, title, area, target_c, actual_c, scenario, options, best_actions)
values (
  'ppic-chiller-001',
  'PPIC Chiller 11°C',
  'PPIC Chiller',
  5,
  11,
  'Saat monitoring pagi, PPIC Chiller tercatat 11°C dari target 5°C. Produk ready meal masih menunggu rilis produksi.',
  '[
    {"key":"A","label":"Investigasi dan tahan produk","score":85,"feedback":"Tepat: tahan produk terdampak, cek durasi deviasi, sensor, pintu, dan kondisi produk."},
    {"key":"B","label":"Corrective action","score":100,"feedback":"Paling tepat jika disertai hold product, pindah chiller cadangan, eskalasi maintenance, dan dokumentasi deviasi."},
    {"key":"C","label":"Lanjut produksi","score":0,"feedback":"Tidak aman. Deviasi suhu harus dikendalikan sebelum produksi dilanjutkan."}
  ]'::jsonb,
  '["A","B"]'::jsonb
)
on conflict (id) do update set
  title = excluded.title,
  area = excluded.area,
  target_c = excluded.target_c,
  actual_c = excluded.actual_c,
  scenario = excluded.scenario,
  options = excluded.options,
  best_actions = excluded.best_actions;

insert into public.itdv_quizzes (id, title, module_slug, questions)
values (
  'qc-basic-quiz',
  'Quiz HACCP dan Food Safety Central Kitchen',
  'haccp-principles',
  '[
    {"id":"q1","text":"Saat suhu PPIC Chiller 11°C dari target 5°C, keputusan QC paling aman adalah...","options":[{"key":"A","label":"Catat saja di akhir shift"},{"key":"B","label":"Investigasi dan tahan produk terdampak"},{"key":"C","label":"Naikkan target suhu"},{"key":"D","label":"Lanjut produksi jika produk terlihat normal"}],"answer":"B"},
    {"id":"q2","text":"Bahaya pangan biologis dalam central kitchen terutama berkaitan dengan...","options":[{"key":"A","label":"Pertumbuhan mikroba pada bahan atau produk"},{"key":"B","label":"Serpihan plastik dari kemasan"},{"key":"C","label":"Residu bahan pembersih"},{"key":"D","label":"Label harga yang tidak sesuai"}],"answer":"A"},
    {"id":"q3","text":"Dalam HACCP, CCP berarti titik proses yang harus dikendalikan karena...","options":[{"key":"A","label":"Selalu paling mahal"},{"key":"B","label":"Berhubungan dengan bahaya keamanan pangan signifikan"},{"key":"C","label":"Hanya untuk dokumen admin"},{"key":"D","label":"Tidak perlu monitoring"}],"answer":"B"},
    {"id":"q4","text":"Dokumentasi corrective action saat deviasi suhu minimal harus memuat...","options":[{"key":"A","label":"Jam, area, suhu aktual, produk terdampak, tindakan, PIC, dan verifikasi"},{"key":"B","label":"Nama menu favorit staff"},{"key":"C","label":"Hanya foto tanpa catatan"},{"key":"D","label":"Nomor invoice pembelian"}],"answer":"A"},
    {"id":"q5","text":"Traceability batch berguna terutama untuk apa?","options":[{"key":"A","label":"Menentukan jalur recall dan audit produk"},{"key":"B","label":"Menghapus kebutuhan QC"},{"key":"C","label":"Mengubah resep produksi"},{"key":"D","label":"Mengganti approval supervisor"}],"answer":"A"}
  ]'::jsonb
)
on conflict (id) do update set
  title = excluded.title,
  module_slug = excluded.module_slug,
  questions = excluded.questions;
