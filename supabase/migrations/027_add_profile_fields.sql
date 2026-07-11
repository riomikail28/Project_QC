-- Add profile details to staff_accounts
ALTER TABLE public.staff_accounts
  ADD COLUMN IF NOT EXISTS employee_id text,
  ADD COLUMN IF NOT EXISTS department text,
  ADD COLUMN IF NOT EXISTS shift text,
  ADD COLUMN IF NOT EXISTS join_date text;
