-- ========================================================
-- QC TRACEABILITY SYSTEM - PRODUCTION SCHEMA
-- ========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DO $$ BEGIN
    CREATE TYPE device_type AS ENUM ('chiller', 'freezer', 'undercounter', 'room_temp');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE staff_role AS ENUM ('admin', 'staff');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE qc_status AS ENUM ('pass', 'warning', 'fail', 'pending');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS staff_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT UNIQUE NOT NULL CHECK (length(username) BETWEEN 1 AND 80),
    password_hash TEXT NOT NULL,
    role staff_role NOT NULL DEFAULT 'staff',
    full_name TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_code TEXT UNIQUE NOT NULL,
    sku_code TEXT UNIQUE,
    product_name TEXT NOT NULL,
    category TEXT,
    brix_min NUMERIC,
    brix_max NUMERIC,
    ph_min NUMERIC,
    ph_max NUMERIC,
    tds_min NUMERIC,
    tds_max NUMERIC,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (brix_min IS NULL OR brix_max IS NULL OR brix_min <= brix_max),
    CHECK (ph_min IS NULL OR ph_max IS NULL OR ph_min <= ph_max),
    CHECK (tds_min IS NULL OR tds_max IS NULL OR tds_min <= tds_max)
);

CREATE TABLE IF NOT EXISTS facility_rooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facility_devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    room_id UUID NOT NULL REFERENCES facility_rooms(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type device_type NOT NULL,
    threshold_temp NUMERIC NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_facility_device_room_name UNIQUE (room_id, name)
);

CREATE TABLE IF NOT EXISTS production_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id),
    batch_code TEXT UNIQUE NOT NULL,
    production_date DATE NOT NULL DEFAULT CURRENT_DATE,
    shift TEXT,
    operator_id UUID REFERENCES staff_accounts(id),
    qc_officer_id UUID REFERENCES staff_accounts(id),
    status TEXT NOT NULL DEFAULT 'open',
    final_qc_status qc_status NOT NULL DEFAULT 'pending',
    photo_url TEXT,
    report_url TEXT,
    approved_by UUID REFERENCES staff_accounts(id),
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS production_batch_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id UUID NOT NULL REFERENCES production_batches(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    operator_id UUID REFERENCES staff_accounts(id),
    raw_temp_c NUMERIC,
    core_temp_c NUMERIC,
    room_temp_c NUMERIC,
    ph_value_extracted NUMERIC,
    brix_value_extracted NUMERIC,
    tds_value NUMERIC,
    raw_temp_c_status qc_status,
    core_temp_c_status qc_status,
    room_temp_c_status qc_status,
    ph_value_extracted_status qc_status,
    brix_value_extracted_status qc_status,
    tds_value_status qc_status,
    stage_qc_status qc_status NOT NULL DEFAULT 'pending',
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    photo_url TEXT,
    corrective_action TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_batch_stage_once UNIQUE (batch_id, stage)
);

CREATE TABLE IF NOT EXISTS facility_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES facility_devices(id),
    room_id UUID NOT NULL REFERENCES facility_rooms(id),
    staff_id UUID REFERENCES staff_accounts(id),
    temperature_c NUMERIC NOT NULL CHECK (temperature_c BETWEEN -80 AND 100),
    humidity_rh NUMERIC CHECK (humidity_rh IS NULL OR humidity_rh BETWEEN 0 AND 100),
    is_normal BOOLEAN NOT NULL DEFAULT TRUE,
    reason TEXT,
    photo_url TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facility_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_id UUID REFERENCES facility_logs(id) ON DELETE SET NULL,
    device_id UUID REFERENCES facility_devices(id) ON DELETE SET NULL,
    zone TEXT,
    temperature_c NUMERIC,
    threshold_c NUMERIC,
    deviation_c NUMERIC,
    status TEXT NOT NULL DEFAULT 'open',
    corrective_action TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_open_alert_per_device
