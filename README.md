# AstroQC — Intelligent Traceability System

A modular, service-oriented QC monitoring system for central kitchen facilities.

## 🚀 Quick Start

1. **Backend**:
   ```bash
   pip install -r requirements.txt
   python -m backend.app
   ```
   API runs at `http://localhost:5000`

2. **Frontend**:
   Open `frontend/dashboard/login.html` or run via local server.
   Default Login: `admin` / `admin123`

## 🏗️ Architecture

- **`backend/`**: Flask-based REST API using Blueprints.
- **`frontend/`**: Mobile-first PWA with Dark Industrial Glass aesthetic.
- **`db/`**: SQL schemas and seeds for Supabase.
- **`integrations/`**: Third-party services (GCP Vision, WhatsApp).
- **`docs/`**: API specifications and Architecture SOPs.
- **`tests/`**: Unit and Integration test suite.

## 📱 Features

- **Facility Monitor**: Real-time temperature tracking for Chillers/Freezers.
- **Batch Inspection**: 4-stage CCP traceability with photo evidence.
- **AI OCR**: Automatic reading of thermometers via Google Cloud Vision.
- **Critical Alerts**: Real-time violation alerts with corrective action tracking.

---
© 2026 PT Astro Teknologi Indonesia
