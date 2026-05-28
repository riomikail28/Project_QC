# API Reference

## 1. Overview

This document describes the main API endpoints used by QC Enterprise, a web-based Quality Control system for Central Kitchen operations.

The API supports authentication, role-based access, staff workflows, monitoring, batch production, QC inspection, reports, Google Sheets export, auditability, and ITDV Learning management.

This reference is intended for GitHub documentation, thesis writing, portfolio review, and future development planning.

## 2. Authentication

QC Enterprise uses authenticated API access with role-based authorization.

### Login

Users authenticate through the login endpoint. After successful login, the backend identifies the user account and role.

### Role Admin

Admin users can access management and reporting features, including:

- Admin dashboard.
- Reports.
- Staff management.
- Product management.
- Audit trail.
- Google Sheets export.
- Learning ITDV CRUD management.

### Role Staff

Staff users can access operational workflows, including:

- Mobile dashboard.
- Profile.
- Temperature monitoring.
- Batch input.
- QC check.
- Learning modules.

### Protected Endpoint

Protected endpoints require a valid authenticated session or token. Requests without valid authentication should return `401 Unauthorized`.

### Admin-Only Endpoint

Admin-only endpoints require both authentication and the `admin` role. Authenticated staff users attempting to access admin-only endpoints should receive `403 Forbidden`.

## 3. Auth API

### POST `/api/auth/login`

Authenticates a user and starts an authenticated session.

Example request:

```json
{
  "username": "admin",
  "password": "secure_password"
}
```

Example response:

```json
{
  "success": true,
  "user": {
    "id": "user_001",
    "name": "Admin QC",
    "role": "admin"
  }
}
```

### POST `/api/auth/logout`

Ends the current authenticated session.

Example response:

