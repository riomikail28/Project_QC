# QA Execution Report

Date: 2026-05-14

## Automated Backend QA

Command:

```bash
py -3 -m pytest -q
```

Result:

```text
30 passed, 1 warning
```

Covered:

- Public health endpoint.
- Auth login validation.
- Refresh/logout flow.
- Admin/staff role boundaries.
- Dashboard API fallback and aggregation.
- Monitoring latest/log validation.
- QC validation malformed and unknown payloads.
- Product fallback.
- Admin analytics authorization.
- Static frontend route serving.
- `/check.html` alias.

## Coverage

Target: >85%.

Status: Tooling blocked locally.

Reason:

`pytest-cov` is listed in `requirements.txt`, but the active local Python environment did not have the plugin installed, so `--cov=backend` was rejected by pytest.

Action:

- Kept `pytest-cov==4.1.0` in `requirements.txt`.
- CI installs from `requirements.txt`, so coverage command can be enabled in GitHub Actions after dependency installation.

## Frontend Static QA

Verified 200 responses:

- `/dashboard.html`
- `/monitoring.html`
- `/profile.html`
- `/inspection.html`
- `/check.html`
- `/alerts.html`
- `/admin/`
- `/admin/admin_panel.html`
- Staff CSS/JS
- Admin CSS/JS

## Functional Staff Test

Automated partial validation:

- Login endpoint covered by tests.
- Dashboard endpoint covered by tests.
- Monitoring log validation and save path covered with fake Supabase.
- Product list fallback covered.
- Logout covered by existing auth flow test.

Requires production Supabase credentials:

- Actual photo upload.
- Actual batch persistence.
- Actual realtime updates.

## Functional Admin Test

Automated partial validation:

- Admin analytics route covered.
- Staff is denied admin route.
- Admin panel static route served.

Requires production Supabase credentials:

- Staff report data.
- Approval queue mutations.
- Evidence image preview.
- Barcode traceability data.
- Temperature chart live data.
- Export PDF/Excel; no concrete export endpoint confirmed.

## Performance Test

Local Flask test client sequential load:

| Load | Endpoint | Avg | P95 | Status |
|---:|---|---:|---:|---|
| 10 | `/api/qc/health` | 2.37ms | 5.64ms | 200 |
| 10 | `/api/qc/dashboard` | 1.86ms | 4.64ms | 200 |
| 10 | `/api/products` | 0.99ms | 1.16ms | 200 |
| 10 | `/dashboard.html` | 9.34ms | 121.68ms | 200 |
| 50 | `/api/qc/health` | 1.79ms | 4.97ms | 200 |
| 50 | `/api/qc/dashboard` | 1.08ms | 1.75ms | 200 |
| 50 | `/api/products` | 2.18ms | 9.03ms | 200 |
| 50 | `/dashboard.html` | 1.00ms | 1.57ms | 200 |
| 100 | `/api/qc/health` | 1.00ms | 1.56ms | 200 |
| 100 | `/api/qc/dashboard` | 0.99ms | 1.34ms | 200 |
| 100 | `/api/products` | 1.10ms | 1.76ms | 200 |
| 100 | `/dashboard.html` | 0.86ms | 1.28ms | 200 |

Targets:

- Dashboard <2s: Pass locally.
- API <500ms: Pass locally.

Note:

This is not a distributed load test. It validates Flask route latency locally without production Supabase/network latency.

## Launch Decision

Backend: 8/10

Frontend: 8/10

Security: 7/10

Performance: 8/10

Production Ready: 8/10

Decision:

Ready for controlled production launch after Vercel/Supabase environment checklist is completed.
