-- Facility Expansion Schema
-- Add more zones/devices as kitchen expands

-- New zones for expansion
INSERT INTO facility_rooms (name) VALUES 
  ('Expansion Wing A'),
  ('Expansion Wing B');

-- Example new devices
INSERT INTO facility_devices (room_id, name, type, threshold_c) VALUES
  (gen_random_uuid(), 'Ultra Low Freezer -20C', 'freezer', -20.0),
  (gen_random_uuid(), 'Walk-in Chiller #2', 'chiller', 4.0),
  (gen_random_uuid(), 'Dry Storage Ambient', 'ambient', 25.0);

-- Additional indices for performance
CREATE INDEX IF NOT EXISTS idx_logs_zone_temp ON facility_logs(zone, temperature_c);
CREATE INDEX IF NOT EXISTS idx_alerts_open ON facility_alerts(status) WHERE status = 'open';

-- View for facility dashboard summary
CREATE OR REPLACE VIEW v_facility_summary AS 
SELECT 
  fr.name as room_name,
  fd.name as device_name,
  fd.type,
  fd.threshold_c,
  fl.temperature_c,
  fl.is_normal,
  fl.recorded_at,
  fl.zone
FROM facility_logs fl
JOIN facility_devices fd ON fl.device_id = fd.id
JOIN facility_rooms fr ON fd.room_id = fr.id
WHERE fl.recorded_at > NOW() - INTERVAL '24 hours'
ORDER BY fl.recorded_at DESC;
