# Project Architecture

## 1. Overview

QC Enterprise is a web-based Quality Control system designed for Central Kitchen operations. The system supports structured monitoring, batch production tracking, QC inspection, reporting, learning management, and Google Sheets export.

The architecture is designed to separate user interface, backend processing, database storage, and external reporting integration. This makes the project suitable for operational use, academic documentation, portfolio review, and future AI automation development.

## 2. System Architecture

QC Enterprise uses a web application architecture with the following components:

- **Frontend:** HTML, CSS, and JavaScript.
- **Backend:** Python Flask.
- **Database:** Supabase PostgreSQL.
- **Deployment:** Vercel.
- **Integration:** Google Apps Script and Google Sheets.
- **PWA Support:** Progressive Web App support for mobile-friendly access and installable app behavior.

The frontend handles user interaction, form submission, dashboard views, and mobile workflows. The Flask backend provides API routes, validation, business logic, role-based access control, and integration handling. Supabase PostgreSQL stores operational data such as users, monitoring records, QC inspections, batch sequences, reports, and learning data. Google Apps Script acts as a webhook bridge for exporting system data to Google Sheets.

## 3. Role Architecture

### Admin

Admin users manage the broader QC operation and system configuration.

Main access areas:

- Dashboard.
- Reports.
- Monitoring.
- Staff management.
- Learning management.
- Google Sheets export.

Admin responsibilities include reviewing QC performance, managing staff, maintaining learning content, exporting data, and supervising operational compliance.

### Staff

Staff users focus on mobile-friendly operational input and daily QC activities.

Main access areas:

- Mobile dashboard.
- Temperature monitoring.
- QC check.
- Batch input.
- Profile.

Staff responsibilities include submitting scheduled monitoring data, recording batch production activity, performing QC checks, uploading evidence, and maintaining accurate operational records.

## 4. Core Workflow

The core workflow connects authentication, role-based access, production activity, QC validation, reporting, and export.

1. User logs in through the web interface.
2. The system validates credentials and identifies the user role.
3. The user is redirected based on role.
4. Staff perform monitoring based on scheduled slots.
5. Staff record batch production sequence data.
6. QC inspection is submitted and classified.
7. HOLD or uncertain results can proceed to re-check.
8. Admin reviews operational data through reports.
9. Admin exports monitoring or QC data to Google Sheets when needed.

## 5. Monitoring Workflow

Monitoring is designed around fixed operational slots:

- 07:00
- 13:00
- 16:00
- 19:00

Each monitoring slot supports per-device monitoring. This means every registered production device can be checked individually for each scheduled time.

The workflow includes duplicate prevention to reduce repeated submissions for the same device and slot. This helps protect data quality and makes the monitoring history easier to audit.

Monitoring progress can be calculated using:

```text
Total Progress = Total Monitored Devices / (Total Devices x Total Slots)
```

This allows the system to show completion progress across all required device checks and scheduled monitoring times.

## 6. Batch Workflow

The batch workflow records production activity at the cooking process level.

In this system:

- **1 batch = 1 cooking process.**
- Each batch is represented by a `batch_sequence`.
- Batch data can be connected with monitoring, QC inspection, reporting, and traceability workflows.

The recommended batch code format is:

```text
SKU-YYYYMMDD-001
```

Example:

```text
CKN-20260529-001
```

This format helps identify the product SKU, production date, and sequence number for the day.

## 7. QC Inspection Workflow

QC inspection records the quality status of a product, process, or batch.

Supported QC statuses:

- **PASS:** The inspected item meets the defined quality requirements.
- **HOLD:** The inspected item requires further review, corrective action, or re-check.
- **FAIL:** The inspected item does not meet the defined quality requirements.

The workflow supports evidence upload so users can attach supporting proof, such as inspection photos or related documentation.

Concurrency lock logic is used to reduce the risk of conflicting updates when multiple users interact with the same inspection record. This helps preserve consistency during status changes, evidence updates, and re-check actions.

Re-check history preserves follow-up inspection records. This is important for traceability because it shows how a HOLD or uncertain result was reviewed over time.

## 8. ITDV Learning Workflow

The ITDV Learning workflow supports structured internal learning for QC knowledge, HACCP concepts, and operational understanding.

Learning components include:

- Module.
- Mini quiz.
- Simulation.
- Quiz.
- Certificate.
- Career recommendation.
- Admin CRUD learning.

Users can access learning modules, complete quizzes, follow simulations, and receive certificates after meeting completion criteria. Career recommendation features can help guide users toward relevant development paths based on learning progress and assessment results.

Admin users can manage learning content through CRUD operations, including creating, updating, reviewing, and deleting learning materials.

## 9. Google Sheets Export Workflow

Google Sheets export is handled through an integration workflow using Google Apps Script as a webhook endpoint.

Export capabilities include:

- Monitoring export.
- QC export.
- Historical re-export.

The Flask backend prepares selected data and sends it to the Google Apps Script webhook. Google Apps Script then writes the data into the configured Google Sheets document.

Historical re-export allows admin users to export previous monitoring or QC records based on selected filters or date ranges. This supports reporting, external review, backup, and operational documentation.

## 10. Data Flow Diagram Text

```text
Staff/Admin
    |
    v
Frontend
    |
    v
Flask API
    |
    v
Service Layer
    |
    v
Supabase
    |
    v
Google Apps Script
    |
    v
Google Sheets
```

This flow shows how user actions move from the interface to backend services, database storage, and external spreadsheet integration.

## 11. Security

Security is handled through role separation, environment configuration, and controlled backend access.

Key security principles:

- Role-based access for Admin and Staff users.
- Admin-only endpoints for sensitive operations such as reports, staff management, learning management, and export.
- Environment variables for secrets, service keys, API URLs, and integration configuration.
- No secret values stored in frontend code.

Sensitive operations should always be validated on the backend. The frontend may control visibility, but authorization must be enforced by the Flask API.

## 12. Testing

Testing supports stability, regression prevention, and deployment confidence.

Testing scope includes:

- `pytest` for backend unit and integration tests.
- JavaScript syntax check for frontend script validation.
- Smoke route tests to confirm important pages and API routes respond correctly.
- Regression tests for critical workflows such as login, monitoring, QC inspection, re-check, reports, and export.

These tests help ensure new changes do not break core QC operations or role-based behavior.

## 13. Future Architecture

QC Enterprise can be expanded into a more advanced digital QC platform through future architecture improvements.

Potential future improvements:

- IoT temperature sensor integration for automated monitoring input.
- WhatsApp alert integration for HOLD, FAIL, missed monitoring, and urgent follow-up.
- AI anomaly detection for unusual temperature patterns, recurring QC issues, and batch risk signals.
- Multi-tenant SaaS architecture for supporting multiple branches, kitchens, or companies.
- APK or Capacitor packaging for native-like mobile deployment.

These future directions can extend QC Enterprise from a web-based information system into a scalable quality control automation platform.
