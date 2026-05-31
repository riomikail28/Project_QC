# Database Schema Documentation

## 1. Overview

QC Enterprise uses Supabase PostgreSQL as the primary database for storing quality control, production, monitoring, learning, audit, and reporting data.

PostgreSQL provides relational structure, data integrity, query flexibility, and scalability for Central Kitchen quality control workflows. Supabase adds managed hosting, API access, authentication support, storage integration, and operational tooling that make the system easier to develop and maintain.

This document describes the main database entities, relationships, integrity rules, and future database improvement opportunities for GitHub documentation, thesis writing, and technical portfolio review.

## 2. Main Tables

### `users` / `staff_accounts`

Stores authenticated user or staff account data.

Common fields:

- `id`
- `name`
- `email`
- `username`
- `password_hash`
- `role`
- `is_active`
- `created_at`
- `updated_at`

Typical roles include `admin` and `staff`.

### `products`

Stores product master data used in batch production and QC inspection.

Common fields:

- `id`
- `sku`
- `product_name`
- `category`
- `standard_temperature`
- `is_active`
- `created_at`
- `updated_at`

### `production_batches`

Stores production batch records. One batch represents one cooking process.

Common fields:

- `id`
- `product_id`
- `production_date`
- `batch_sequence`
- `batch_code`
- `cook_name`
- `quantity`
- `production_shift`
- `created_by`
- `created_at`
- `updated_at`

### `qc_reports`

Stores QC inspection reports linked to production batches.

Common fields:

- `id`
- `batch_id`
- `inspector_id`
- `inspection_status`
- `inspection_round`
- `parent_inspection`
- `evidence_photo_url`
- `notes`
- `is_active`
- `completed_at`
- `created_at`
- `updated_at`

Supported inspection statuses are `PASS`, `HOLD`, and `FAIL`.

### `qc_findings`

Stores detailed findings or observations related to QC reports.

Common fields:

- `id`
- `qc_report_id`
- `finding_type`
- `description`
- `severity`
- `corrective_action`
- `created_at`
- `updated_at`

### `facility_logs`

Stores facility monitoring records, including room, device, schedule, and operational condition data.

Common fields:

- `id`
- `monitoring_date`
- `slot_time`
- `device_id`
- `room_id`
- `status`
- `notes`
- `submitted_by`
- `submitted_at`
- `is_late`
- `schedule_status`

### `temperature_logs`

Stores temperature readings from scheduled or manual monitoring.

Common fields:

- `id`
- `monitoring_date`
- `slot_time`
- `device_id`
- `room_id`
- `temperature`
- `status`
- `notes`
- `submitted_by`
- `submitted_at`
- `is_late`
- `schedule_status`

### `audit_logs`

Stores activity history for traceability and accountability.

Common fields:

- `id`
- `actor_id`
- `action`
- `entity`
- `entity_id`
- `metadata`
- `created_at`

### `itdv_modules`

Stores ITDV Learning module data.

Common fields:

- `id`
- `slug`
- `title`
- `description`
- `content`
- `order_index`
- `is_active`
- `deleted_at`
- `created_at`
- `updated_at`

### `itdv_module_mini_quizzes`

Stores mini quiz questions associated with learning modules.

Common fields:

- `id`
- `module_id`
- `question`
- `options`
- `correct_answer`
- `explanation`
- `order_index`
- `is_active`
- `deleted_at`
- `created_at`
- `updated_at`

### `itdv_quiz_questions`

Stores main quiz questions for ITDV Learning assessment.

Common fields:

- `id`
- `question`
- `options`
- `correct_answer`
- `category`
- `difficulty`
- `is_active`
- `deleted_at`
- `created_at`
- `updated_at`

### `itdv_simulations`

Stores learning simulation scenarios and expected answers.

Common fields:

- `id`
- `title`
- `scenario`
- `choices`
- `expected_answer`
- `feedback`
- `is_active`
- `deleted_at`
- `created_at`
- `updated_at`

### `itdv_certificates`

