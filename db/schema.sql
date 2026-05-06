-- QC Central Kitchen - Supabase PostgreSQL Schema
-- Version: 2.0 (Modular)

-- 1. Staff Accounts
CREATE TABLE staff_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT CHECK (role IN ('admin', 'staff')) DEFAULT 'staff',
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Product Catalog (SKU)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_code TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    category TEXT,
    brix_min DECIMAL, brix_max DECIMAL,
    ph_min DECIMAL, ph_max DECIMAL,
    tds_min DECIMAL, tds_max DECIMAL,
    temp_threshold DECIMAL DEFAULT 5.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Production Batches
CREATE TABLE production_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_code TEXT UNIQUE NOT NULL,
    product_id UUID REFERENCES products(id),
    operator_id UUID REFERENCES staff_accounts(id),
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    final_qc_status TEXT DEFAULT 'pending',
    qc_score INTEGER DEFAULT 0
);

-- 4. CCP Logs (Critical Control Points)
CREATE TABLE ccp_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id UUID REFERENCES production_batches(id),
    stage TEXT NOT NULL, -- Incoming, Cooking, Cooling, Packaging
    metrics JSONB, -- {temp: 4.5, brix: 12.1, ...}
    photo_url TEXT,
    qc_status TEXT,
    operator_id UUID REFERENCES staff_accounts(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Facility Logs (Temperature Monitoring)
CREATE TABLE facility_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone TEXT NOT NULL,
    temperature_c DECIMAL NOT NULL,
    threshold_c DECIMAL,
    is_normal BOOLEAN DEFAULT TRUE,
    status TEXT, -- PASS, WARNING, FAIL
    logged_by UUID REFERENCES staff_accounts(id),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Alerts & Corrective Actions
CREATE TABLE facility_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_id UUID REFERENCES facility_logs(id),
    zone TEXT NOT NULL,
    temperature_c DECIMAL NOT NULL,
    threshold_c DECIMAL NOT NULL,
    deviation_c DECIMAL,
    status TEXT DEFAULT 'open', -- open, resolved
    notes TEXT,
    alert_sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_by UUID REFERENCES staff_accounts(id),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE corrective_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_log_id UUID,
    action_text TEXT NOT NULL,
    created_by UUID REFERENCES staff_accounts(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
