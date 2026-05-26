-- Additive admin CRUD support for ITDV Learning Center.
-- Keeps existing module/progress data intact and uses soft-delete flags.

alter table public.itdv_modules
  add column if not exists description text,
  add column if not exists learning_material text,
  add column if not exists case_study text,
  add column if not exists competencies jsonb not null default '[]'::jsonb,
  add column if not exists estimated_time integer,
  add column if not exists order_number integer,
  add column if not exists difficulty text,
  add column if not exists published boolean not null default true,
  add column if not exists archived boolean not null default false,
  add column if not exists updated_at timestamptz not null default now();

update public.itdv_modules
set
  description = coalesce(description, summary),
  estimated_time = coalesce(estimated_time, duration_minutes),
  order_number = coalesce(order_number, sort_order)
where description is null or estimated_time is null or order_number is null;

create table if not exists public.itdv_module_mini_quizzes (
  id uuid primary key default gen_random_uuid(),
  module_slug text not null references public.itdv_modules(slug) on delete cascade,
  question text not null,
  option_a text not null,
  option_b text not null,
  option_c text not null,
  option_d text not null,
  correct_answer text not null check (correct_answer in ('A', 'B', 'C', 'D')),
  explanation text,
  published boolean not null default true,
  archived boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.itdv_simulations
  add column if not exists risk text,
  add column if not exists ideal_action text,
  add column if not exists haccp_reason text,
  add column if not exists corrective_action text,
  add column if not exists documentation_required text,
  add column if not exists published boolean not null default true,
  add column if not exists archived boolean not null default false,
  add column if not exists updated_at timestamptz not null default now();

create table if not exists public.itdv_quiz_questions (
  id uuid primary key default gen_random_uuid(),
  question text not null,
  option_a text not null,
  option_b text not null,
  option_c text not null,
  option_d text not null,
  correct_answer text not null check (correct_answer in ('A', 'B', 'C', 'D')),
  explanation text,
  related_module_slug text references public.itdv_modules(slug) on delete set null,
  published boolean not null default true,
  archived boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_itdv_modules_admin_order_022
on public.itdv_modules (archived, published, sort_order);

create index if not exists idx_itdv_module_mini_quizzes_module_022
on public.itdv_module_mini_quizzes (module_slug, archived, published);

create index if not exists idx_itdv_simulations_admin_022
on public.itdv_simulations (archived, published, created_at desc);

create index if not exists idx_itdv_quiz_questions_admin_022
on public.itdv_quiz_questions (archived, published, related_module_slug);
