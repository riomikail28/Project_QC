# Facility UUID and Evidence Preview Fix

## Root Cause

Monitoring and admin facility screens could receive generated IDs such as `default-room-kitchen`, `default-room-pack-kering`, or `log-room-*`. Those strings were later sent as `room_id` / `device_id` to Supabase columns typed as `uuid`, causing errors like:

```text
invalid input syntax for type uuid: "default-room-kitchen"
```

The same synthetic IDs could also make admin device delete return `Device not found`.

## Fix Summary

- `/api/facility/structure` now returns only persisted `facility_rooms` and `facility_devices` rows with UUID IDs.
- Synthetic/default/log-derived IDs are filtered out and are never used as source-of-truth IDs.
- Frontend monitoring rejects non-UUID `room_id` / `device_id` before submit.
- Backend `POST /api/monitoring/log` rejects non-UUID IDs with a clear 400 response.
- Backend `DELETE /api/facility/devices/:id` rejects non-UUID IDs with a clear 400 response.
- Evidence records are normalized so admin reports receive a previewable `photo_url` when `public_url`, `signed_url`, `photo_url`, or `storage_path` exists.
- Admin evidence cells render thumbnails and a preview button instead of showing raw storage paths as the primary preview.

## Migration

Apply:

```sql
supabase/migrations/013_seed_real_facility_uuid.sql
```

This idempotently seeds real UUID-backed facility data:

- Rooms: `PPIC`, `Grouper`, `Pack Basah`, `Pack Kering`, `Ruang Kopi`, `Kitchen`
- Devices per room: `Suhu Ruangan`, `Chiller`, `Freezer`

The migration uses `ON CONFLICT` and unique indexes on `facility_rooms.slug` and `facility_devices(room_id, slug)`.

## QA Manual

1. Run migration 013 in Supabase.
2. Open staff monitoring and refresh.
3. Input temperature for Kitchen, PPIC, Pack Kering, and Ruang Kopi.
4. Confirm request payload contains UUID `room_id` and UUID `device_id`.
5. Confirm no `default-room-*` or `log-room-*` appears in monitoring submit.
6. Open admin facility setup.
7. Add, edit, and delete a device with a real UUID.
8. If a device has logs, delete should return a clear conflict instead of 503.
9. Open admin reports and verify evidence thumbnail appears.
10. Click Preview and verify the image modal opens with image and metadata.

## Expected API Errors

Invalid synthetic monitoring room:

```json
{
  "success": false,
  "error_code": "INVALID_ROOM_ID",
  "message": "room_id must be a valid UUID. Received synthetic id: default-room-kitchen"
}
```

Invalid synthetic facility device delete:

```json
{
  "success": false,
  "error_code": "INVALID_DEVICE_ID",
  "message": "device_id must be a valid UUID. Received synthetic id: default-room-kitchen-chiller"
}
```