```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

### GET `/api/auth/me`

Returns the currently authenticated user.

Example response:

```json
{
  "id": "user_001",
  "name": "Admin QC",
  "role": "admin"
}
```

## 4. Staff API

### Staff Dashboard

Staff dashboard endpoints provide mobile-friendly operational summaries for monitoring, QC checks, and daily tasks.

Common route pattern:

```text
GET /api/staff/dashboard
```

### Staff Profile

Profile endpoints provide staff identity, role, and account information.

Common route pattern:

```text
GET /api/staff/profile
PUT /api/staff/profile
```

## 5. Monitoring API

Monitoring endpoints support scheduled temperature and facility checks.

### GET `/api/facility/monitoring/schedule/today`

Returns today's monitoring schedule, including available slots such as 07:00, 13:00, 16:00, and 19:00.

### POST `/api/facility/monitoring/submit`

Submits a scheduled monitoring record.

Required or commonly used payload fields:

- `device_id`
- `room_id`
- `temperature`
- `slot_time`
- `monitoring_date`
- `notes`

Example request:

```json
{
  "device_id": "device_001",
  "room_id": "room_chiller",
  "temperature": 3.8,
  "slot_time": "07:00",
  "monitoring_date": "2026-05-29",
  "notes": "Temperature stable"
}
```

### GET `/api/temperature/logs`

Returns temperature monitoring logs. This endpoint can be used for monitoring history, reports, or device-based review.

### POST `/api/temperature/logs`

Creates a temperature log entry.

Example request:

```json
{
  "device_id": "device_001",
  "room_id": "room_chiller",
  "temperature": 3.8,
  "slot_time": "07:00",
  "monitoring_date": "2026-05-29",
  "notes": "Manual temperature log"
}
```

## 6. Batch API

Batch endpoints manage production batch records.

### GET `/api/batch/next-code`

Generates or returns the next available batch code.

Recommended batch code format:

```text
SKU-YYYYMMDD-001
```

### POST `/api/batch`

Creates a new batch production record.

Required or commonly used payload fields:

- `product_id`
- `production_date`
- `batch_sequence`
- `batch_code`
- `cook_name`
- `quantity`
- `production_shift`

Example request:

```json
{
  "product_id": "SKU-CKN",
  "production_date": "2026-05-29",
  "batch_sequence": 1,
  "batch_code": "SKU-CKN-20260529-001",
  "cook_name": "Budi",
  "quantity": 120,
  "production_shift": "morning"
}
```

### GET `/api/batch`

Returns batch records. This endpoint can support filters such as production date, product, or shift.

### GET `/api/batch/<id>`

Returns detail for a specific batch record.

## 7. QC Inspection API

QC inspection endpoints manage quality decisions, evidence, and re-check history.

### POST `/api/qc/submit`

Submits a QC inspection result.

Supported statuses:

- `PASS`
- `HOLD`
- `FAIL`

Supported workflow concepts:

- Evidence photo upload.
- Re-check.
- `inspection_round`.
- `parent_inspection`.

Example request:

```json
{
  "batch_id": "batch_001",
  "inspection_status": "HOLD",
  "inspection_round": 1,
  "parent_inspection": null,
  "notes": "Texture requires re-check after cooling",
  "evidence_photo": "https://example.com/uploads/qc-evidence-001.jpg"
}
```

### GET `/api/qc/active`

Returns active QC inspections, including items requiring review or re-check.

### GET `/api/qc/history/<batch>`

Returns QC inspection history for a selected batch, including re-check records and parent-child inspection relationships.

## 8. Admin API

Admin endpoints support management, supervision, reporting, and integration workflows.

Main admin API categories:

- Admin reports.
- Audit trail.
- Staff management.
- Product management.
- Google Sheets export.
- Learning ITDV CRUD.

Common route patterns:

```text
GET /api/admin/dashboard
GET /api/admin/audit-trail
GET /api/admin/staff
POST /api/admin/staff
PUT /api/admin/staff/<id>
DELETE /api/admin/staff/<id>
GET /api/admin/products
POST /api/admin/products
PUT /api/admin/products/<id>
DELETE /api/admin/products/<id>
```

All admin endpoints should require authenticated admin access.

## 9. Reports API

Reports endpoints provide operational summaries, monitoring review, QC review, batch analysis, and alert visibility.

### GET `/api/admin/reports/summary`

Returns high-level report summary metrics.

### GET `/api/admin/reports/monitoring`

Returns monitoring report data, including device, room, temperature, schedule slot, and date-based records.

### GET `/api/admin/reports/qc`

Returns QC inspection report data, including PASS, HOLD, FAIL, evidence, and re-check information.

### GET `/api/admin/reports/batches`

Returns batch production report data.

### GET `/api/admin/reports/alerts`

Returns alert-related report data, such as HOLD, FAIL, missed monitoring, or unresolved follow-up items.

## 10. Google Sheets API

Google Sheets endpoints support integration with Google Apps Script and external spreadsheet export.

### GET `/api/admin/google-sheets/status`

Returns Google Sheets integration status.

### POST `/api/admin/google-sheets/test`

Sends a test payload to the Google Apps Script webhook.

### POST `/api/admin/google-sheets/export/monitoring`

Exports monitoring records to Google Sheets.

### POST `/api/admin/google-sheets/export/qc`

Exports QC inspection records to Google Sheets.

All Google Sheets endpoints should be admin-only because they may expose operational records outside the main system.

## 11. Learning ITDV API

Learning ITDV endpoints support staff learning, quizzes, simulations, progress tracking, and certificate generation.

### GET `/api/learning/modules`

Returns available learning modules.

### GET `/api/learning/modules/<slug>`

Returns detail for a selected learning module.

### POST `/api/learning/modules/<slug>/mini-quiz`

Submits a mini quiz answer for a module.

### POST `/api/learning/modules/<slug>/complete`

Marks a module as completed.

### GET `/api/learning/progress`

Returns learning progress for the authenticated user.

### GET `/api/learning/simulations`

Returns available simulations.

### POST `/api/learning/simulations/<id>/submit`

Submits simulation results.

### GET `/api/learning/quizzes`

Returns available quizzes.

### POST `/api/learning/quizzes/<id>/submit`

Submits quiz answers.

### POST `/api/learning/certificate`

Generates or requests a learning certificate after completion requirements are met.

## 12. Admin Learning CRUD API

Admin Learning CRUD endpoints allow admin users to manage learning content.

### Modules

```text
GET /api/admin/learning/modules
POST /api/admin/learning/modules
PUT /api/admin/learning/modules/<id>
DELETE /api/admin/learning/modules/<id>
```

### Module Mini Quiz

```text
GET /api/admin/learning/modules/<id>/mini-quiz
POST /api/admin/learning/modules/<id>/mini-quiz
PUT /api/admin/learning/mini-quiz/<id>
DELETE /api/admin/learning/mini-quiz/<id>
```

### Simulations

```text
GET /api/admin/learning/simulations
POST /api/admin/learning/simulations
PUT /api/admin/learning/simulations/<id>
DELETE /api/admin/learning/simulations/<id>
```

### Quizzes

```text
GET /api/admin/learning/quizzes
POST /api/admin/learning/quizzes
PUT /api/admin/learning/quizzes/<id>
DELETE /api/admin/learning/quizzes/<id>
```

### Learning Progress

```text
GET /api/admin/learning/progress
```

## 13. Error Response Format

The API should return consistent JSON error responses.

Recommended format:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Required field is missing",
    "details": {
      "field": "device_id"
    }
  }
}
```