ON facility_alerts(device_id)
WHERE status = 'open' AND device_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS qc_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    staff_id UUID REFERENCES staff_accounts(id),
    reason TEXT NOT NULL,
    photo_url TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    corrective_action TEXT,
    resolved_by UUID REFERENCES staff_accounts(id),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_trail (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id UUID REFERENCES staff_accounts(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    before_data JSONB,
    after_data JSONB,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_facility_logs_device_recorded ON facility_logs(device_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_facility_logs_room_recorded ON facility_logs(room_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_batches_date ON production_batches(production_date DESC);
CREATE INDEX IF NOT EXISTS idx_batch_logs_batch ON production_batch_logs(batch_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_trail(entity_type, entity_id, created_at DESC);

CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_staff_updated_at ON staff_accounts;
CREATE TRIGGER trg_staff_updated_at BEFORE UPDATE ON staff_accounts
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_products_updated_at ON products;
CREATE TRIGGER trg_products_updated_at BEFORE UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_rooms_updated_at ON facility_rooms;
CREATE TRIGGER trg_rooms_updated_at BEFORE UPDATE ON facility_rooms
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_devices_updated_at ON facility_devices;
CREATE TRIGGER trg_devices_updated_at BEFORE UPDATE ON facility_devices
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_batches_updated_at ON production_batches;
CREATE TRIGGER trg_batches_updated_at BEFORE UPDATE ON production_batches
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_alerts_updated_at ON facility_alerts;
CREATE TRIGGER trg_alerts_updated_at BEFORE UPDATE ON facility_alerts
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

CREATE OR REPLACE FUNCTION seed_facility_data() RETURNS void AS $$
DECLARE
    room_ppic UUID;
    room_grouper UUID;
    room_pack_basah UUID;
    room_pack_kering UUID;
    room_kopi UUID;
    room_kitchen UUID;
BEGIN
    INSERT INTO facility_rooms (name) VALUES
        ('PPIC'), ('Grouper'), ('Pack Basah'), ('Pack Kering'), ('Ruang Kopi'), ('Kitchen')
    ON CONFLICT (name) DO NOTHING;

    SELECT id INTO room_ppic FROM facility_rooms WHERE name = 'PPIC';
    SELECT id INTO room_grouper FROM facility_rooms WHERE name = 'Grouper';
    SELECT id INTO room_pack_basah FROM facility_rooms WHERE name = 'Pack Basah';
    SELECT id INTO room_pack_kering FROM facility_rooms WHERE name = 'Pack Kering';
    SELECT id INTO room_kopi FROM facility_rooms WHERE name = 'Ruang Kopi';
    SELECT id INTO room_kitchen FROM facility_rooms WHERE name = 'Kitchen';

    INSERT INTO facility_devices (room_id, name, type, threshold_temp) VALUES
        (room_ppic, 'Suhu Ruangan', 'room_temp', 25.0),
        (room_ppic, 'Chiller 1', 'chiller', 5.0), (room_ppic, 'Chiller 2', 'chiller', 5.0),
        (room_ppic, 'Chiller 3', 'chiller', 5.0), (room_ppic, 'Chiller 4', 'chiller', 5.0),
        (room_ppic, 'Freezer 1', 'freezer', -18.0), (room_ppic, 'Freezer 2', 'freezer', -18.0),
        (room_ppic, 'Freezer 3', 'freezer', -18.0), (room_ppic, 'Freezer 4', 'freezer', -18.0),
        (room_ppic, 'Freezer 5', 'freezer', -18.0), (room_ppic, 'Freezer 6', 'freezer', -18.0),
        (room_grouper, 'Suhu Ruangan', 'room_temp', 25.0),
        (room_grouper, 'Chiller 1', 'chiller', 5.0), (room_grouper, 'Chiller 2', 'chiller', 5.0),
        (room_grouper, 'UC Chiller', 'undercounter', 5.0),
        (room_grouper, 'Freezer 1', 'freezer', -18.0), (room_grouper, 'Freezer 2', 'freezer', -18.0),
        (room_grouper, 'Freezer 3', 'freezer', -18.0),
        (room_pack_basah, 'Suhu Ruangan', 'room_temp', 25.0),
        (room_pack_basah, 'Freezer 1', 'freezer', -18.0), (room_pack_basah, 'Freezer 2', 'freezer', -18.0),
        (room_pack_basah, 'Chiller 1', 'chiller', 5.0), (room_pack_basah, 'Chiller 2', 'chiller', 5.0),
        (room_pack_basah, 'Chiller 3', 'chiller', 5.0),
        (room_pack_kering, 'Suhu Ruang 1', 'room_temp', 25.0),
        (room_pack_kering, 'Suhu Ruang 2', 'room_temp', 25.0),
        (room_pack_kering, 'Suhu Ruang 3', 'room_temp', 25.0),
        (room_pack_kering, 'Freezer 1', 'freezer', -18.0), (room_pack_kering, 'Freezer 2', 'freezer', -18.0),
        (room_kopi, 'Suhu Ruangan', 'room_temp', 25.0),
        (room_kitchen, 'Suhu Ruangan', 'room_temp', 25.0),
        (room_kitchen, 'Chiller 1', 'chiller', 5.0),
        (room_kitchen, 'Undercounter 1', 'undercounter', 5.0),
        (room_kitchen, 'Undercounter 2', 'undercounter', 5.0)
    ON CONFLICT (room_id, name) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

SELECT seed_facility_data();
