# Testing Guide

## 1. Overview

Testing in QC Enterprise is used to maintain system stability, prevent regression, and ensure that critical Quality Control workflows continue to work correctly after changes.

Because QC Enterprise supports Central Kitchen operations, testing should focus on authentication, role-based access, monitoring, batch production, QC inspection, reporting, audit trail, learning, and external Google Sheets export. A reliable testing process helps protect operational data quality and improves confidence before deployment.

This guide is intended for GitHub documentation, thesis support, portfolio review, and production readiness.

## 2. Test Stack

QC Enterprise uses a practical testing stack that combines automated and manual validation.

- **Pytest:** Backend unit, integration, route, and regression tests.
- **JavaScript syntax check:** Static syntax validation for frontend JavaScript files.
- **Smoke route test:** Basic route checks to confirm important pages and APIs respond.
- **Manual browser test:** Human verification for UI, role behavior, uploads, mobile layout, and PWA behavior.
- **Production checklist:** Final deployment validation for environment variables, external services, and integration readiness.

## 3. How to Run Tests

Run backend tests with:

```bash
py -m pytest
```

Alternative Python command:

```bash
python -m pytest
```

Run JavaScript syntax checks with:

```bash
node --check frontend/js/admin_app.js
node --check frontend/js/monitoring.js
node --check frontend/js/inspection.js
```

Recommended full local validation:

```bash
py -m pytest
node --check frontend/js/admin_app.js
node --check frontend/js/monitoring.js
node --check frontend/js/inspection.js
```

## 4. Test Coverage Area

Testing should cover the following system areas:

- Auth.
- Role redirect.
- Admin dashboard.
- Staff dashboard.
- Monitoring schedule.
- Batch production.
- QC inspection.
- Re-check.
- Reports.
- Audit trail.
- Google Sheets export.
- ITDV Learning.
- Profile dropdown.
- PWA manifest.

These areas represent the main workflows that users interact with and the most important operational behavior in QC Enterprise.

## 5. Critical Regression Tests

Critical regression tests should verify behavior that must not break during future development.

### Role and Access Control

- Staff users must not be able to access admin endpoints.
- Admin users must be able to access admin endpoints.
- Protected endpoints must reject unauthenticated requests.

### Monitoring

- Monitoring schedule must support per-device checks.
- Monitoring slots should support 07:00, 13:00, 16:00, and 19:00.
- Duplicate monitoring prevention must reject repeated submissions for the same device, slot, and date.
- Monitoring progress should calculate against total device x slot requirements.

### Batch Production

- Batch code sequence must generate correctly.
- Batch code should follow the format `SKU-YYYYMMDD-001`.
- Duplicate batch codes should be rejected.

### QC Inspection

- QC status must support `PASS`, `HOLD`, and `FAIL`.
- QC concurrency lock must prevent conflicting updates.
- Re-check records must preserve inspection history.
- Evidence photo references must be stored correctly.

### ITDV Learning

- Mini quiz gating must prevent module completion when requirements are not met.
- Certificate locked logic must prevent certificate generation before completion criteria are satisfied.
- Learning progress should update after module, quiz, or simulation completion.

### Google Sheets Export

- Google Sheets webhook failure must not cause the main submit workflow to fail.
- Export failure should be logged or reported clearly.
- Historical export should respect selected filters or date ranges.

## 6. Manual QA Checklist

Use this checklist before demo, release, thesis presentation, or portfolio review.

### Admin

- [ ] Login works.
- [ ] Dashboard loads correctly.
- [ ] Reports page displays expected data.
- [ ] Audit trail shows recent system activities.
- [ ] Learning CRUD can create, update, and disable learning content.
- [ ] Google Sheets export can send test and real export data.

### Staff

- [ ] Login works.
- [ ] Dashboard loads correctly on mobile layout.
- [ ] Monitoring can be submitted for the correct schedule slot.
- [ ] QC check can be submitted with valid status.
- [ ] New batch can be created.
- [ ] Photo upload works for QC evidence.
- [ ] Profile page or dropdown displays correct user information.

### PWA

- [ ] Add to home screen is available on supported devices.
- [ ] Standalone mode opens without browser chrome when installed.
- [ ] Mobile navigation works.
- [ ] FAB is visible and usable on mobile screens.

## 7. Production Testing Checklist

Before production deployment, verify:

- [ ] Environment variables are configured.
- [ ] Supabase migrations are applied.
- [ ] Demo account is available and tested.
- [ ] Vercel deployment completes successfully.
- [ ] Google Apps Script URL is configured.
- [ ] Google Sheets export works from production.
- [ ] Service worker is registered correctly.
- [ ] Manifest file is available and valid.

## 8. Known Risks

Known risks that should be checked during testing:

- **Google Apps Script permission:** Export can fail if the script is not deployed correctly or permission is not granted.
- **Timezone Asia/Jakarta:** Monitoring date, schedule slot, and late status must use the correct timezone.
- **Duplicate batch:** Batch code generation must prevent repeated batch codes.
- **Device monitoring schedule:** Each device must map correctly to the required monitoring slots.
- **Uploaded photo storage:** Evidence upload must store and retrieve photo references reliably.
- **PWA cache:** Cached frontend assets may cause users to see outdated behavior after deployment.

## 9. Bug Report Template

Use this format when reporting bugs.

```markdown
## Title

Short description of the issue.

## Environment

- Local / Staging / Production:
- Browser:
- Device:
- Date and time:

## Role

- Admin / Staff:

## Steps to Reproduce

1. Open ...
2. Click ...
3. Submit ...

## Expected Result

Describe what should happen.

## Actual Result

Describe what actually happened.

## Screenshot

Attach screenshot or screen recording if available.

## Logs

Paste relevant backend, frontend console, Vercel, Supabase, or Google Apps Script logs.
```

## 10. Release Checklist

Before releasing a new version, confirm:

- [ ] All tests passed.
- [ ] Migration applied.
- [ ] README updated.
- [ ] Demo account checked.
- [ ] Production smoke test done.

The release should only proceed after critical workflows have been verified for both Admin and Staff roles.
