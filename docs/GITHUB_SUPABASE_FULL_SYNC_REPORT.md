# GitHub Supabase Full Sync Report

Date: 2026-05-16

## Problems Found

- Production Supabase schema differed from repo migrations.
- Backend inserted columns not present in production, especially `staff_accounts.full_name`.
- Backend omitted required production fields for `facility_logs`.
- Batch creation did not handle production `production_batches.product_id NOT NULL`.
- Admin facility CRUD mixed persisted rows with synthetic fallback rows.
- CDN source-map requests were blocked by stale CSP.
- Legacy tables `rooms` and `storage_units` still exist but should not be used for new features.

## Final Schema Contract

See [PROJECT_QC_SYNC_CONTRACT.md](PROJECT_QC_SYNC_CONTRACT.md).

Key decisions:

- Facility master: `facility_rooms`, `facility_devices`.
- Staff auth: `staff_accounts`.
- Staff profile/name: `users`.
- Batch default product: `products.product_code = 'GENERAL-QC'`.
- Evidence bucket/table: `qc-evidence`, `qc_evidence`.
- Legacy avoided for new code: `rooms`, `storage_units`.

## Migration Baru

- `supabase/migrations/008_sync_qc_production_contract.sql`

This migration:

- Seeds `GENERAL-QC`.
- Aligns facility room/device/log columns.
- Converts `facility_logs.zone` to text when needed.
- Relaxes stale `facility_logs` not-null constraints where backend now sends compatibility data anyway.
- Aligns `temperature_logs`, `qc_reports`, `qc_evidence`.
- Seeds default rooms/devices idempotently.
- Adds staff profile support through `users.staff_account_id`.

## Endpoint/Backend Fixes

- Staff CRUD no longer writes `full_name` to `staff_accounts`.
- Staff display name syncs through `users`.
- Batch creation resolves product codes or uses `GENERAL-QC`.
- Monitoring submit writes required production fields.
- Facility CRUD uses `facility_rooms/facility_devices` and direct REST fallback.
- Admin reports expose temperature, inspection, evidence, batches, staff activity, approvals.
- CSP header is overwritten and includes CDN connect sources.

## Frontend Fixes

- Admin staff password field includes `autocomplete`.
- Admin facility modal supports room/device status, device type, target/min/max temperatures.
- API errors show backend `message` instead of generic `Request failed`.
- Empty states remain for no data.

## CRUD Status

Ready:

- Add/edit/delete room.
- Add/edit/delete device.
- Edit device type.
- Edit target/min/max temperature.
- Active/inactive room and device.
- Default/synthetic fallback device deletion no longer hard-crashes UI.

## Upload Flow

Final storage paths:

- `staff/{staff_id}/temperature/{YYYY-MM-DD}/{uuid}.jpg`
- `staff/{staff_id}/inspection/{YYYY-MM-DD}/{uuid}.jpg`
- `staff/{staff_id}/ccp/{YYYY-MM-DD}/{uuid}.jpg`
- `batches/{batch_id}/evidence/{uuid}.jpg`

Upload flow:

1. Validate MIME and size.
2. Upload to `qc-evidence`.
3. Store metadata in `qc_evidence`.
4. Store path/url on related report/log row.
5. Roll back uploaded file when DB insert fails where practical.

## Staff To Admin Report Flow

Temperature:

Staff `monitoring.html` -> `POST /api/monitoring/log` -> `facility_logs` + `qc_evidence` -> admin temperature report.

Inspection:

Staff `inspection.html` -> `POST /api/inspection/submit` -> `qc_reports` + `barcode_labels` + `qc_evidence` -> admin QC report/evidence report.

Batch:

Staff `new_batch.html` -> `POST /api/batch/create` -> `production_batches`, using `GENERAL-QC` when product UUID is missing.

Approval:

Admin approval endpoints update `approvals` or `qc_reports` status.

## Test Result

Commands:

```bash
python -m pytest -q
python -m compileall -q backend tests
```

Local result:

```text
107 passed, 1 warning
compileall passed
```

## Apply Migration

Supabase CLI:

```bash
supabase db push
```

Manual SQL Editor:

1. Open Supabase SQL Editor.
2. Run `supabase/migrations/008_sync_qc_production_contract.sql`.
3. Verify `GENERAL-QC` exists in `products`.
4. Verify default facility rooms/devices exist.

## Deploy To Vercel

1. Confirm environment variables:
   - `JWT_SECRET_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_STORAGE_BUCKET=qc-evidence`
   - `FLASK_ENV=production`
2. Push to `main`.
3. Let Vercel redeploy.
4. Hard refresh browser and verify CSP header includes `cdn.jsdelivr.net` and `unpkg.com` in `connect-src`.

## Residual Risk

- Production contains enum-heavy legacy columns. Migration converts/relaxes the known blocking `facility_logs.zone` path, but any hidden trigger/policy outside repo should be validated in Supabase SQL Editor.
- Browser extension `content-script.js` / `AdUnit` logs are unrelated to app code.

## Status

READY FOR MASS USER TESTING after applying migration and redeploying Vercel.
