# Security Report

Date: 2026-05-14

## Scope

Security checks covered:

- Authentication and authorization
- JWT/session handling
- Role boundaries
- SQL injection posture
- XSS posture
- CSRF posture
- Secret exposure
- Supabase key exposure
- File upload validation

## Results

### Authentication

Status: Pass with hardening notes.

- Login is validated through `LoginRequest`.
- JWT auth is enforced on protected API routes.
- Admin-only routes use `require_role("admin")`.
- Staff users are denied admin analytics in tests.
- Logout invalidates refresh token when present and revokes access token JTI.

### Session / JWT

Status: Pass with production ENV requirement.

- Refresh token is stored as HttpOnly cookie.
- Access token is returned to frontend and stored in `localStorage`.
- Production must set `JWT_SECRET_KEY`; fallback secret warning appears if missing.

Risk:

- `localStorage` token storage increases exposure if XSS occurs.

Recommendation:

- Move access token to memory or short-lived cookie-backed session in a future hardening sprint.

### Role Access

Status: Pass.

- Admin APIs return 403 for staff token.
- Staff list requires admin role.

### SQL Injection

Status: Pass.

- Supabase client/query builder is used instead of raw SQL for runtime APIs.
- Inputs are validated before database calls in key routes.

### XSS

Status: Medium residual risk.

- Multiple frontend render paths use `innerHTML` for API data.
- No `eval()` usage was found.

Recommendation:

- Add a small HTML escape helper for all dynamic string rendering.
- Prefer `textContent` and DOM node creation for untrusted API fields.

### CSRF

Status: Medium residual risk.

- API mutations rely primarily on bearer token auth.
- Refresh cookie is `HttpOnly`, `Secure` in non-dev, and `SameSite=Lax`.
- No explicit CSRF token exists for cookie-backed endpoints.

Recommendation:

- Add CSRF token for refresh/logout or enforce same-origin checks.

### Secret Exposure

Status: Pass with repository hygiene note.

- `.env` is ignored by `.gitignore`.
- No real Supabase service-role key was found in tracked source during scan.
- Test placeholders exist in tests and config only.

### Supabase Key

Status: Pass with caution.

- Backend uses `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_KEY` from env.
- Frontend camera module can use `window.QC_CONFIG.supabaseAnonKey`.

Recommendation:

- Use anon key only on frontend.
- Never expose service-role key in `window.QC_CONFIG`.

### File Upload Validation

Status: Needs hardening.

- Upload endpoints accept photo files and use storage helpers.
- MIME type, extension allowlist, and max file size should be enforced before production scale.

Recommendation:

- Add server-side allowlist: JPEG, PNG, WEBP.
- Enforce max upload size, e.g. 5MB.
- Normalize filenames with `secure_filename`.

## Security Test Summary

| Check | Result |
|---|---:|
| Broken auth | Pass |
| Role bypass | Pass |
| SQL injection posture | Pass |
| XSS posture | Needs hardening |
| CSRF posture | Needs hardening |
| Token exposure | Needs hardening |
| Secret scan | Pass |
| File upload validation | Needs hardening |

## Launch Risk

No critical blocker was found for a controlled launch. Recommended launch mode: limited production rollout with monitoring and a follow-up security hardening sprint.
