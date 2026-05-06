# QC Central Kitchen - Backend v2.0

Modular Flask architecture for industrial-scale QC monitoring.

## Architecture

- **`app.py`**: Application entry point.
- **`__init__.py`**: Flask application factory and blueprint registration.
- **`routes/`**: HTTP layer (Blueprints). No business logic here.
  - `temperature_routes.py`: Facility monitoring.
  - `batch_routes.py`: Production batch management.
  - `qc_routes.py`: Dashboard and system health.
  - `ccp_routes.py`: Multi-stage CCP inspections.
- **`service/`**: Core business logic layer.
  - `qc_engine.py`: Validation rules (SOPs).
  - `alert_service.py`: Alert generation and corrective actions.
  - `batch_service.py`: Batch lifecycle and summary logic.
  - `ccp_service.py`: Inspection stage processing (OCR, Photo).
- **`database/`**: Persistence layer.
  - `supabase_client.py`: Singleton client for Supabase.
- **`skills/`**: Domain-specific standalone modules.
  - `product_catalog.py`: SKU database and fallback.
  - `staff_manager.py`: Authentication and staff CRUD.
  - `parameter_checker.py`: Granular QC parameter validation.
  - `auto_reporter.py`: Batch summary report generation.

## Technology Stack

- **Framework**: Flask
- **Database**: Supabase (PostgreSQL)
- **Deployment**: Vercel / Docker
- **Frontend**: Vanilla JS / CSS (Industrial Mobile-First)
