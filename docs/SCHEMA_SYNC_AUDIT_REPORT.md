# Schema Sync Audit Report

Date: 2026-05-16

## Summary

The main production failures came from schema drift between Supabase production and backend/frontend assumptions:

- `staff_accounts.full_name` was referenced by backend/admin UI but does not exist in production.
- `production_batches.product_id` is `NOT NULL`, while staff flows can submit only SKU/free-form product data.
- `facility_logs.zone`, `threshold_c`, and `is_normal` are required in production, while monitoring submit did not always send them.
- `facility_rooms` and `facility_devices` are the correct facility master tables; legacy `rooms` and `storage_units` must not be used for new features.
- CDN sourcemap warnings were caused by production serving an older CSP header.

## Findings

| Area | File(s) | Issue | Root Cause | Fix |
| --- | --- | --- | --- | --- |
| Staff CRUD | `backend/auth/staff_manager.py`, `frontend/js/admin_app.js` | Add staff failed with `full_name` column missing. | Production `staff_accounts` has no `full_name`. | Store names in `users.full_name`, linked by `staff_account_id`; never POST/PATCH `full_name` to `staff_accounts`. |
| Batch create | `backend/services/batch_service.py`, `backend/api/batch_routes.py` | SKU like `SKU-HONEY-001` was sent to UUID `product_id`. | Frontend sends product code; production requires UUID FK. | Resolve SKU to `products.id`; if unresolved/missing, create/use default `GENERAL-QC`. |
| Monitoring submit | `backend/services/monitoring_service.py` | Insert failed on `facility_logs.zone NOT NULL`. | Payload omitted legacy required fields. | Send `zone`, `device_type`, `threshold_c`, `is_normal`, `temperature_c`, `notes`, and compatibility values. |
| Facility CRUD | `backend/api/facility_routes.py`, `backend/monitoring/facility_manager.py`, `frontend/js/admin_app.js` | Add/edit/delete room/device unstable, synthetic fallback IDs caused 503. | Master data and fallback display rows were mixed. | Admin CRUD endpoints use `facility_rooms/devices`; synthetic IDs delete as no-op success; CRUD supports direct REST fallback. |
| Admin reports | `backend/api/admin_routes.py`, `backend/services/admin_service.py` | Staff reports were not exposed through all requested report endpoints. | Missing endpoint contract. | Added temperature, inspection, evidence, batches, staff-activity, approvals endpoints. |
| Storage | `backend/services/storage_service.py`, `backend/api/storage_routes.py`, `backend/services/inspection_service.py` | Evidence metadata was incomplete. | `mime_type` and typed storage path were not consistently stored. | Store `mime_type`, `file_size`, bucket, path, uploader, related type/id. |
| CSP | `backend/middleware/security_middleware.py` | CDN `.map` requests blocked. | Header used old `connect-src`; `setdefault` could preserve stale header. | CSP now overwrites header and includes `cdn.jsdelivr.net` and `unpkg.com`. |

## Legacy Tables

`rooms` and `storage_units` remain in production but are not used by new code paths. Their appearance in old `temperature_logs.storage_unit_id` is historical compatibility only.

## Required Migration

Use:

- `supabase/migrations/008_sync_qc_production_contract.sql`

This migration seeds `GENERAL-QC`, aligns facility/device/log/report/evidence columns, seeds default rooms/devices, and prepares staff profile storage through `users`.
