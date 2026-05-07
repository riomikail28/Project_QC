-- QC Central Kitchen - Safe initial seeds
-- Default passwords are temporary and must be rotated after first deploy.
-- admin: ChangeMeAdmin123!
-- staff: ChangeMeStaff123!

INSERT INTO staff_accounts (username, password_hash, role, full_name)
VALUES
('admin', 'pbkdf2:sha256:1000000$OplosIZA37VI9taF$17d52eeb445433a1511e2e90899caa235286a7cf69a189d36380a4ce4cda62ef', 'admin', 'Administrator Utama'),
('staff', 'pbkdf2:sha256:1000000$bH8lxnBrDgP02Dqd$499caae1cde8c753cfe47b0f3d3e77ff3105aed4ab0a975aec539506a8abed74', 'staff', 'Operator Kitchen')
ON CONFLICT (username) DO NOTHING;

INSERT INTO products (product_code, sku_code, product_name, category, brix_min, brix_max, ph_min, ph_max, tds_min, tds_max)
VALUES
('BRD-001', 'BRD-001', 'Signature Brioche', 'Bakery', NULL, NULL, 5.5, 6.5, NULL, NULL),
('SCE-012', 'SCE-012', 'Classic Tomato Sauce', 'Sauce', 12.0, 14.5, 3.8, 4.2, 1200, 1500),
('MT-442', 'MT-442', 'Marinated Wagyu Beef', 'Meat', NULL, NULL, 5.8, 6.2, NULL, NULL),
('DRK-99', 'DRK-99', 'Cold Brew Coffee', 'Beverage', 4.5, 5.5, 4.8, 5.2, 800, 1100)
ON CONFLICT (product_code) DO NOTHING;
