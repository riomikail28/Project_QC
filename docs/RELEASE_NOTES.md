# Release Notes

Version: v1.0
Date: 2026-05-14

## Overview

QC Central Kitchen v1.0 is the first production release candidate for staff field QC operations and admin analytics.

## Features

- QC Monitoring
- Barcode Traceability
- Temperature Monitoring
- Staff Dashboard
- Admin Dashboard
- Approval System
- Analytics
- Facility monitoring structure
- Temperature alert feed
- QC finding upload flow
- Staff/admin role-based access
- Audit trail support

## Bug Fixes

- Added `/styles/<file>` static serving for redesigned frontend CSS.
- Added `/assets/<file>` static route for future production assets.
- Added `/check.html` alias to serve the QC inspection page.
- Fixed inspection page container mismatch for active batch rendering.
- Added dashboard alert drawer so alert review does not force page navigation.
- Added SVG/CSS icon fallbacks for navigation and dashboard cards.
- Added fallback data behavior for dashboard and monitoring when Supabase is empty/offline.

## QA Improvements

- Added pytest coverage for:
  - API health and validation
  - Authentication and roles
  - Dashboard aggregation
  - Monitoring logs
  - Frontend route aliasing
- Local test suite result: 30 passed.

## Performance Improvements

- Mobile-first CSS compaction for dashboard, monitoring, and QC pages.
- Reduced mobile header height.
- Added swipe chips for monitoring filters.
- Added responsive FAB sizing.
- Preserved fallback dashboard responses when database is offline.

## Known Issues

- Full Playwright visual regression was not run in the local environment.
- `pytest-cov` was listed in requirements but unavailable in the local Python environment used for this audit.
- Access tokens are stored in `localStorage`; future hardening should move to memory/cookie-backed session.
- Some dynamic frontend rendering still uses `innerHTML`; future hardening should sanitize or use DOM APIs.
- Production Supabase upload and realtime behavior require live credentials to validate end to end.
- Export PDF/Excel is visible as a roadmap/admin expectation but no backend export endpoint was confirmed in this audit.

## Upgrade Notes

Before production launch:

1. Configure Vercel secrets.
2. Apply Supabase migrations and policies.
3. Create staff/admin accounts.
4. Verify `/api/qc/health` with database status connected.
5. Run real-device staff UAT.
