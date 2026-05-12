alter table public.staff_activity enable row level security;
alter table public.qc_reports enable row level security;
alter table public.temperature_logs enable row level security;
alter table public.barcode_labels enable row level security;
alter table public.audit_logs enable row level security;

create policy "authenticated read staff activity"
on public.staff_activity for select
to authenticated
using (true);

create policy "authenticated read qc reports"
on public.qc_reports for select
to authenticated
using (true);

create policy "authenticated write qc reports"
on public.qc_reports for insert
to authenticated
with check (true);

create policy "authenticated update qc reports"
on public.qc_reports for update
to authenticated
using (true)
with check (true);

create policy "authenticated read temperature logs"
on public.temperature_logs for select
to authenticated
using (true);

create policy "authenticated write temperature logs"
on public.temperature_logs for insert
to authenticated
with check (true);

create policy "authenticated read barcode labels"
on public.barcode_labels for select
to authenticated
using (true);

create policy "authenticated write barcode labels"
on public.barcode_labels for insert
to authenticated
with check (true);

create policy "authenticated read audit logs"
on public.audit_logs for select
to authenticated
using (true);

create policy "authenticated write audit logs"
on public.audit_logs for insert
to authenticated
with check (true);

create policy "public read qc photos"
on storage.objects for select
to public
using (bucket_id in ('qc-photos', 'barcode-labels', 'temperature-checks'));

create policy "authenticated upload qc photos"
on storage.objects for insert
to authenticated
with check (bucket_id in ('qc-photos', 'barcode-labels', 'temperature-checks'));