Stores certificate records generated after learning completion.

Common fields:

- `id`
- `user_id`
- `certificate_code`
- `issued_at`
- `score`
- `status`
- `metadata`
- `created_at`

## 3. Production Batch Schema

The production batch schema supports traceability for cooking activities.

In QC Enterprise:

- **Batch = 1 cooking process.**
- `batch_sequence` identifies the sequence number of the batch for a product or production date.
- `batch_code` is a unique human-readable batch identifier.
- `cook_name` records the person responsible for the cooking process.
- `quantity` records the production quantity.
- `production_shift` identifies the operating shift.

Recommended batch code format:

```text
SKU-YYYYMMDD-001
```

Example:

```text
SAUCE-20260531-001
```

Recommended fields:

```text
id
product_id
production_date
batch_sequence
batch_code
cook_name
quantity
production_shift
created_by
created_at
updated_at
```

The `batch_code` should be unique to prevent duplicate traceability records.

## 4. Monitoring Schema

The monitoring schema supports scheduled facility and temperature monitoring.

Core fields:

- `monitoring_date`: Date of monitoring activity.
- `slot_time`: Monitoring schedule slot, such as `07:00`, `13:00`, `16:00`, or `19:00`.
- `device_id`: Device or equipment being monitored.
- `room_id`: Room or area where the device is located.
- `temperature`: Recorded temperature value.
- `status`: Monitoring result or device status.
- `submitted_at`: Timestamp when the record was submitted.
- `is_late`: Indicates whether submission happened after the expected schedule.
- `schedule_status`: Tracks whether the monitoring slot is pending, completed, missed, or late.

Recommended fields:

```text
id
monitoring_date
slot_time
device_id
room_id
temperature
status
notes
submitted_by
submitted_at
is_late
schedule_status
created_at
updated_at
```

Monitoring records should prevent duplicate submissions for the same `monitoring_date`, `slot_time`, and `device_id`.

## 5. QC Inspection Schema

The QC inspection schema supports quality decisions, evidence, re-check, and history tracking.

Supported statuses:

- `PASS`
- `HOLD`
- `FAIL`

Core fields:

- `evidence_photo_url`: Stores a reference to uploaded evidence photo.
- `inspection_round`: Identifies the inspection attempt or re-check sequence.
- `parent_inspection`: Links a re-check record to its original inspection.
- `is_active`: Indicates the currently active inspection record.
- `completed_at`: Timestamp when the inspection was completed.

Recommended fields:

```text
id
batch_id
inspector_id
inspection_status
inspection_round
parent_inspection
evidence_photo_url
notes
is_active
completed_at
created_at
updated_at
```

Re-check history is represented by creating a new inspection record with a higher `inspection_round` and a `parent_inspection` reference to the original or previous inspection.

This approach preserves QC history instead of overwriting previous inspection decisions.

## 6. ITDV Learning Schema

The ITDV Learning schema supports structured learning, assessments, progress tracking, and certification.

Main learning components:

- Learning modules.
- Module mini quiz.
- Simulation.
- Main quiz.
- Progress.
- Certificates.

Recommended tables:

```text
itdv_modules
itdv_module_mini_quizzes
itdv_simulations
itdv_quiz_questions
itdv_certificates
```

Optional progress table:

```text
itdv_learning_progress
```

Recommended progress fields:

```text
id
user_id
module_id
status
score
completed_at
created_at
updated_at
```

This schema allows the system to track which modules users have opened, completed, passed, or certified.

## 7. Audit Trail Schema

The audit trail schema records important system actions for accountability and traceability.

Core fields:

- `actor_id`: User or staff account that performed the action.
- `action`: Activity name, such as `create`, `update`, `delete`, `export`, `login`, or `recheck`.
- `entity`: Affected resource, such as `batch`, `qc_report`, `temperature_log`, or `learning_module`.
- `entity_id`: Identifier of the affected record.
- `metadata`: JSON object containing contextual details.
- `created_at`: Timestamp of the activity.

Recommended fields:

