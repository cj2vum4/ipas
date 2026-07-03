create table if not exists public.study_progress (
  user_id uuid not null references auth.users(id) on delete cascade,
  date text not null,
  read boolean not null default false,
  quiz boolean not null default false,
  review boolean not null default false,
  updated_at timestamptz not null default now(),
  primary key (user_id, date)
);

alter table public.study_progress enable row level security;

drop policy if exists "Users can read own study progress" on public.study_progress;
create policy "Users can read own study progress"
  on public.study_progress
  for select
  using (auth.uid() = user_id);

drop policy if exists "Users can insert own study progress" on public.study_progress;
create policy "Users can insert own study progress"
  on public.study_progress
  for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users can update own study progress" on public.study_progress;
create policy "Users can update own study progress"
  on public.study_progress
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users can delete own study progress" on public.study_progress;
create policy "Users can delete own study progress"
  on public.study_progress
  for delete
  using (auth.uid() = user_id);

create table if not exists public.quiz_mistakes (
  user_id uuid not null references auth.users(id) on delete cascade,
  date text not null,
  question_index integer not null,
  prompt text not null default '',
  answer text not null default '',
  note text not null default '',
  resolved boolean not null default false,
  updated_at timestamptz not null default now(),
  primary key (user_id, date, question_index)
);

alter table public.quiz_mistakes enable row level security;

drop policy if exists "Users can read own quiz mistakes" on public.quiz_mistakes;
create policy "Users can read own quiz mistakes"
  on public.quiz_mistakes
  for select
  using (auth.uid() = user_id);

drop policy if exists "Users can insert own quiz mistakes" on public.quiz_mistakes;
create policy "Users can insert own quiz mistakes"
  on public.quiz_mistakes
  for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users can update own quiz mistakes" on public.quiz_mistakes;
create policy "Users can update own quiz mistakes"
  on public.quiz_mistakes
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users can delete own quiz mistakes" on public.quiz_mistakes;
create policy "Users can delete own quiz mistakes"
  on public.quiz_mistakes
  for delete
  using (auth.uid() = user_id);
