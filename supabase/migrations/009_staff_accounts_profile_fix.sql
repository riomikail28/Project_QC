-- Staff account/profile compatibility fix.
-- Existing production staff_accounts does not have full_name; keep identity fields in users.

alter table if exists public.users
  add column if not exists staff_account_id uuid,
  add column if not exists full_name text,
  add column if not exists role text not null default 'qc_staff',
  add column if not exists updated_at timestamptz not null default now();

do $$
begin
  if to_regclass('public.staff_accounts') is not null
     and not exists (
       select 1 from pg_constraint
       where conname = 'users_staff_account_id_fkey'
         and conrelid = 'public.users'::regclass
     ) then
    alter table public.users
      add constraint users_staff_account_id_fkey
      foreign key (staff_account_id) references public.staff_accounts(id) on delete set null not valid;
  end if;
end $$;

create unique index if not exists idx_users_staff_account_id_unique
on public.users (staff_account_id)
where staff_account_id is not null;

insert into public.users (staff_account_id, full_name, role)
select
  sa.id,
  sa.username,
  case when sa.role = 'admin' then 'admin' else 'qc_staff' end
from public.staff_accounts sa
where not exists (
  select 1 from public.users u where u.staff_account_id = sa.id
);
