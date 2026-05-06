-- QC Central Kitchen - Initial Seeds
-- Version: 2.0

-- 1. Initial Staff (Password: admin123)
INSERT INTO staff_accounts (username, password_hash, role, full_name)
VALUES 
('admin', 'admin123', 'admin', 'Administrator Utama'),
('staff_kitchen', 'staff123', 'staff', 'Operator Kitchen 01'),
('qc_lead', 'qc123', 'qc_lead', 'Kepala Quality Control');

-- 2. Product Catalog (SOP Thresholds)
INSERT INTO products (sku_code, product_name, category, brix_min, brix_max, ph_min, ph_max, tds_min, tds_max)
VALUES 
('BRD-001', 'Signature Brioche', 'Bakery', NULL, NULL, 5.5, 6.5, NULL, NULL),
('SCE-012', 'Classic Tomato Sauce', 'Sauce', 12.0, 14.5, 3.8, 4.2, 1200, 1500),
('MT-442', 'Marinated Wagyu Beef', 'Meat', NULL, NULL, 5.8, 6.2, NULL, NULL),
('DRK-99', 'Cold Brew Coffee', 'Beverage', 4.5, 5.5, 4.8, 5.2, 800, 1100);

-- 3. Initial Facility Setup (Zones)
-- These are usually handled by the backend logic, but can be seeded for testing
INSERT INTO facility_logs (zone, temperature_c, status)
VALUES 
('Chiller Kitchen', 3.2, 'PASS'),
('Freezer Central', -19.5, 'PASS'),
('Ambient Storage', 22.1, 'PASS');
