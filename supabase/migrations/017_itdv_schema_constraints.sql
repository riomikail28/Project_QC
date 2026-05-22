-- Finalize ITDV learning schema names and constraints.
-- This migration only touches ITDV tables and does not modify legacy QC data.

do $$
begin
    if to_regclass('public.itdv_progress') is null
       and to_regclass('public.itdv_learning_progress') is not null then
        alter table public.itdv_learning_progress rename to itdv_progress;
    end if;
end $$;

create table if not exists public.itdv_progress (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    module_slug text not null,
    status text not null default 'in_progress',
    completed_at timestamptz,
    updated_at timestamptz not null default now()
);

do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'itdv_progress_module_slug_fkey') then
        alter table public.itdv_progress
            add constraint itdv_progress_module_slug_fkey
            foreign key (module_slug)
            references public.itdv_modules(slug)
            on delete cascade;
    end if;

    if not exists (select 1 from pg_constraint where conname = 'itdv_progress_status_check') then
        alter table public.itdv_progress
            add constraint itdv_progress_status_check
            check (status in ('in_progress', 'completed'));
    end if;

    if not exists (select 1 from pg_constraint where conname = 'itdv_progress_completed_at_check') then
        alter table public.itdv_progress
            add constraint itdv_progress_completed_at_check
            check (status <> 'completed' or completed_at is not null);
    end if;

    if not exists (select 1 from pg_constraint where conname = 'itdv_progress_user_module_unique') then
        alter table public.itdv_progress
            add constraint itdv_progress_user_module_unique
            unique (user_id, module_slug);
    end if;
end $$;

do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'itdv_modules_duration_non_negative') then
        alter table public.itdv_modules
            add constraint itdv_modules_duration_non_negative
            check (duration_minutes >= 0);
    end if;

    if not exists (select 1 from pg_constraint where conname = 'itdv_modules_objectives_array') then
        alter table public.itdv_modules
            add constraint itdv_modules_objectives_array
            check (jsonb_typeof(objectives) = 'array');
    end if;
end $$;

do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'itdv_simulations_options_array') then
        alter table public.itdv_simulations
            add constraint itdv_simulations_options_array
            check (jsonb_typeof(options) = 'array');
    end if;

    if not exists (select 1 from pg_constraint where conname = 'itdv_simulations_best_actions_array') then
        alter table public.itdv_simulations
            add constraint itdv_simulations_best_actions_array
            check (jsonb_typeof(best_actions) = 'array');
    end if;
end $$;

do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'itdv_simulation_attempts_simulation_fkey') then
        alter table public.itdv_simulation_attempts
            add constraint itdv_simulation_attempts_simulation_fkey
            foreign key (simulation_id)
            references public.itdv_simulations(id)
            on delete cascade;
    end if;

    if not exists (select 1 from pg_constraint where conname = 'itdv_simulation_attempts_score_check') then
        alter table public.itdv_simulation_attempts
            add constraint itdv_simulation_attempts_score_check
            check (score >= 0 and score <= 100);
    end if;
end $$;

do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'itdv_quizzes_module_slug_fkey') then
        alter table public.itdv_quizzes
            add constraint itdv_quizzes_module_slug_fkey
            foreign key (module_slug)
            references public.itdv_modules(slug)
            on delete set null;
    end if;

    if not exists (select 1 from pg_constraint where conname = 'itdv_quizzes_questions_array') then
        alter table public.itdv_quizzes
            add constraint itdv_quizzes_questions_array
            check (jsonb_typeof(questions) = 'array');
    end if;
end $$;

do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'itdv_quiz_attempts_quiz_fkey') then
        alter table public.itdv_quiz_attempts
            add constraint itdv_quiz_attempts_quiz_fkey
            foreign key (quiz_id)
            references public.itdv_quizzes(id)
            on delete cascade;
    end if;

    if not exists (select 1 from pg_constraint where conname = 'itdv_quiz_attempts_score_check') then
        alter table public.itdv_quiz_attempts
            add constraint itdv_quiz_attempts_score_check
            check (score >= 0 and score <= 100);
    end if;

    if not exists (select 1 from pg_constraint where conname = 'itdv_quiz_attempts_answers_object') then
        alter table public.itdv_quiz_attempts
            add constraint itdv_quiz_attempts_answers_object
            check (jsonb_typeof(answers) = 'object');
    end if;
end $$;

do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'itdv_certificates_user_program_unique') then
        alter table public.itdv_certificates
            add constraint itdv_certificates_user_program_unique
            unique (user_id, program_code);
    end if;
end $$;

create index if not exists idx_itdv_progress_user on public.itdv_progress(user_id);
create index if not exists idx_itdv_progress_module on public.itdv_progress(module_slug);
create index if not exists idx_itdv_simulations_created_at on public.itdv_simulations(created_at desc);
create index if not exists idx_itdv_sim_attempts_user on public.itdv_simulation_attempts(user_id, created_at desc);
create index if not exists idx_itdv_sim_attempts_simulation on public.itdv_simulation_attempts(simulation_id, created_at desc);
create index if not exists idx_itdv_quizzes_module on public.itdv_quizzes(module_slug);
create index if not exists idx_itdv_quiz_attempts_user on public.itdv_quiz_attempts(user_id, created_at desc);
create index if not exists idx_itdv_quiz_attempts_quiz on public.itdv_quiz_attempts(quiz_id, created_at desc);
create index if not exists idx_itdv_certificates_user on public.itdv_certificates(user_id, issued_at desc);
