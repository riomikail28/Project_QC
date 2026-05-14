# Production Checklist

Version: v1.0
Date: 2026-05-14

## Environment

- [ ] `JWT_SECRET_KEY` configured in Vercel.
- [ ] `SUPABASE_URL` configured in Vercel.
- [ ] `SUPABASE_SERVICE_ROLE_KEY` configured in Vercel backend environment.
- [ ] `SUPABASE_KEY` configured only if required as fallback.
- [ ] `SUPABASE_STORAGE_BUCKET=qc-evidence` configured.
- [ ] `CORS_ORIGINS` restricted to production domains.
- [ ] `DEV_HTTP=false` in production.
- [ ] `.env` not committed.

## Vercel

- [x] `vercel.json` points all traffic to `api/app.py`.
- [x] Flask serves staff/admin static HTML.
- [x] Flask serves `/css`, `/styles`, `/js`, `/assets`.
- [x] `/check.html` alias serves inspection page.
- [ ] Production deployment verified from Vercel dashboard.

## Supabase

- [ ] Production schema migrations applied.
- [ ] RLS policies applied.
- [ ] Demo seed reviewed before production use.
- [ ] Storage bucket exists.
- [ ] Upload permissions tested.
- [ ] Staff/admin accounts created.

## GitHub Actions

- [x] Production CI/CD workflow exists.
- [x] Python syntax validation configured.
- [x] Pytest configured.
- [x] Vercel deployment job configured.
- [ ] GitHub secrets configured:
  - `VERCEL_ORG_ID`
  - `VERCEL_PROJECT_ID`
  - `VERCEL_TOKEN`

## Build / Test

- [x] `py -3 -m compileall -q backend api` passed locally.
- [x] `py -3 -m pytest -q` passed locally: 30 passed.
- [ ] `pytest-cov` available in CI and coverage report generated.
- [ ] Coverage threshold enforced in CI.

## Health Endpoint

- [x] `/api/qc/health` returns 200 locally.
- [ ] `/api/qc/health` returns 200 in production.
- [ ] Database status shows connected in production.

## Monitoring

- [ ] Vercel function logs reviewed.
- [ ] Supabase logs reviewed.
- [ ] Error tracking configured.
- [ ] Admin audit trail verified.
- [ ] Performance logs monitored after launch.

## Functional Staff UAT

- [ ] Staff login.
- [ ] Dashboard loads with real data.
- [ ] Monitoring rooms/devices load.
- [ ] Temperature log saves to Supabase.
- [ ] Photo upload saves to Supabase Storage.
- [ ] Batch creation works.
- [ ] QC submission works.
- [ ] Logout works.

## Functional Admin UAT

- [ ] Admin login.
- [ ] Analytics dashboard loads.
- [ ] Staff reports visible.
- [ ] Approval queue visible.
- [ ] Evidence photo preview works.
- [ ] Barcode traceability works.
- [ ] Temperature graph works.
- [ ] Filters work.
- [ ] Audit trail records actions.

## Launch Decision Gate

Launch is approved when all unchecked ENV/Supabase/Vercel items are completed in production.
