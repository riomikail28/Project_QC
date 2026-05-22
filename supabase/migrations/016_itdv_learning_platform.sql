create table if not exists public.itdv_modules (
    slug text primary key,
    title text not null,
    category text not null,
    summary text not null,
    objectives jsonb not null default '[]'::jsonb,
    duration_minutes integer not null default 0,
    sort_order integer not null default 0,
    created_at timestamptz not null default now()
);

create table if not exists public.itdv_learning_progress (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    module_slug text not null references public.itdv_modules(slug) on delete cascade,
    status text not null default 'in_progress' check (status in ('in_progress', 'completed')),
    completed_at timestamptz,
    updated_at timestamptz not null default now(),
    unique (user_id, module_slug)
);

create table if not exists public.itdv_simulations (
    id text primary key,
    title text not null,
    area text not null,
    target_c numeric,
    actual_c numeric,
    scenario text not null,
    options jsonb not null default '[]'::jsonb,
    best_actions jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.itdv_simulation_attempts (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    simulation_id text not null references public.itdv_simulations(id) on delete cascade,
    selected_action text not null,
    score integer not null check (score >= 0 and score <= 100),
    feedback text,
    created_at timestamptz not null default now()
);

create table if not exists public.itdv_quizzes (
    id text primary key,
    title text not null,
    module_slug text references public.itdv_modules(slug) on delete set null,
    questions jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.itdv_quiz_attempts (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    quiz_id text not null references public.itdv_quizzes(id) on delete cascade,
    score integer not null check (score >= 0 and score <= 100),
    answers jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.itdv_certificates (
    id uuid primary key default gen_random_uuid(),
    certificate_id text not null unique,
    user_id text not null,
    program_code text not null,
    participant_name text not null,
    issued_at timestamptz not null default now(),
    unique (user_id, program_code)
);

create index if not exists idx_itdv_progress_user on public.itdv_learning_progress(user_id);
create index if not exists idx_itdv_sim_attempts_user on public.itdv_simulation_attempts(user_id, created_at desc);
create index if not exists idx_itdv_quiz_attempts_user on public.itdv_quiz_attempts(user_id, created_at desc);

insert into public.itdv_modules (slug, title, category, summary, objectives, duration_minutes, sort_order)
values
('haccp', 'HACCP', 'Food Safety', 'Identifikasi bahaya, CCP, critical limit, monitoring, corrective action, dan verifikasi.', '["Mengenali bahaya pangan","Menentukan CCP","Membuat tindakan korektif"]'::jsonb, 45, 10),
('food-safety', 'Food Safety', 'Sanitasi', 'Prinsip keamanan pangan, personal hygiene, kontaminasi silang, dan alur sanitasi area produksi.', '["Mencegah kontaminasi","Memahami hygiene","Menilai risiko area"]'::jsonb, 35, 20),
('qc-dasar', 'QC Dasar', 'Quality Control', 'Parameter mutu dasar, sampling, inspeksi visual, evidence, dan keputusan pass/warning/fail.', '["Membaca parameter QC","Melakukan sampling","Mencatat evidence"]'::jsonb, 30, 30),
('traceability', 'Traceability', 'Batch', 'Pelacakan batch dari bahan baku, proses, penyimpanan, distribusi, sampai audit trail.', '["Melacak batch","Menganalisis audit trail","Menyiapkan recall simulation"]'::jsonb, 40, 40),
('monitoring-suhu', 'Monitoring Suhu', 'Cold Chain', 'Pemantauan suhu chiller/freezer, batas kritis, alert, investigasi, dan eskalasi.', '["Membaca deviasi suhu","Memilih aksi korektif","Menyimpan log monitoring"]'::jsonb, 25, 50)
on conflict (slug) do update set
    title = excluded.title,
    category = excluded.category,
    summary = excluded.summary,
    objectives = excluded.objectives,
    duration_minutes = excluded.duration_minutes,
    sort_order = excluded.sort_order;

insert into public.itdv_simulations (id, title, area, target_c, actual_c, scenario, options, best_actions)
values (
    'ppic-chiller-001',
    'PPIC Chiller Temperature Deviation',
    'PPIC Chiller',
    5,
    11,
    'Saat monitoring pagi, suhu aktual PPIC Chiller berada di atas target. Produk masih menunggu rilis produksi.',
    '[
        {"key":"A","label":"Investigasi","score":70,"feedback":"Benar sebagai langkah awal: cek durasi deviasi, sensor, pintu, dan kondisi produk."},
        {"key":"B","label":"Corrective Action","score":100,"feedback":"Paling tepat jika disertai hold product, pindah chiller cadangan, dan eskalasi maintenance."},
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
    'Quiz QC Dasar',
    'qc-dasar',
    '[
        {"id":"q1","text":"Apa tindakan pertama saat suhu chiller melewati critical limit?","options":[{"key":"A","label":"Catat saja di akhir shift"},{"key":"B","label":"Investigasi dan tahan produk terdampak"},{"key":"C","label":"Naikkan target suhu"},{"key":"D","label":"Lanjut produksi jika produk terlihat normal"}],"answer":"B"},
        {"id":"q2","text":"Traceability batch berguna terutama untuk apa?","options":[{"key":"A","label":"Menentukan jalur recall dan audit produk"},{"key":"B","label":"Menghapus kebutuhan QC"},{"key":"C","label":"Mengubah resep produksi"},{"key":"D","label":"Mengganti approval supervisor"}],"answer":"A"},
        {"id":"q3","text":"Dalam HACCP, CCP berarti titik proses yang harus dikendalikan karena...","options":[{"key":"A","label":"Selalu paling mahal"},{"key":"B","label":"Berhubungan dengan bahaya keamanan pangan signifikan"},{"key":"C","label":"Hanya untuk dokumen admin"},{"key":"D","label":"Tidak perlu monitoring"}],"answer":"B"}
    ]'::jsonb
)
on conflict (id) do update set
    title = excluded.title,
    module_slug = excluded.module_slug,
    questions = excluded.questions;