### 400 Validation Error

Returned when the request payload is invalid or required fields are missing.

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid monitoring payload"
  }
}
```

### 401 Unauthorized

Returned when the user is not authenticated.

```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication is required"
  }
}
```

### 403 Forbidden

Returned when the authenticated user does not have permission.

```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "Admin access is required"
  }
}
```

### 404 Not Found

Returned when the requested resource does not exist.

```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found"
  }
}
```

### 409 Conflict

Returned when the request conflicts with existing data, such as duplicate monitoring for the same device and slot.

```json
{
  "success": false,
  "error": {
    "code": "CONFLICT",
    "message": "Monitoring record already exists for this device and slot"
  }
}
```

### 500 Server Error

Returned when an unexpected server error occurs.

```json
{
  "success": false,
  "error": {
    "code": "SERVER_ERROR",
    "message": "Internal server error"
  }
}
```

## 14. Example Payloads

### Monitoring Submit

```json
{
  "device_id": "device_freezer_01",
  "room_id": "room_frozen_storage",
  "temperature": -18.5,
  "slot_time": "13:00",
  "monitoring_date": "2026-05-29",
  "notes": "Freezer temperature within standard range"
}
```

### Batch Create

```json
{
  "product_id": "SKU-SAUCE",
  "production_date": "2026-05-29",
  "batch_sequence": 1,
  "batch_code": "SKU-SAUCE-20260529-001",
  "cook_name": "Siti",
  "quantity": 80,
  "production_shift": "afternoon"
}
```

### QC Submit

```json
{
  "batch_id": "batch_20260529_001",
  "inspection_status": "PASS",
  "inspection_round": 1,
  "parent_inspection": null,
  "evidence_photo": "https://example.com/uploads/qc-pass-001.jpg",
  "notes": "Color, texture, aroma, and temperature meet QC standard"
}
```

### Google Sheets Test Export

```json
{
  "target": "monitoring",
  "test_mode": true,
  "sample": {
    "device_id": "device_chiller_01",
    "temperature": 4.2,
    "slot_time": "16:00",
    "monitoring_date": "2026-05-29"
  }
}
```

### Module Complete

```json
{
  "module_slug": "haccp-basic-principles",
  "completed": true,
  "score": 90,
  "completed_at": "2026-05-29T10:30:00+07:00"
}
```

## 15. Notes

- Endpoint paths and payload fields may change as the project evolves.
- Do not expose secrets, service keys, database credentials, or webhook secrets in frontend code.
- Use environment variables for API keys, Supabase configuration, Google Apps Script webhook URLs, and deployment secrets.
- Authorization must be validated on the backend, even when the frontend hides protected UI elements.
- API documentation should be updated whenever routes, payloads, role access, or integration behavior changes.
