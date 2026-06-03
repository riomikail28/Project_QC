-- Ensure staff display names submitted by staff QC can be persisted.
-- Idempotent compatibility migration for existing Supabase projects.

alter table if exists public.qc_reports
  add column if not exists staff_name text;

alter table if exists public.qc_findings
  add column if not exists staff_name text;
