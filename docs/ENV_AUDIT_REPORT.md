# Environment Audit Report

Date: 2026-05-14

## Scope

Audited backend, frontend, middleware, services, database clients, Vercel config, tests, and Supabase integration code for environment variable usage.

## Environment Variables Used

### Required For Production

| Variable | Used In | Purpose | Status |
|---|---|---|---|
| `JWT_SECRET_KEY` | `backend/middleware/security_middleware.py`, `backend/services/auth_service.py`, `backend/__init__.py` | JWT signing and verification | Required |
| `SUPABASE_URL` | `backend/database/supabase_client.py`, `backend/auth/staff_manager.py`, `backend/qc/parametric_checker.py` | Supabase REST/client URL | Required |
| `SUPABASE_SERVICE_ROLE_KEY` | `backend/database/supabase_client.py`, `backend/auth/staff_manager.py`, `backend/qc/parametric_checker.py` | Backend privileged Supabase access | Required backend only |
| `SUPABASE_STORAGE_BUCKET` | `backend/database/supabase_client.py`, `backend/services/ccp_service.py` | Evidence bucket name | Required, default `qc-evidence` |
| `FLASK_ENV` | Deployment convention | Production mode marker | Required for Vercel env hygiene |
| `ALERT_WEBHOOK_URL` | `backend/qc/parametric_checker.py` | Optional maintenance alert webhook | Required by launch checklist, can be empty only if alerts are disabled |
| `CORS_ORIGINS` | `backend/__init__.py` | Restrict browser origins | Required |

### Optional / Conditional

| Variable | Used In | Purpose | Status |
|---|---|---|---|
| `SUPABASE_KEY` | `backend/database/supabase_client.py`, `backend/auth/staff_manager.py`, tests | Fallback key, usually anon key | Optional fallback |
| `SUPABASE_ANON_KEY` | `.env.example`, `frontend/js/camera-module.js` via `window.QC_CONFIG` | Public frontend storage upload if enabled | Optional public only |
| `DATABASE_URL` | `.env.example` | Reserved for future DB integration | Not used currently |
| `GCP_PROJECT_ID` | `.env.example` | Reserved for GCP/OCR integration | Not used currently |
| `GOOGLE_APPLICATION_CREDENTIALS` | `.env.example` | Reserved for GCP/OCR credentials | Not used currently |
| `JWT_ISSUER` | security/auth services | JWT issuer | Optional, default `qc-traceability-api` |
| `JWT_ACCESS_TOKEN_MINUTES` | security middleware | Access token lifetime | Optional, default `480` |
| `REFRESH_TOKEN_DAYS` | auth routes/service | Refresh token lifetime | Optional, default `14` |
| `REFRESH_TOKEN_COOKIE` | auth routes | Refresh cookie name | Optional, default `refresh_token` |
| `DEV_HTTP` | auth routes | Allows non-secure refresh cookie for local dev | Must be false/empty in production |
| `MAX_REQUEST_BYTES` | security middleware | Request size cap | Optional, default 10MB |
| `MAX_UPLOAD_BYTES` | storage service | Upload size cap | Optional, default 5MB |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | security middleware | Login rate limit | Optional, default 5 |
| `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | security middleware | Login rate window | Optional, default 900 |
| `VERCEL` | backend upload/static behavior | Vercel runtime detection | Auto-set by Vercel |
| `VERCEL_ORG_ID` | GitHub Actions | Vercel deployment | Required in GitHub secrets for deploy |
| `VERCEL_PROJECT_ID` | GitHub Actions | Vercel deployment | Required in GitHub secrets for deploy |
| `VERCEL_TOKEN` | GitHub Actions | Vercel deployment | Required in GitHub secrets for deploy |

## Environment Variables Missing From Previous Example

Added to `.env.example`:

- `SUPABASE_ANON_KEY`
- `ALERT_WEBHOOK_URL`
- `DATABASE_URL`
- `GCP_PROJECT_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`

## Environment Variables Not Used

- `DATABASE_URL`: not used by current code. Keep only if future non-Supabase DB is planned.
- `GCP_PROJECT_ID`: not used by current code. Keep only if OCR/GCP is reintroduced.
- `GOOGLE_APPLICATION_CREDENTIALS`: not used by current code. Keep only if OCR/GCP is reintroduced.
- `FLASK_ENV`: not read directly by Flask app code, but useful as deployment marker.

## Duplicate / Alias Variables

- `SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_KEY`
  - Backend prefers `SUPABASE_SERVICE_ROLE_KEY`.
  - `SUPABASE_KEY` is fallback only.
  - Production should use service-role key only on backend.
- `JWT_SECRET_KEY` and `SECRET_KEY`
  - Security middleware supports both.
  - Production should use `JWT_SECRET_KEY`.

## Dangerous Environment Patterns

- `SUPABASE_SERVICE_ROLE_KEY` must never be exposed to frontend or `window.QC_CONFIG`.
- `DEV_HTTP=true` must never be used in production.
- Missing `JWT_SECRET_KEY` triggers fallback signing secret and is not acceptable for production.
- Broad `CORS_ORIGINS` should be avoided in production.

## Required Vercel Environment

Minimum:

- `JWT_SECRET_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET=qc-evidence`
- `FLASK_ENV=production`
- `ALERT_WEBHOOK_URL`
- `GCP_PROJECT_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`

Conditional:

- `DATABASE_URL` if non-Supabase DB is added.
- `SUPABASE_ANON_KEY` only if public frontend Supabase access is intentionally enabled.

## Audit Decision

Environment configuration is ready after Vercel secrets are populated and Supabase bucket migration `003_storage_qc_evidence.sql` is applied.
