create table if not exists public.itdv_mentor_history (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    question text not null,
    answer text not null,
    topics jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'itdv_mentor_history_question_length') then
        alter table public.itdv_mentor_history
            add constraint itdv_mentor_history_question_length
            check (char_length(question) between 3 and 1000);
    end if;

    if not exists (select 1 from pg_constraint where conname = 'itdv_mentor_history_topics_array') then
        alter table public.itdv_mentor_history
            add constraint itdv_mentor_history_topics_array
            check (jsonb_typeof(topics) = 'array');
    end if;
end $$;

create index if not exists idx_itdv_mentor_history_user_created
on public.itdv_mentor_history(user_id, created_at desc);
