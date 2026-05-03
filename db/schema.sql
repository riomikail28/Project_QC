-- Supabase Schema for QC Traceability System
-- Execute this in Supabase SQL Editor or migrate via CLI

-- Enable RLS on all tables for security
-- Row Level Security must be enabled on tables for RLS to take effect.

-- 1. Staff Accounts
CREATE TABLE staff_accounts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'qc', 'staff', 'operator')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);
ALTER TABLE staff_accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Staff can view own account" ON staff_accounts FOR SELECT USING (auth.uid()::text = id::text);
CREATE POLICY "Admin can manage staff" ON staff_accounts FOR ALL USING (auth.role() = 'service_role');

-- 2. Products (SKU + SOP Thresholds)
CREATE TABLE products (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    product_code TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    ph_min DECIMAL,
    ph_max DECIMAL,
    brix_min DECIMAL,
    brix_max DECIMAL,
    tds_min DECIMAL,
    tds_max DECIMAL,
    core_temp_min_c DECIMAL DEFAULT 75.0,
    raw_temp_max_c DECIMAL DEFAULT 5.0,
    room_temp_max_c DECIMAL DEFAULT 20.0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read products" ON products FOR SELECT USING (is_active = true);

-- Demo products (run once)
INSERT INTO products (product_code, product_name, ph_min, ph_max, brix_min, brix_max) VALUES
('SKU-BEEF-001', 'Beef Teriyaki 90gr', 4.0, 6.0, 11.0, 14.0),
('SKU-CHKN-001', 'Chicken Teriyaki 90gr', 4.0, 6.0, 11.0, 14.0);

-- 3. Production Batches
CREATE TABLE production_batches (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    product_id UUID REFERENCES products(id),
    batch_code TEXT UNIQUE NOT NULL,
    production_date DATE NOT NULL,
    shift TEXT CHECK (shift IN ('Pagi', 'Siang', 'Malam')),
    status TEXT DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed')),
    final_qc_status TEXT CHECK (final_qc_status IN ('pass', 'fail')),
    operator_id UUID REFERENCES staff_accounts(id),
    qc_officer_id UUID REFERENCES staff_accounts(id),
    report_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE production_batches ENABLE ROW LEVEL SECURITY;

-- 4. Batch QC Logs (CCP stages)
CREATE TABLE production_batch_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES production_batches(id) ON DELETE CASCADE,
    stage TEXT NOT NULL CHECK (stage IN ('CCP1_PRE_COOK', 'CCP2_POST_COOK', 'CCP3_PACKAGING')),
    recorder_id UUID REFERENCES staff_accounts(id),
    
    -- CCP 1
    raw_temp_c DECIMAL,
    raw_temp_status TEXT,
    
    raw_material_photo_path TEXT,
    
    -- CCP 2
    core_temp_c DECIMAL,
    core_temp_status TEXT,
    
    ph_meter_photo_path TEXT,
    ph_value_extracted DECIMAL,
    ph_value_status TEXT,
    ocr_confidence_ph DECIMAL,
    
    refractometer_photo_path TEXT,
    brix_value_extracted DECIMAL,
    brix_value_status TEXT,
    ocr_confidence_brix DECIMAL,
    
    tds_value DECIMAL,
    tds_value_status TEXT,
    
    ocr_raw_output JSONB,  -- Full OCR output for audit
    
    -- CCP 3
    room_temp_c DECIMAL,
    room_temp_status TEXT,
    packaging_photo_path TEXT,
    
    stage_qc_status TEXT DEFAULT 'pending_review',
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE production_batch_logs ENABLE ROW LEVEL SECURITY;

-- 5. Facility Monitoring
CREATE TABLE facility_rooms (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE facility_devices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    room_id UUID REFERENCES facility_rooms(id),
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('chiller', 'freezer', 'ambient')),
    threshold_c DECIMAL NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE facility_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_id UUID REFERENCES facility_devices(id),
    zone TEXT NOT NULL,
    temperature_c DECIMAL NOT NULL,
    threshold_c DECIMAL NOT NULL,
    is_normal BOOLEAN,
    recorder_id UUID REFERENCES staff_accounts(id),
    notes TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE facility_alerts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    log_id UUID REFERENCES facility_logs(id),
    device_id UUID REFERENCES facility_devices(id),
    zone TEXT NOT NULL,
    temperature_c DECIMAL NOT NULL,
    threshold_c DECIMAL NOT NULL,
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on facility tables
ALTER TABLE facility_rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE facility_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE facility_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE facility_alerts ENABLE ROW LEVEL SECURITY;

-- Indexes for performance
CREATE INDEX idx_batch_production_date ON production_batches(production_date);
CREATE INDEX idx_logs_batch_id ON production_batch_logs(batch_id);
CREATE INDEX idx_logs_stage ON production_batch_logs(stage);
CREATE INDEX idx_facility_logs_zone ON facility_logs(zone);
CREATE INDEX idx_facility_logs_recorded ON facility_logs(recorded_at DESC);

-- Demo facility data
INSERT INTO facility_rooms (name) VALUES ('Dapur Utama'), ('Packing Area');
INSERT INTO facility_devices (room_id, name, type, threshold_c) VALUES
  ('00000000-0000-0000-0000-000000000001', 'Chiller A', 'chiller', 4.0),
  ('00000000-0000-0000-0000-000000000001', 'Freezer B', 'freezer', -18.0),
  ('00000000-0000-0000-0000-000000000002', 'Ambient Packing', 'ambient', 20.0);

-- Demo staff
INSERT INTO staff_accounts (username, password_hash, role) VALUES
  ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin'),  -- admin123
  ('staff', '81dc9bdb52d04dc20036dbd8313ed055', 'staff');  -- 1234

-- Public API Policies (for frontend read-only access)
CREATE POLICY "Public read products" ON products FOR SELECT USING (is_active = true);
CREATE POLICY "Public read batches" ON production_batches FOR SELECT USING (true);
CREATE POLICY "Public read batch logs" ON production_batch_logs FOR SELECT USING (true);
CREATE POLICY "Public read facility rooms" ON facility_rooms FOR SELECT USING (true);
CREATE POLICY "Public read facility devices" ON facility_devices FOR SELECT USING (is_active = true);
CREATE POLICY "Public read facility logs" ON facility_logs FOR SELECT USING (true);
CREATE POLICY "Public read staff" ON staff_accounts FOR SELECT USING (is_active = true);
