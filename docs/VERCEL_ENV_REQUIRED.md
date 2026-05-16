# Vercel Environment Variables Required

Set these variables in Vercel Project Settings before deploying the backend.

## Required

- `SUPABASE_URL`: Supabase project URL, for example `https://PROJECT_REF.supabase.co`.
- `SUPABASE_SERVICE_ROLE_KEY`: Backend-only service role key used for privileged Storage and database writes.
- `SUPABASE_STORAGE_BUCKET`: Storage bucket name. Use `qc-evidence`.
- `JWT_SECRET_KEY`: Strong random secret for staff/admin JWT.
- `CORS_ORIGINS`: Production origin, for example `https://project-qc-mu.vercel.app`.

## Compatibility Fallback

- `SUPABASE_KEY`: Backend fallback if `SUPABASE_SERVICE_ROLE_KEY` is not present.

Do not use `SUPABASE_ANON_KEY` for backend privileged upload. The service role key must never be exposed to frontend JavaScript.
