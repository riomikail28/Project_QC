-- Seed Script: Task-Specific Rooms + Default Chiller/Freezer
-- Run this ONCE in Supabase SQL Editor after confirming tables exist
-- Cleans up any test data first

-- ⚠️ SAFETY: Delete demo data (optional, comment out if you want to keep)
-- DELETE FROM facility_devices;
-- DELETE FROM facility_rooms WHERE name IN ('Dapur Utama', 'Packing Area', 'Expansion Wing A', 'Expansion Wing B');

-- 1. Create Task Rooms
INSERT INTO facility_rooms (name) VALUES 
  ('PPIC'),
  ('Grouper'),
  ('Pack Basah'),
  ('Pack Kering'),
  ('Ruang Kopi'),
  ('Ruang Kitchen')
ON CONFLICT (name) DO NOTHING;

-- 2. Get Room IDs (using CTE for simplicity)
WITH task_rooms AS (
  SELECT id, name FROM facility_rooms 
  WHERE name IN ('PPIC', 'Grouper', 'Pack Basah', 'Pack Kering', 'Ruang Kopi', 'Ruang Kitchen')
)
-- 3. Add Default Chiller (4°C) + Freezer (-18°C) per room
INSERT INTO facility_devices (room_id, name, type, threshold_c, is_active) 
SELECT 
  tr.id, 
  CONCAT(fr.type, ' ', ROW_NUMBER() OVER (PARTITION BY tr.id, fr.type), ' - ', tr.name),
  fr.type,
  fr.threshold_c,
  true
FROM task_rooms tr
CROSS JOIN (VALUES 
  ('chiller', 4.0),
  ('freezer', -18.0)
) AS fr(type, threshold_c)
ON CONFLICT DO NOTHING;

-- 4. Verify seeding
SELECT 
  r.name as room,
  d.name as device,
  d.type,
  d.threshold_c
FROM facility_rooms r
JOIN facility_devices d ON r.id = d.room_id
WHERE r.name IN ('PPIC', 'Grouper', 'Pack Basah', 'Pack Kering', 'Ruang Kopi', 'Ruang Kitchen')
ORDER BY r.name, d.type;

-- 🎉 Expected: 6 rooms × 2 devices = 12 devices created
