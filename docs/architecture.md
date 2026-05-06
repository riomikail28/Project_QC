# QC Central Kitchen — Architecture & SOP Guide

## 1. System Overview
The system is built on a **Modular Service Architecture** using Flask (Python) and Supabase (PostgreSQL). It is designed to handle high-frequency quality control data from a central kitchen facility.

## 2. Directory Structure
- `backend/`: Core logic and API gateway.
  - `routes/`: Blueprint-based API endpoints.
  - `service/`: Domain-specific business logic.
  - `skills/`: Low-level utilities and managed data.
- `frontend/`: PWA-enabled mobile-first dashboard.
- `db/`: Database migrations and schema definitions.
- `integrations/`: Third-party service configurations (OCR, WhatsApp, etc).

## 3. Standard Operating Procedures (SOP)

### 3.1 Temperature Monitoring
- **Chiller**: Must be between `0°C` and `5°C`.
- **Freezer**: Must be below `-18°C`.
- **Ambient**: Must be below `25°C`.
- Alerts are automatically triggered if thresholds are violated for > 15 minutes.

### 3.2 Batch Traceability (CCP)
Every production batch must pass through 4 stages:
1. **Material Incoming**: Check raw material temp.
2. **Cooking**: Check core product temp (target > 75°C).
3. **Cooling**: Check rapid cooling progress.
4. **Packaging**: Check chemical parameters (Brix, pH, TDS) and labeling.

## 4. Integration Guide
- **Supabase**: Primary database and photo storage.
- **GCP Vision**: Used for thermometer OCR in Stage 2.
- **WhatsApp API**: (Pending) For critical alert notifications to QC Leads.
