insert into public.qc_reports (
  batch_code, product_name, inspector_name, status, approval_status, inspection_result
) values
  ('QC-DEMO-001', 'Ready Meal Demo', 'Admin QC', 'pass', 'approved', '{"temperature":"pass","label":"pass","product":"pass"}'),
  ('QC-DEMO-002', 'Cold Storage Demo', 'Admin QC', 'warning', 'pending', '{"temperature":"warning","label":"pass","product":"pending"}')
on conflict do nothing;

insert into public.temperature_logs (
  device_type, zone, temperature_c, threshold_c, is_abnormal
) values
  ('freezer', 'Freezer 1', -18.5, -18.0, false),
  ('chiller', 'Chiller 1', 4.2, 5.0, false),
  ('room', 'Preparation Room', 28.1, 25.0, true)
on conflict do nothing;

insert into public.barcode_labels (
  batch_code, product_name, barcode_value, staff_name
) values
  ('QC-DEMO-001', 'Ready Meal Demo', '899700000001', 'Admin QC')
on conflict do nothing;
