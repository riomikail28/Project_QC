-- Migration: Expand Facility Monitoring to Rooms and Devices
-- PT Astro Teknologi Indonesia - Central Kitchen

-- 1. Create facility_rooms table
CREATE TABLE IF NOT EXISTS facility_rooms (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(100) NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create facility_devices table
CREATE TABLE IF NOT EXISTS facility_devices (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    room_id     UUID NOT NULL REFERENCES facility_rooms(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    type        facility_zone NOT NULL,
    threshold_c NUMERIC(5, 2) NOT NULL,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(room_id, name)
);

-- 3. Update facility_logs (Add device_id)
ALTER TABLE facility_logs ADD COLUMN IF NOT EXISTS device_id UUID REFERENCES facility_devices(id) ON DELETE SET NULL;

-- 4. Update facility_alerts (Add device_id)
ALTER TABLE facility_alerts ADD COLUMN IF NOT EXISTS device_id UUID REFERENCES facility_devices(id) ON DELETE SET NULL;

-- 5. Seed initial rooms as requested by user
INSERT INTO facility_rooms (name) VALUES 
('PPIC'), 
('Grouper'), 
('Pack Basah'), 
('Pack Kering'), 
('Ruang Kopi'), 
('Ruang Kitchen')
ON CONFLICT (name) DO NOTHING;

-- 6. Seed some initial devices for demonstration
INSERT INTO facility_devices (room_id, name, type, threshold_c)
SELECT id, 'Chiller 1', 'chiller', 4.0 FROM facility_rooms WHERE name = 'Ruang Kitchen'
UNION ALL
SELECT id, 'Freezer A', 'freezer', -18.0 FROM facility_rooms WHERE name = 'Ruang Kitchen'
UNION ALL
SELECT id, 'Ambient Sensor', 'ambient', 20.0 FROM facility_rooms WHERE name = 'Pack Kering'
ON CONFLICT DO NOTHING;
