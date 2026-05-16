# Facility And Inspection Fix Report

Date: 2026-05-16

## Root Cause

Production was missing `public.facility_rooms`, while backend and frontend already query `facility_rooms`, `facility_devices`, `facility_logs`, `facility_alerts`, and `temperature_logs`. Because `facility_rooms` was absent from Supabase schema cache, monitoring/admin facility relation queries failed and cascaded into broken setup flows.

Inspection submit returned `400` because frontend/backend upload handling needed clearer multipart validation and backend errors were surfaced as generic `Request failed`. Batch creation could return `Database offline` when the Supabase SDK client was unavailable even though direct REST access could still work with configured Supabase env keys.

## Migration Baru

Created:

- `supabase/migrations/007_facility_rooms_devices_fix.sql`

Migration adds/repairs:

- `facility_rooms`
- `facility_devices`
- `facility_logs`
- `temperature_logs`
- `facility_alerts`
- `production_batches`
- `qc_evidence`
- `qc-evidence` storage bucket
- Required indexes
- Idempotent default seed rooms and devices

Default seeded rooms:

- PPIC
- Grouper
- Pack Basah
- Pack Kering
- Ruang Kopi
- Kitchen

Default seeded units per room:

- Suhu Ruangan / `room_temp` / target 25
- Chiller / `chiller` / target 5
- Freezer / `freezer` / target -18

## Endpoint Baru / Diperbaiki

Admin facility aliases:

- `GET /api/admin/facility/structure`
- `GET /api/admin/facility/rooms`
- `POST /api/admin/facility/rooms`
- `PUT /api/admin/facility/rooms/{room_id}`
- `DELETE /api/admin/facility/rooms/{room_id}`
- `GET /api/admin/facility/devices`
- `POST /api/admin/facility/devices`
- `PUT /api/admin/facility/devices/{device_id}`
- `DELETE /api/admin/facility/devices/{device_id}`

Existing `/api/facility/*` routes remain available.

## Admin Facility CRUD Fix

- Admin can add/edit/delete rooms.
- Admin can add/edit/delete devices.
- Default device delete is no longer permanently locked; UI shows confirmation.
- Device modal now supports `device_type`, target temperature, min temperature, max temperature, and active status.
- CRUD refreshes facility list without page reload.
- API responses now include clear `success/message/data` envelopes for admin facility CRUD.

## Upload Inspection Fix

- `POST /api/inspection/submit` reads `request.form` and `request.files`.
- Photo is optional.
- Barcode/manual batch code is required.
- `ccp_stage` defaults to `receiving`.
- `qc_status` defaults to `pending`; `hold` is normalized to `warning`.
- Staff id is taken from token/session when not provided in form.
- QC rows store direct columns plus `inspection_result` JSON.
- Evidence rows write `mime_type`, `file_size`, storage path, bucket, uploader, related type, and related id.

## Batch Offline Fix

- Batch create no longer requires `product_id` when `batch_code` is available.
- Batch create stores `batch_code`, `product_name`, `production_date`, `expired_date`, `status`, `created_by`, `operator_id`, `created_at`.
- If Supabase SDK client is unavailable, service attempts direct REST insert via configured Supabase env.
- Error responses now include `success: false` and `message`.

Required production env:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Fallbacks still supported:

- `SUPABASE_KEY`
- `SUPABASE_ANON_KEY`

## CSP Warning

Current CSP already allows CDN source-map fetches in `connect-src`:

- `https://cdn.jsdelivr.net`
- `https://unpkg.com`

The sourcemap warning is not the root application failure. It can disappear after redeploy with the current CSP. For stricter production hardening, self-host Chart.js/Lucide under `frontend/vendor/` in a separate asset cleanup.

## QA Result

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q backend tests
```

Result:

```text
96 passed, 1 warning
compileall passed
```

## Cara Apply Migration

Supabase CLI:

```bash
supabase db push
```

Manual:

1. Open Supabase SQL Editor.
2. Run `supabase/migrations/007_facility_rooms_devices_fix.sql`.
3. Redeploy Vercel with correct Supabase env values.

## Manual Production Validation

1. Open `/admin/#section-facility`.
2. Add room.
3. Edit room.
4. Delete room.
5. Add unit.
6. Edit unit type and thresholds.
7. Delete unit.
8. Open `/inspection.html`.
9. Create batch.
10. Submit QC with and without photo.
11. Verify object in Supabase Storage bucket `qc-evidence`.
12. Verify rows in admin reports.
