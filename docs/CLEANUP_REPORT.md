# Cleanup Report

Date: 2026-05-14

## Summary

Project structure was audited for production launch. Cleanup was intentionally conservative because several legacy CSS/JS files are still referenced by older staff pages (`new_batch.html`, `batch_detail.html`, `ccp_stage.html`, login, and admin legacy helpers). No destructive deletion was performed without a confirmed dead reference.

## Files Deleted

None.

Reason: no zero-byte frontend assets were found, and no workflow was confirmed deprecated. Existing `.github/workflows/ci-cd-production.yml` is active and production-oriented.

## Files Moved

None.

Reason: existing Vercel/Flask static routes depend on current `/frontend/css`, `/frontend/js`, `/frontend/styles`, `/frontend/staff`, and `/frontend/admin` paths.

## Files Added

- `tests/conftest.py`
- `tests/test_api.py`
- `tests/test_auth.py`
- `tests/test_dashboard.py`
- `tests/test_monitoring.py`
- `docs/CLEANUP_REPORT.md`
- `docs/FRONTEND_QA_REPORT.md`
- `docs/SECURITY_REPORT.md`
- `docs/PRODUCTION_CHECKLIST.md`
- `docs/RELEASE_NOTES.md`

## Files Updated

- `backend/__init__.py`
  - Added `/check.html` alias to serve `inspection.html`, preventing broken UAT route.
- `requirements.txt`
  - Added dependencies used by imported modules.

## Dependency Changes

### Dependencies Added

- `pydantic==2.7.4`
  - Required by `backend/core/response.py` and `backend/core/enterprise_response.py`.
- `httpx==0.27.0`
  - Required by `backend/qc/parametric_checker.py`.

### Dependencies Removed

None.

Reason: all existing dependencies are either directly imported, required for production serving, or required by CI/test tooling.

## Active Dependencies

- `Flask`
- `Flask-CORS`
- `Werkzeug`
- `supabase`
- `PyJWT`
- `python-dotenv`
- `prometheus_client`
- `gunicorn`
- `python-multipart`
- `pydantic`
- `httpx`
- `pytest`
- `pytest-cov`

## CSS/JS Audit

### Active CSS

- `frontend/styles/*.css`: active enterprise staff UI design system.
- `frontend/css/admin_enterprise.css`: active admin panel stylesheet.
- `frontend/css/login.css`, `dashboard.css`, `new_batch.css`, `monitoring.css`, `inspection.css`, `mobile.css`, `admin_panel.css`: retained because legacy/current pages still reference them.

### Active JS

- `api.js`, `auth.js`, `dashboard.js`, `monitoring.js`, `inspection.js`, `admin_app.js`: active core frontend logic.
- `admin_panel.js`, `ccp.js`, `camera-module.js`, `mobile-nav.js`, `ui-mobile.js`, `temp-monitor.js`, `performance-optimized.js`, `alerts.js`: retained due existing page references or reusable functionality.

## Cleanup Decision

No file deletion was performed in this release pass. The project is now safer for production because tests and route aliasing were added without destabilizing legacy pages.