```text
id
actor_id
action
entity
entity_id
metadata
created_at
```

Human-readable display mapping can transform audit data into user-friendly messages.

Example:

```text
actor_id + action + entity + metadata
= "Admin QC exported QC reports for 2026-05-31"
```

This makes audit history easier to review in admin dashboards, reports, and thesis documentation.

## 8. Google Sheets Export Data

Google Sheets export data should record what source data was exported and when.

Core concepts:

- `source_type`: Defines the exported data type, such as `monitoring_log` or `qc_report`.
- `source_id`: References the source record or export batch.
- `monitoring_log`: Exported monitoring or temperature record.
- `qc_report`: Exported QC inspection record.
- Historical re-export: Export operation for older records using date range or filter criteria.

Recommended export log fields:

```text
id
source_type
source_id
export_type
date_from
date_to
exported_by
exported_at
status
response_metadata
created_at
```

Export logs should be connected to `audit_logs` so admin export activity remains traceable.

## 9. Relationships

Main database relationships:

- `products` -> `production_batches`
- `production_batches` -> `qc_reports`
- `qc_reports` -> `qc_findings`
- `users` / `staff_accounts` -> `facility_logs`
- `users` / `staff_accounts` -> `temperature_logs`
- `users` / `staff_accounts` -> `qc_reports`
- `itdv_modules` -> `itdv_module_mini_quizzes`
- `users` / `staff_accounts` -> `itdv_certificates`
- `users` / `staff_accounts` -> `audit_logs`

Recommended foreign key examples:

```text
production_batches.product_id -> products.id
qc_reports.batch_id -> production_batches.id
qc_findings.qc_report_id -> qc_reports.id
temperature_logs.submitted_by -> users.id
facility_logs.submitted_by -> users.id
qc_reports.inspector_id -> users.id
itdv_module_mini_quizzes.module_id -> itdv_modules.id
itdv_certificates.user_id -> users.id
audit_logs.actor_id -> users.id
```

## 10. Data Integrity Rules

Recommended data integrity rules:

- `batch_code` must be unique.
- Monitoring duplicate prevention should enforce one record per `device_id`, `slot_time`, and `monitoring_date`.
- QC concurrency lock should prevent conflicting updates to the same active inspection record.
- Re-check records should preserve previous inspection history instead of overwriting it.
- Learning content should use soft delete through fields such as `is_active` and `deleted_at`.
- Admin-only CRUD should be enforced for staff management, product management, learning management, reports, and export configuration.
- Foreign key references should be used for products, batches, QC reports, users, and learning modules.
- Required operational fields should be validated before insert or update.

Example uniqueness constraints:

```text
UNIQUE (batch_code)
UNIQUE (monitoring_date, slot_time, device_id)
```

## 11. Migration Strategy

Database migrations should be production-safe and additive whenever possible.

Recommended migration principles:

- Prefer additive migrations, such as adding new tables, columns, indexes, or nullable fields.
- Do not delete old data during routine schema changes.
- Avoid destructive changes in production unless there is a tested rollback and backup plan.
- Use backfill scripts when adding required fields to existing tables.
- Add constraints only after existing data has been validated.
- Keep migration files documented and version-controlled.
- Test migrations in a staging or development database before applying them to production.

Production-safe changes reduce the risk of data loss and service disruption.

## 12. Future Database Improvements

Future database improvements can make QC Enterprise more scalable, automated, and suitable for enterprise deployment.

Potential improvements:

- Add `organization_id` for multi-tenant architecture.
- Add IoT sensor tables for automated temperature data collection.
- Add notification logs for WhatsApp, email, or in-app alerts.
- Add report snapshot tables for preserving generated report states.
- Add user permissions table for more granular access control.

Recommended future tables:

```text
organizations
iot_sensors
iot_temperature_readings
notification_logs
report_snapshots
user_permissions
```

These improvements would support future use cases such as multi-branch Central Kitchen operations, automated monitoring, AI anomaly detection, and enterprise-level reporting.
