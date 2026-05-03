-- =======================================================
-- INTELLIGENT QC TRACEABILITY SYSTEM
-- PT Astro Teknologi Indonesia - Central Kitchen
-- Database Schema for Supabase (PostgreSQL)
-- =======================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -------------------------------------------------------
-- ENUM TYPES
-- -------------------------------------------------------

CREATE TYPE facility_zone AS ENUM ('chiller', 'freezer', 'ambient');
CREATE TYPE alert_status   AS ENUM ('open', 'acknowledged', 'resolved');
CREATE TYPE ccp_stage      AS ENUM ('CCP1_PRE_COOK', 'CCP2_POST_COOK', 'CCP3_PACKAGING');
CREATE TYPE qc_status      AS ENUM ('pass', 'fail', 'pending_review');
CREATE TYPE batch_status   AS ENUM ('in_progress', 'completed', 'rejected');

-- -------------------------------------------------------
-- MODULE A: FACILITY MONITORING
-- -------------------------------------------------------

CREATE TABLE facility_logs (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone            facility_zone NOT NULL,
    recorded_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    temperature_c   NUMERIC(5, 2) NOT NULL,
    -- SOP thresholds (stored for audit immutability)
    threshold_c     NUMERIC(5, 2) NOT NULL,
    is_normal       BOOLEAN       NOT NULL,   -- true = within SOP
    recorder_id     UUID          REFERENCES auth.users(id) ON DELETE SET NULL,
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE facility_alerts (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_id          UUID         NOT NULL REFERENCES facility_logs(id) ON DELETE CASCADE,
    zone            facility_zone NOT NULL,
    temperature_c   NUMERIC(5, 2) NOT NULL,
    threshold_c     NUMERIC(5, 2) NOT NULL,
    deviation_c     NUMERIC(5, 2) GENERATED ALWAYS AS (temperature_c - threshold_c) STORED,
    status          alert_status NOT NULL DEFAULT 'open',
    alert_sent_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    acknowledged_by UUID         REFERENCES auth.users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    notes           TEXT
);

-- -------------------------------------------------------
-- MODULE B: BATCH QUALITY TRACEABILITY
-- -------------------------------------------------------

CREATE TABLE products (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_code    VARCHAR(50)  NOT NULL UNIQUE,
    product_name    VARCHAR(255) NOT NULL,
    -- SOP thresholds per product
    ph_min          NUMERIC(4, 2),
    ph_max          NUMERIC(4, 2),
    brix_min        NUMERIC(5, 2),
    brix_max        NUMERIC(5, 2),
    tds_min         NUMERIC(8, 2),
    tds_max         NUMERIC(8, 2),
    core_temp_min_c NUMERIC(5, 2) DEFAULT 75.00,  -- Post-cook CCP2
    raw_temp_max_c  NUMERIC(5, 2) DEFAULT 5.00,   -- Pre-cook CCP1
    room_temp_max_c NUMERIC(5, 2) DEFAULT 20.00,  -- Packaging CCP3
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE staff_accounts (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(80)  NOT NULL UNIQUE,
    password_hash   TEXT         NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'staff' CHECK (role IN ('admin', 'staff')),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE production_batches (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_code      VARCHAR(100) NOT NULL UNIQUE,  -- e.g. BATCH-2024-04-19-001
    product_id      UUID         NOT NULL REFERENCES products(id),
    production_date DATE         NOT NULL DEFAULT CURRENT_DATE,
    shift           VARCHAR(10),                   -- e.g. 'morning', 'afternoon'
    operator_id     UUID         REFERENCES auth.users(id) ON DELETE SET NULL,
    qc_officer_id   UUID         REFERENCES auth.users(id) ON DELETE SET NULL,
    status          batch_status NOT NULL DEFAULT 'in_progress',
    final_qc_status qc_status   DEFAULT 'pending_review',
    report_url      TEXT,        -- Supabase Storage path to final PDF report
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE production_batch_logs (
    id                    UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id              UUID         NOT NULL REFERENCES production_batches(id) ON DELETE CASCADE,
    stage                 ccp_stage    NOT NULL,
    recorded_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    recorder_id           UUID         REFERENCES auth.users(id) ON DELETE SET NULL,

    -- ---- CCP1: Pre-Cook ----
    raw_material_photo_path  TEXT,        -- Supabase Storage path
    raw_temp_c               NUMERIC(5, 2),
    raw_temp_status          qc_status,

    -- ---- CCP2: Post-Cook ----
    core_temp_c              NUMERIC(5, 2),
    core_temp_status         qc_status,
    ph_meter_photo_path      TEXT,        -- Supabase Storage path (Milwaukee pH51 LCD)
    ph_value_extracted       NUMERIC(4, 2),
    ph_value_status          qc_status,
    refractometer_photo_path TEXT,        -- Supabase Storage path (Digital Refractometer LCD)
    brix_value_extracted     NUMERIC(5, 2),
    brix_value_status        qc_status,
    tds_value                NUMERIC(8, 2),
    tds_value_status         qc_status,
    ocr_confidence_ph        NUMERIC(5, 4), -- 0.0 to 1.0
    ocr_confidence_brix      NUMERIC(5, 4),
    ocr_raw_output           JSONB,         -- full OCR response for audit

    -- ---- CCP3: Packaging ----
    packaging_photo_path     TEXT,        -- Supabase Storage path
    room_temp_c              NUMERIC(5, 2),
    room_temp_status         qc_status,

    -- ---- Overall ----
    stage_qc_status          qc_status    NOT NULL DEFAULT 'pending_review',
    notes                    TEXT,
    created_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE corrective_actions (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_log_id    UUID         REFERENCES production_batch_logs(id) ON DELETE CASCADE,
    action_text     TEXT         NOT NULL,
    created_by      UUID         REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------
-- INDEXES
-- -------------------------------------------------------

CREATE INDEX idx_facility_logs_zone_time   ON facility_logs (zone, recorded_at DESC);
CREATE INDEX idx_facility_alerts_status    ON facility_alerts (status, alert_sent_at DESC);
CREATE INDEX idx_batch_logs_batch_stage    ON production_batch_logs (batch_id, stage);
CREATE INDEX idx_batches_production_date   ON production_batches (production_date DESC);
CREATE INDEX idx_batches_status            ON production_batches (status, final_qc_status);
CREATE INDEX idx_staff_accounts_username   ON staff_accounts (username);

-- -------------------------------------------------------
-- ROW-LEVEL SECURITY (Supabase RLS)
-- -------------------------------------------------------

ALTER TABLE facility_logs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE facility_alerts       ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_batches    ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_batch_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE products              ENABLE ROW LEVEL SECURITY;
ALTER TABLE staff_accounts        ENABLE ROW LEVEL SECURITY;
ALTER TABLE corrective_actions    ENABLE ROW LEVEL SECURITY;

-- Example policy: authenticated users can read all; only owners can insert
CREATE POLICY "Authenticated read facility_logs"
    ON facility_logs FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated insert facility_logs"
    ON facility_logs FOR INSERT TO authenticated WITH CHECK (auth.uid() = recorder_id);

CREATE POLICY "Authenticated read batches"
    ON production_batches FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated insert batch_logs"
    ON production_batch_logs FOR INSERT TO authenticated WITH CHECK (auth.uid() = recorder_id);

-- -------------------------------------------------------
-- UPDATED_AT TRIGGER
-- -------------------------------------------------------

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_batches_updated_at
    BEFORE UPDATE ON production_batches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_staff_updated_at
    BEFORE UPDATE ON staff_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- -------------------------------------------------------
-- SEED: Central kitchen products and SOP thresholds
-- -------------------------------------------------------

INSERT INTO products (product_code, product_name, ph_min, ph_max, brix_min, brix_max, tds_min, tds_max)
VALUES
    ('SKU-BEEF-001', 'Finish Goods - Chilled/Frozen Original beef 90gr - AK', NULL, NULL, 11.0, 14.0, NULL, NULL),
    ('SKU-BEEF-002', 'Finish Goods - Chilled/Frozen Teriyaki beef 90gr- AK', NULL, NULL, 11.0, 14.0, NULL, NULL),
    ('SKU-CHKN-001', 'Finish Goods - Chilled/Frozen Teriyaki chicken 90gr - AK', NULL, NULL, 11.0, 14.0, NULL, NULL),
    ('SKU-CUGIL-001', 'Finish Goods - Chilled/Frozen Cugil 100gr - AK', NULL, NULL, 11.0, 14.0, NULL, NULL),
    ('SKU-CUGIL-002', 'Finish Goods - Chilled/Frozen Cugil tanpa Pete 100gr - AK', NULL, NULL, 11.0, 14.0, NULL, NULL),
    ('SKU-BUMBU-001', 'Finish Goods - Bumbu Pecel 150gr - AG', 4.0, 6.0, NULL, NULL, NULL, NULL),
    ('SKU-BUMBU-002', 'Finish Goods - Garlic In Oil 150gr - AG', 4.5, 7.0, NULL, NULL, NULL, NULL),
    ('SKU-BUMBU-003', 'Finish Goods - Bumbu Dasar Merah 150gr - AG', 5.0, 6.5, NULL, NULL, NULL, NULL),
    ('SKU-BUMBU-004', 'Finish Goods - Bumbu Dasar Putih 150gr - AG', 5.0, 6.5, NULL, NULL, NULL, NULL),
    ('SKU-WIP-001', 'Finish Goods - WIP Astro Kitchen - Espresso concentrate 1L', NULL, NULL, NULL, NULL, 4800.0, 5700.0),
    ('SKU-WIP-002', 'Finish Goods - WIP Cold Brew concentrate PATRIA 1L - AK', NULL, NULL, NULL, NULL, 2300.0, 3700.0),
    ('SKU-WIP-003', 'Finish Goods - WIP Cold Brew concentrate KINTAMANI 1L - AK', NULL, NULL, NULL, NULL, 2300.0, 3700.0),
    ('SKU-CHKN-002', 'Finish Goods - Grilled Chicken 100gr - AK', 4.0, 6.0, 55.0, 65.0, NULL, NULL),
    ('SKU-EGG-001', 'Finish Goods - Telur Marinated 1pcs - AK', NULL, NULL, 25.0, 35.0, NULL, NULL),
    ('SKU-ONIG-001', 'Finish Goods - Onigiri Salmon Mentai 110gr - AK', 3.5, 6.5, NULL, NULL, NULL, NULL),
    ('SKU-ONIG-002', 'Finish Goods - Onigiri Tuna Mayo 110gr - AK', 3.5, 6.5, NULL, NULL, NULL, NULL),
    ('SKU-ONIG-003', 'Finish Goods - Onigiri Ebi Mentai 110gr - AK', 3.0, 6.0, NULL, NULL, NULL, NULL),
    ('SKU-ONIG-004', 'Finish Goods - Onigiri Beef Yakiniku 110gr - AK', 4.0, 6.0, 20.0, 25.0, NULL, NULL),
    ('SKU-ONIG-005', 'Finish Goods - Onigiri Chicken Truffle 110gr - AK', 5.0, 7.0, 15.0, 25.0, NULL, NULL),
    ('SKU-SAMBAL-001', 'Finish Goods - Sambal Korek 15gr ver 2 - AK', 4.0, 6.0, NULL, NULL, NULL, NULL),
    ('SKU-SAUCE-001', 'Finish Goods - Sauce Katsu 100gr', 3.0, 4.0, 20.0, 30.0, NULL, NULL),
    ('SKU-SAUCE-002', 'Finish Goods - Sauce Mentai 100gr', 3.0, 4.0, 35.0, 75.0, NULL, NULL),
    ('SKU-HONEY-001', 'Finish Goods - Honey Jelly 150gr', NULL, NULL, 9.0, 11.0, NULL, NULL)
ON CONFLICT (product_code) DO UPDATE SET
    product_name = EXCLUDED.product_name,
    ph_min = EXCLUDED.ph_min,
    ph_max = EXCLUDED.ph_max,
    brix_min = EXCLUDED.brix_min,
    brix_max = EXCLUDED.brix_max,
    tds_min = EXCLUDED.tds_min,
    tds_max = EXCLUDED.tds_max,
    is_active = TRUE,
    updated_at = NOW();

INSERT INTO staff_accounts (username, password_hash, role)
VALUES
    ('admin', encode(digest('admin123', 'sha256'), 'hex'), 'admin'),
    ('staff', encode(digest('1234', 'sha256'), 'hex'), 'staff')
ON CONFLICT (username) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    is_active = TRUE,
    updated_at = NOW();
