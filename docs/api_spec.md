# QC Central Kitchen — API Specification (v2.0)

## 1. Authentication
- **POST `/api/staff/login`**: Authenticate staff and return JWT/Role.

## 2. Dashboard & Analytics
- **GET `/api/qc/dashboard`**: Returns health score, critical issues, and room summaries.
- **GET `/api/qc/stats`**: Returns daily/weekly production statistics.

## 3. Temperature Monitoring
- **GET `/api/temperature/history`**: Get latest 20 facility logs.
- **POST `/api/temperature/log`**: Submit a new zone temperature.
  - Body: `{ "zone": "Chiller 01", "temp": 4.5 }`

## 4. Batch Management
- **GET `/api/batch/list`**: List all active and completed batches.
- **POST `/api/batch/create`**: Initialize a new production batch.
  - Body: `{ "sku": "BRD-001", "operator_id": "uuid" }`
- **GET `/api/batch/<id>`**: Get detailed timeline and CCP logs for a batch.

## 5. CCP Inspections
- **POST `/api/ccp/submit-stage`**: Submit inspection data for a specific CCP stage.
  - Multipart: `batch_id`, `stage`, `metrics` (json), `photo` (file).
- **POST `/api/ccp/ocr`**: Process a photo via GCP Vision and return extracted text.

## 6. Alerts
- **GET `/api/alerts`**: List all active critical violations.
- **POST `/api/alerts/<id>/resolve`**: Mark an alert as resolved with a corrective action log.
