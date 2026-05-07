-- ========================================================
-- QC TRACEABILITY SYSTEM - UPDATED SCHEMA V3
-- ========================================================

-- 1. ENUMS & EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
DO $$ BEGIN
    CREATE TYPE device_type AS ENUM ('chiller', 'freezer', 'undercounter', 'room_temp');
    CREATE TYPE staff_role AS ENUM ('admin', 'staff');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 1b. STAFF & AUTH
CREATE TABLE IF NOT EXISTS staff_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role staff_role DEFAULT 'staff',
    full_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1c. PRODUCT CATALOG
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_code TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    category TEXT,
    brix_min NUMERIC,
    brix_max NUMERIC,
    ph_min NUMERIC,
    ph_max NUMERIC,
    tds_min NUMERIC,
    tds_max NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. FACILITY STRUCTURE
CREATE TABLE IF NOT EXISTS facility_rooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL, -- e.g., 'PPIC', 'Kitchen'
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facility_devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    room_id UUID REFERENCES facility_rooms(id) ON DELETE CASCADE,
    name TEXT NOT NULL, -- e.g., 'Chiller A', 'Freezer 1'
    type device_type NOT NULL,
    threshold_temp NUMERIC NOT NULL, -- SOP Threshold
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. UPDATED LOGS (Including Humidity & Photos)
CREATE TABLE IF NOT EXISTS facility_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES facility_devices(id),
    room_id UUID REFERENCES facility_rooms(id),
    staff_id UUID REFERENCES staff_accounts(id),
    temperature_c NUMERIC NOT NULL,
    humidity_rh NUMERIC, -- Only for room_temp
    is_normal BOOLEAN DEFAULT TRUE,
    reason TEXT, -- Optional reason if abnormal
    photo_url TEXT, -- Staff findings photo
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facility_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_id UUID REFERENCES facility_logs(id) ON DELETE SET NULL,
    device_id UUID REFERENCES facility_devices(id) ON DELETE SET NULL,
    zone TEXT,
    temperature_c NUMERIC,
    threshold_c NUMERIC,
    deviation_c NUMERIC,
    status TEXT DEFAULT 'open',
    corrective_action TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. SEED INITIAL DATA (Based on User Requirements)
-- We use a function to safely seed data without duplicates
CREATE OR REPLACE FUNCTION seed_facility_data() RETURNS void AS $$
DECLARE
    room_ppic UUID;
    room_grouper UUID;
    room_pack_basah UUID;
    room_pack_kering UUID;
    room_kopi UUID;
    room_kitchen UUID;
BEGIN
    -- Rooms
    INSERT INTO facility_rooms (name) VALUES 
        ('PPIC'), ('Grouper'), ('Pack Basah'), ('Pack Kering'), ('Ruang Kopi'), ('Kitchen')
    ON CONFLICT (name) DO NOTHING;

    SELECT id INTO room_ppic FROM facility_rooms WHERE name = 'PPIC';
    SELECT id INTO room_grouper FROM facility_rooms WHERE name = 'Grouper';
    SELECT id INTO room_pack_basah FROM facility_rooms WHERE name = 'Pack Basah';
    SELECT id INTO room_pack_kering FROM facility_rooms WHERE name = 'Pack Kering';
    SELECT id INTO room_kopi FROM facility_rooms WHERE name = 'Ruang Kopi';
    SELECT id INTO room_kitchen FROM facility_rooms WHERE name = 'Kitchen';

    -- PPIC Devices (Room Temp, 4 Chillers, 6 Freezers)
    INSERT INTO facility_devices (room_id, name, type, threshold_temp) VALUES 
        (room_ppic, 'Suhu Ruangan', 'room_temp', 25.0),
        (room_ppic, 'Chiller 1', 'chiller', 5.0), (room_ppic, 'Chiller 2', 'chiller', 5.0),
        (room_ppic, 'Chiller 3', 'chiller', 5.0), (room_ppic, 'Chiller 4', 'chiller', 5.0),
        (room_ppic, 'Freezer 1', 'freezer', -18.0), (room_ppic, 'Freezer 2', 'freezer', -18.0),
        (room_ppic, 'Freezer 3', 'freezer', -18.0), (room_ppic, 'Freezer 4', 'freezer', -18.0),
        (room_ppic, 'Freezer 5', 'freezer', -18.0), (room_ppic, 'Freezer 6', 'freezer', -18.0)
    ON CONFLICT DO NOTHING;

    -- Grouper (Room Temp, 2 Chiller, 1 UC, 3 Freezer)
    INSERT INTO facility_devices (room_id, name, type, threshold_temp) VALUES 
        (room_grouper, 'Suhu Ruangan', 'room_temp', 25.0),
        (room_grouper, 'Chiller 1', 'chiller', 5.0), (room_grouper, 'Chiller 2', 'chiller', 5.0),
        (room_grouper, 'UC Chiller', 'undercounter', 5.0),
        (room_grouper, 'Freezer 1', 'freezer', -18.0), (room_grouper, 'Freezer 2', 'freezer', -18.0), (room_grouper, 'Freezer 3', 'freezer', -18.0)
    ON CONFLICT DO NOTHING;

    -- Pack Basah (Room Temp, 2 Freezer, 3 Chiller)
    INSERT INTO facility_devices (room_id, name, type, threshold_temp) VALUES 
        (room_pack_basah, 'Suhu Ruangan', 'room_temp', 25.0),
        (room_pack_basah, 'Freezer 1', 'freezer', -18.0), (room_pack_basah, 'Freezer 2', 'freezer', -18.0),
        (room_pack_basah, 'Chiller 1', 'chiller', 5.0), (room_pack_basah, 'Chiller 2', 'chiller', 5.0), (room_pack_basah, 'Chiller 3', 'chiller', 5.0)
    ON CONFLICT DO NOTHING;

    -- Pack Kering (3 Room Temp zones, 2 Freezer)
    INSERT INTO facility_devices (room_id, name, type, threshold_temp) VALUES 
        (room_pack_kering, 'Suhu Ruang 1', 'room_temp', 25.0),
        (room_pack_kering, 'Suhu Ruang 2', 'room_temp', 25.0),
        (room_pack_kering, 'Suhu Ruang 3', 'room_temp', 25.0),
        (room_pack_kering, 'Freezer 1', 'freezer', -18.0), (room_pack_kering, 'Freezer 2', 'freezer', -18.0)
    ON CONFLICT DO NOTHING;

    -- Ruang Kopi (Room Temp)
    INSERT INTO facility_devices (room_id, name, type, threshold_temp) VALUES 
        (room_kopi, 'Suhu Ruangan', 'room_temp', 25.0)
    ON CONFLICT DO NOTHING;

    -- Kitchen Devices
    INSERT INTO facility_devices (room_id, name, type, threshold_temp) VALUES 
        (room_kitchen, 'Suhu Ruangan', 'room_temp', 25.0),
        (room_kitchen, 'Chiller 1', 'chiller', 5.0),
        (room_kitchen, 'Undercounter 1', 'undercounter', 5.0),
        (room_kitchen, 'Undercounter 2', 'undercounter', 5.0)
    ON CONFLICT DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- 5. QC FINDINGS (General observations with photo and reason)
CREATE TABLE IF NOT EXISTS qc_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    staff_id UUID REFERENCES staff_accounts(id),
    reason TEXT NOT NULL,
    photo_url TEXT,
    status TEXT DEFAULT 'open', -- open, resolved
    created_at TIMESTAMPTZ DEFAULT NOW()
);

SELECT seed_facility_data();
