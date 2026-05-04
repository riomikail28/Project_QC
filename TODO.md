# Temperature & Storage Monitoring Implementation

## Status: 🚀 In Progress

### [x] Planning & Approval ✅
- Analyzed backend/DB/frontend
- Plan approved by user

### [ ] 1. Database Seeding (db/rooms-seed.sql)
- Create 6 task rooms: PPIC, Grouper, Pack Basah, Pack Kering, Ruang Kopi, Ruang Kitchen
- Add default chiller (4°C) + freezer (-18°C) per room

### [ ] 2. Backend Updates (backend/main.py)
- Add POST /facility/{room_id}/devices/adjust endpoint for +/- chiller/freezer

### [ ] 3. Frontend JS Module (frontend/dashboard/temp-monitor.js)
- Fetch rooms/devices from /facility/rooms
- Poll latest temperatures
- Handle +/- adjust buttons

### [ ] 4. Dashboard UI (frontend/dashboard/index.html)
- Add "Monitoring Suhu & Penyimpanan" section
- Room cards with temps + control buttons
- Load temp-monitor.js

### [ ] 5. Testing & Demo
- Run seed SQL in Supabase
- Test APIs with curl/Postman
- Verify dashboard functionality
- Demo command: `start http://localhost:8000/frontend/dashboard`

**Next Step:** Create db/rooms-seed.sql
