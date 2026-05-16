# Vercel Supabase ENV Fix

Production error:

```text
Supabase standard client creation failed; trying fallback: Invalid API key
```

This means Vercel is not using a valid Supabase API key at runtime.

## Required Vercel ENV

- `SUPABASE_URL`: Supabase project URL, for example `https://PROJECT_REF.supabase.co`.
- `SUPABASE_SERVICE_ROLE_KEY`: backend-only key from Supabase Project Settings -> API -> `service_role` secret key.
- `SUPABASE_ANON_KEY`: public anon key from Supabase Project Settings -> API -> anon/public key.
- `SUPABASE_STORAGE_BUCKET`: `qc-evidence`.
- `JWT_SECRET_KEY`: production JWT secret.

## Rules

- `SUPABASE_SERVICE_ROLE_KEY` must not be exposed in frontend JavaScript.
- Backend upload must use `SUPABASE_SERVICE_ROLE_KEY`.
- Frontend may only receive `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_STORAGE_BUCKET`.
- Do not paste anon/public key into `SUPABASE_SERVICE_ROLE_KEY`.
- Do not use placeholder values such as `your-supabase-service-role-key`.

## Verify

After updating Vercel ENV, redeploy production and open:

```text
https://project-qc-mu.vercel.app/api/health/supabase
```

Expected:

```json
{
  "success": true,
  "supabase_url_configured": true,
  "service_role_key_configured": true,
  "storage_bucket": "qc-evidence",
  "connection": "ok"
}
```

If it returns `Invalid Supabase API key`, replace `SUPABASE_SERVICE_ROLE_KEY` with the real service_role secret key and redeploy.
