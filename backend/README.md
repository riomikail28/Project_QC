# Backend

Flask backend organized for Vercel + Supabase production deployment.

- `api/`: HTTP blueprints.
- `services/`: business logic and Supabase data access.
- `middleware/`: security, JWT role guard, and metrics.
- `database/`: Supabase client singleton.
- `auth/`: staff account helpers.
- `qc/`: QC validation helpers.
- `monitoring/`: facility/temperature helpers.
- `utils/`: shared utilities.

The backend has no Docker, Kubernetes, Celery, Redis, AWS S3, or Google Sheets runtime dependency.
