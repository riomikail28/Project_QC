-- QC Evidence Storage Bucket
-- Apply in Supabase SQL editor or migration pipeline before production launch.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'qc-evidence',
  'qc-evidence',
  false,
  5242880,
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Remove older policy definitions safely before recreating.
drop policy if exists "qc evidence admin read" on storage.objects;
drop policy if exists "qc evidence admin write" on storage.objects;
drop policy if exists "qc evidence admin delete" on storage.objects;
drop policy if exists "qc evidence staff read own" on storage.objects;
drop policy if exists "qc evidence staff write own" on storage.objects;

-- Admins can read all evidence.
create policy "qc evidence admin read"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'qc-evidence'
  and coalesce((auth.jwt() ->> 'role'), '') = 'admin'
);

-- Admins can upload/update all evidence.
create policy "qc evidence admin write"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'qc-evidence'
  and coalesce((auth.jwt() ->> 'role'), '') = 'admin'
);

-- Admins can delete evidence during audit cleanup.
create policy "qc evidence admin delete"
on storage.objects
for delete
to authenticated
using (
  bucket_id = 'qc-evidence'
  and coalesce((auth.jwt() ->> 'role'), '') = 'admin'
);

-- Staff can read their own folder only.
-- Expected object path: <auth.uid()>/<context>/<filename>
create policy "qc evidence staff read own"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'qc-evidence'
  and owner = auth.uid()
);

-- Staff can upload to their own folder only.
-- Expected object path: <auth.uid()>/<context>/<filename>
create policy "qc evidence staff write own"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'qc-evidence'
  and owner = auth.uid()
  and split_part(name, '/', 1) = auth.uid()::text
);
