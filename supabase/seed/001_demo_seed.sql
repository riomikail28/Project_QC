-- Demo data for QC Enterprise presentations.
-- Safe to rerun. Passwords are stored as SHA-256 hashes because the backend
-- supports legacy SHA-256 verification while new app-created users use PBKDF2.

create extension if not exists pgcrypto;

insert into public.staff_accounts (id, username, password_hash, full_name, role, is_active)
values
  (
    '00000000-0000-4000-8000-000000000101',
    'demo.admin@qcenterprise.id',
    encode(digest('demo123456', 'sha256'), 'hex'),
    'Demo Admin QC',
    'admin',
    true
  ),
  (
    '00000000-0000-4000-8000-000000000102',
    'demo.staff@qcenterprise.id',
    encode(digest('demo123456', 'sha256'), 'hex'),
    'Demo Staff QC',
    'staff',
    true
  )
on conflict (username) do update set
  password_hash = excluded.password_hash,
  full_name = excluded.full_name,
  role = excluded.role,
  is_active = true,
  updated_at = now();

insert into public.users (staff_account_id, email, full_name, role)
values
  (
    '00000000-0000-4000-8000-000000000101',
    'demo.admin@qcenterprise.id',
    'Demo Admin QC',
    'admin'
  ),
  (
    '00000000-0000-4000-8000-000000000102',
    'demo.staff@qcenterprise.id',
    'Demo Staff QC',
    'qc_staff'
  )
on conflict (staff_account_id) do update set
  email = excluded.email,
  full_name = excluded.full_name,
  role = excluded.role,
  updated_at = now();

insert into public.products (
  id, product_code, sku_code, product_name, ph_min, ph_max, brix_min, brix_max, tds_min, tds_max, is_active
)
values
  (
    '10000000-0000-4000-8000-000000000001',
    'DEMO-RM-001',
    'SKU-DEMO-RM-001',
    'Ready Meal Demo',
    4.50,
    7.00,
    10.00,
    14.00,
    90.00,
    160.00,
    true
  ),
  (
    '10000000-0000-4000-8000-000000000002',
    'DEMO-SOUP-001',
    'SKU-DEMO-SOUP-001',
    'Soup Base Demo',
    4.80,
    6.80,
    8.00,
    12.00,
    100.00,
    180.00,
    true
  )
on conflict (product_code) do update set
  sku_code = excluded.sku_code,
  product_name = excluded.product_name,
  ph_min = excluded.ph_min,
  ph_max = excluded.ph_max,
  brix_min = excluded.brix_min,
  brix_max = excluded.brix_max,
  tds_min = excluded.tds_min,
  tds_max = excluded.tds_max,
  is_active = true,
  updated_at = now();

insert into public.production_batches (
  batch_code, product_id, product_name, production_date, expired_date, status, created_by, storage_path
)
values
  (
    'QC-DEMO-001',
    '10000000-0000-4000-8000-000000000001',
    'Ready Meal Demo',
    current_date,
    current_date + interval '3 day',
    'completed',
    '00000000-0000-4000-8000-000000000102',
    'Chiller A'
  ),
  (
    'QC-DEMO-002',
    '10000000-0000-4000-8000-000000000002',
    'Soup Base Demo',
    current_date,
    current_date + interval '2 day',
    'hold',
    '00000000-0000-4000-8000-000000000102',
    'PPIC Chiller'
  )
on conflict (batch_code) do update set
  product_id = excluded.product_id,
  product_name = excluded.product_name,
  production_date = excluded.production_date,
  expired_date = excluded.expired_date,
  status = excluded.status,
  created_by = excluded.created_by,
  storage_path = excluded.storage_path,
  updated_at = now();

insert into public.temperature_logs (
  device_type, zone, temperature_c, threshold_c, is_abnormal, staff_id,
  monitoring_date, slot_time, schedule_status, submitted_at, is_late, recorded_at
)
values
  ('chiller', 'Chiller A', 4.2, 5.0, false, '00000000-0000-4000-8000-000000000102', current_date, '07:00', 'completed', now() - interval '6 hour', false, now() - interval '6 hour'),
  ('freezer', 'Freezer 1', -18.5, -18.0, false, '00000000-0000-4000-8000-000000000102', current_date, '13:00', 'completed', now() - interval '2 hour', false, now() - interval '2 hour'),
  ('chiller', 'PPIC Chiller', 11.0, 5.0, true, '00000000-0000-4000-8000-000000000102', current_date, '16:00', 'late', now() - interval '30 minute', true, now() - interval '30 minute'),
  ('room', 'Preparation Room', 27.8, 25.0, true, '00000000-0000-4000-8000-000000000102', current_date, '19:00', null, null, false, now())
on conflict do nothing;

insert into public.qc_reports (
  batch_code, product_id, product_name, staff_id, inspector_name, status, approval_status, inspection_result
)
values
  (
    'QC-DEMO-001',
    '10000000-0000-4000-8000-000000000001',
    'Ready Meal Demo',
    '00000000-0000-4000-8000-000000000102',
    'Demo Staff QC',
    'pass',
    'approved',
    '{"temperature":"pass","label":"pass","product":"pass","decision":"PASS"}'::jsonb
  ),
  (
    'QC-DEMO-002',
    '10000000-0000-4000-8000-000000000002',
    'Soup Base Demo',
    '00000000-0000-4000-8000-000000000102',
    'Demo Staff QC',
    'warning',
    'pending',
    '{"temperature":"warning","label":"pass","product":"hold","decision":"HOLD"}'::jsonb
  ),
  (
    'QC-DEMO-003',
    '10000000-0000-4000-8000-000000000001',
    'Ready Meal Demo',
    '00000000-0000-4000-8000-000000000102',
    'Demo Staff QC',
    'failed',
    'pending',
    '{"temperature":"failed","label":"warning","product":"failed","decision":"FAIL"}'::jsonb
  )
on conflict do nothing;

insert into public.barcode_labels (
  batch_code, product_name, barcode_value, staff_name
)
values
  ('QC-DEMO-001', 'Ready Meal Demo', '899700000001', 'Demo Staff QC'),
  ('QC-DEMO-002', 'Soup Base Demo', '899700000002', 'Demo Staff QC')
on conflict do nothing;

insert into public.itdv_progress (user_id, module_slug, status, completed_at)
values
  ('00000000-0000-4000-8000-000000000102', 'food-safety-hygiene', 'completed', now() - interval '2 day'),
  ('00000000-0000-4000-8000-000000000102', 'gmp-personal-hygiene', 'completed', now() - interval '1 day')
on conflict (user_id, module_slug) do update set
  status = excluded.status,
  completed_at = excluded.completed_at,
  updated_at = now();

insert into public.itdv_module_quiz_attempts (user_id, module_slug, score, passed, answers)
values
  ('00000000-0000-4000-8000-000000000102', 'food-safety-hygiene', 100, true, '{"food-safety-hygiene-q1":"A","food-safety-hygiene-q2":"B","food-safety-hygiene-q3":"A"}'::jsonb),
  ('00000000-0000-4000-8000-000000000102', 'gmp-personal-hygiene', 100, true, '{"gmp-personal-hygiene-q1":"A","gmp-personal-hygiene-q2":"B","gmp-personal-hygiene-q3":"A"}'::jsonb)
on conflict do nothing;
