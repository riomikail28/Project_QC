# Security Environment Report

Date: 2026-05-14

## Executive Summary

Vercel + Supabase configuration was audited for production launch. Safe fixes were applied:

- Storage bucket default changed from `qc-photos` to `qc-evidence`.
- Frontend camera upload bucket changed to `qc-evidence`.
- Hardcoded Supabase placeholder URL/key removed from `backend/qc/parametric_checker.py`.
- `.env.example` expanded with production-required variables.
- Supabase Storage migration and RLS policies generated for `qc-evidence`.

## Secret Exposure Audit

### Service Role Key In Frontend

Status: Pass.

No `SUPABASE_SERVICE_ROLE_KEY` usage was found in frontend files.

### Public Anon Key In Frontend

Status: Conditional.

`frontend/js/camera-module.js` reads `window.QC_CONFIG.supabaseAnonKey`. This is acceptable only for Supabase anon key. It must never receive service-role credentials.

### Hardcoded Secrets

Status: Fixed.

Removed placeholder fallback credentials in `backend/qc/parametric_checker.py`. Missing Supabase config now raises an explicit runtime error instead of silently using placeholder values.

### JWT Exposure

Status: Needs hardening.

Access token is stored in `localStorage` by `frontend/js/auth.js`. This is functional but increases risk if XSS occurs.

Recommended next step:

- Move access token to memory or use a secure cookie/session model.

### `innerHTML` Rendering

Status: Needs hardening.

Several frontend files render API data with `innerHTML`. This is common in the current codebase but should be hardened before broad public exposure.

Recommended next step:

- Add shared `escapeHtml()` helper.
- Use `textContent` for untrusted data.
- Keep templated HTML only for static UI skeletons.

## Upload Security

Status: Improved.

`backend/services/storage_service.py` validates:

- Max upload bytes.
- JPEG magic bytes.
- PNG magic bytes.
- WEBP magic bytes.
- Content type for storage upload.

Storage bucket:

- Production bucket is now `qc-evidence`.
- SQL migration generated at `supabase/migrations/003_storage_qc_evidence.sql`.

## Vercel Security Requirements

Set these in Vercel project settings:

- `JWT_SECRET_KEY`: strong random secret.
- `SUPABASE_URL`: project URL.
- `SUPABASE_SERVICE_ROLE_KEY`: backend only.
- `SUPABASE_STORAGE_BUCKET=qc-evidence`.
- `CORS_ORIGINS`: production origin only.
- `DEV_HTTP=false` or unset.
- `MAX_REQUEST_BYTES=10485760`.
- `MAX_UPLOAD_BYTES=5242880`.

Optional:

- `ALERT_WEBHOOK_URL`.
- `SUPABASE_ANON_KEY`, only if frontend direct Supabase access is enabled.

## Supabase Storage Policy Notes

Generated policies assume Supabase Auth JWT claims for `auth.uid()` and `auth.jwt()->>'role'`.

Important:

- Backend uploads using service-role key bypass RLS.
- Direct frontend uploads with anon key require Supabase authenticated users and folder paths beginning with `auth.uid()`.
- If the app keeps custom JWT auth only, production should prefer backend upload endpoints and not direct frontend Supabase uploads.

## Final Security Environment Score

Security env posture: 8/10.

Launch condition:

Ready after Vercel secrets are configured and Supabase migration is applied.
