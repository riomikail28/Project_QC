# Massive Fix Audit Report

Date: 2026-05-16

## Scope

Audited backend routes/services, frontend staff/admin flows, Supabase migrations/storage, tests, and docs for production readiness of the QC Central Kitchen mobile web app.

## Findings

| Severity | Area | Bug / Risk | Root Cause | Files impacted | Fix plan |
| --- | --- | --- | --- | --- | --- |
| Critical | Staff QC input | Inspection page did not submit a complete QC record to `qc_reports`. | UI button redirected to batch page; backend inspection routes were read-only. | `frontend/staff/inspection.html`, `frontend/js/inspection.js`, `backend/api/inspection_routes.py`, `backend/services/inspection_service.py` | Add `/api/inspection/submit`, multipart support, DB insert, barcode label insert, audit write, loading/error state. |
| Critical | Staff-admin reporting | Admin reports mixed legacy endpoints and did not expose required report endpoints. | Admin service had overview/fallback methods but no consistent `/reports/*` contract. | `backend/api/admin_routes.py`, `backend/services/admin_service.py`, `frontend/js/admin_app.js` | Add temperature, inspection, evidence, batch, staff-activity endpoints with `{success,data,message}`. |
| Critical | Photo evidence | Storage paths were inconsistent and did not follow `qc-evidence/staff/{staff_id}/{type}` layout. | Storage helper used legacy `{staff_id}/{date}` path and frontend direct upload used another layout. | `backend/services/storage_service.py`, `backend/api/storage_routes.py`, `frontend/js/api.js`, `backend/services/monitoring_service.py` | Add typed storage paths while keeping legacy default compatibility; record `qc_evidence` metadata. |
| High | Monitoring submit | Submit from "All rooms" could send `room_id=all`. | Hidden room field used selected filter instead of actual device room. | `frontend/js/monitoring.js` | Use `device.room_id || room.id` when opening log modal. |
| High | Approval | Admin could list pending items but could not approve/reject from API/UI. | Approval mutation endpoints absent. | `backend/api/admin_routes.py`, `backend/services/admin_service.py`, `frontend/js/admin_app.js` | Add approve/reject endpoints and UI action buttons. |
| High | Role stability | Role naming was split between `staff` and desired `qc_staff`; supervisor/manager not accepted for admin-class routes. | Legacy token/profile contracts used `staff`; middleware checked raw role. | `backend/middleware/security_middleware.py`, `frontend/js/auth.js` | Normalize authorization internally while preserving legacy frontend/session compatibility. |
| High | Database sync | Required tables/columns/indexes for reports/evidence/approval were not guaranteed by migrations. | Prior migrations were incremental and not a full additive compatibility layer. | `supabase/migrations/006_massive_qc_fix.sql` | Add safe migration for `qc_evidence`, `approvals`, missing columns, indexes, storage bucket/policies. |
| Medium | Dashboard real data | Dashboard chart class used fake naming and empty states needed to stay explicit. | Historical CSS naming remained after real-data integration. | `frontend/staff/dashboard.html`, `frontend/styles/dashboard.css`, `frontend/js/dashboard.js` | Rename chart class and keep empty-state rendering when all counts are zero. |
| Medium | Upload validation | Invalid upload could fail after Supabase client initialization instead of MIME validation. | Storage helper created Supabase client before validating bytes/MIME. | `backend/services/storage_service.py` | Validate file before accessing Supabase. |
| Medium | API consistency | Existing admin endpoints returned raw arrays/objects; new contract requires envelope. | Legacy frontend depended on raw responses. | `backend/api/admin_routes.py` | Keep legacy endpoints stable; add new required endpoints with consistent envelope. |
| Medium | Mobile routes | Admin/staff route separation needed regression coverage. | Mixed historical hash navigation exists; redirect handled on staff dashboard only. | `backend/__init__.py`, `frontend/staff/dashboard.html`, `tests/test_mobile_routes.py` | Add route tests and keep `/admin/` serving separate admin panel. |

## Dummy / Fallback Review

No new dummy business data was added. Existing test fixtures and historical docs mention fake/demo data for tests or past reports only. Staff/admin dashboard API paths return empty arrays, `0`, or `null` and frontend renders empty states such as "No data available yet" instead of fabricated reports.

Operational default monitoring rooms still exist to preserve current app behavior and existing tests. They are UI scaffolding for input targets, not fake submitted QC activity.

## Production Fix Plan Applied

1. Make staff inspection submit persist real `qc_reports` and barcode traceability.
2. Standardize evidence upload metadata and storage paths.
3. Add admin reporting endpoints for all staff-submitted data.
4. Add approval approve/reject flow.
5. Add additive Supabase migration for missing tables/columns/indexes.
6. Add regression tests for staff input, photo upload, admin reporting, roles, mobile routes, and empty real-data behavior.
