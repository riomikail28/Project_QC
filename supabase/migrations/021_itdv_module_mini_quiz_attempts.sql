-- Mini quiz attempts for individual ITDV learning modules.
-- Additive only; existing ITDV progress remains unchanged.

create table if not exists public.itdv_module_quiz_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  module_slug text not null references public.itdv_modules(slug) on delete cascade,
  score integer not null check (score >= 0 and score <= 100),
  passed boolean not null default false,
  answers jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_itdv_module_quiz_attempts_user_module_021
on public.itdv_module_quiz_attempts (user_id, module_slug, created_at desc);

create index if not exists idx_itdv_module_quiz_attempts_passed_021
on public.itdv_module_quiz_attempts (user_id, module_slug, passed);
