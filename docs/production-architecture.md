# Production Architecture

Project QC is deployed as a Vercel serverless Flask application with static frontend pages served by the same app. Supabase is the only external backend platform for database records, storage buckets, and realtime-ready monitoring data.

## Runtime Flow

1. Browser opens `/login.html`, `/dashboard.html`, or `/admin_panel.html`.
2. Flask serves files from `frontend/staff` or `frontend/admin`.
3. Browser calls `/api/...` endpoints with JWT bearer tokens.
4. Flask validates the token and role in `backend/middleware/security_middleware.py`.
5. Services read/write Supabase tables and storage buckets.

## Supported Deployment

- Vercel: serverless Flask + static frontend
- Supabase: Postgres, Storage, Auth/session-compatible user data
- GitHub Actions: validate, test, Vercel deploy

## Disabled Deployment Paths

The repo intentionally does not include Kubernetes, Helm, Docker, Redis/Celery workers, AWS S3, WAL-G backups, chaos testing, or old staging cluster workflows.
