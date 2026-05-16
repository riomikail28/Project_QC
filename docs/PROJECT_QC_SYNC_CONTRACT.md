# Project QC Sync Contract

Date: 2026-05-16

This document is the source-of-truth contract between Supabase production schema, Flask backend APIs, and staff/admin frontend flows.

## A. Facility Monitoring

Standard tables:

- `facility_rooms`: room master for QC monitoring areas.
- `facility_devices`: device/unit master linked to `facility_rooms`.
- `facility_logs`: primary staff temperature monitoring submissions.
- `facility_alerts`: abnormal temperature alerts and corrective status.
- `temperature_logs`: compatibility table for historical/mobile temperature reads.

Required device types:

- `room_temp`
- `chiller`
- `freezer`

New features must use `facility_rooms` and `facility_devices`, not legacy room tables.

## B. Inspection/QC

Standard tables:

- `production_batches`: batch header records.
- `production_batch_logs`: CCP/stage records.
- `products`: product master. `GENERAL-QC` is the default product for free-form batches.
- `qc_reports`: staff QC inspection submissions.
- `qc_evidence`: uploaded file metadata.
- `barcode_labels`: barcode traceability records.
- `approvals`: admin/supervisor approval queue.
- `audit_logs`: system activity audit records.

`production_batches.product_id` is treated as required in production. If staff does not provide a valid product id, backend must resolve or create `products.product_code = 'GENERAL-QC'`.

## C. Auth/User

Standard tables:

- `staff_accounts`: authentication account table.
- `users`: user profile table; staff display names live here through `users.staff_account_id`.
- `staff_activity`: high-level staff activity feed.

Do not write `full_name` to `staff_accounts` in production. The production table does not have that column.

## D. Legacy Tables To Avoid

Do not use these tables for new features:

- `rooms`
- `storage_units`

They may remain in production for historical compatibility only. New monitoring and admin facility features must use `facility_rooms` and `facility_devices`.

## Response Contract

Success:

```json
{
  "success": true,
  "data": {},
  "message": "OK"
}
```

Failure:

```json
{
  "success": false,
  "data": null,
  "message": "Clear user-facing reason"
}
```

Legacy endpoints may still return arrays for backwards compatibility, but newly added admin/staff production endpoints should use the envelope above.
