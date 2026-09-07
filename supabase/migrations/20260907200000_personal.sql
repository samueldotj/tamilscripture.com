-- M3: personal data. Every table is keyed by auth user and protected by RLS
-- (design §7). Locations are version-independent integers (ADR-5).

create table public.profiles (
  user_id          uuid primary key references auth.users(id) on delete cascade,
  display_name     text,
  settings         jsonb not null default '{}'::jsonb,   -- reader settings sync (R-1.9)
  share_aggregates boolean not null default true,        -- contributes to heatmaps (R-2.4)
  history_paused   boolean not null default false,       -- R-10.7
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);
alter table public.profiles enable row level security;
create policy "own profile" on public.profiles
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Create the profile row when a user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (user_id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name'))
  on conflict (user_id) do nothing;
  return new;
end;
$$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

create table public.highlights (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  book        text not null,
  chapter     smallint not null,
  verse_start smallint not null,
  verse_end   smallint not null,
  color       text not null check (color in ('yellow', 'green', 'blue', 'pink')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  check (verse_end >= verse_start)
);
create index highlights_user_loc on public.highlights (user_id, book, chapter);
alter table public.highlights enable row level security;
create policy "own highlights" on public.highlights
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create table public.notes (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  book        text not null,
  chapter     smallint not null,
  verse_start smallint not null,
  verse_end   smallint not null,
  body        text not null check (length(body) <= 5000),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  check (verse_end >= verse_start)
);
create index notes_user_loc on public.notes (user_id, book, chapter);
create index notes_body_fts on public.notes using gin (to_tsvector('simple', body));
alter table public.notes enable row level security;
create policy "own notes" on public.notes
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create table public.history (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references auth.users(id) on delete cascade,
  book        text not null,
  chapter     smallint not null,
  verse_start smallint,
  verse_end   smallint,
  version     text not null,
  visited_at  timestamptz not null default now()
);
create index history_user_time on public.history (user_id, visited_at desc);
alter table public.history enable row level security;
create policy "own history" on public.history
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- updated_at maintenance
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end; $$;
create trigger highlights_touch before update on public.highlights for each row execute function public.touch_updated_at();
create trigger notes_touch before update on public.notes for each row execute function public.touch_updated_at();
create trigger profiles_touch before update on public.profiles for each row execute function public.touch_updated_at();

-- Record a visit, collapsing repeats of the same chapter within 10 minutes (R-10.5).
create or replace function public.record_visit(p_book text, p_chapter int, p_version text, p_verse_start int default null, p_verse_end int default null)
returns void
language plpgsql
security invoker
as $$
declare
  paused boolean;
begin
  if auth.uid() is null then return; end if;
  select history_paused into paused from public.profiles where user_id = auth.uid();
  if coalesce(paused, false) then return; end if;
  if exists (
    select 1 from public.history
    where user_id = auth.uid() and book = p_book and chapter = p_chapter
      and visited_at > now() - interval '10 minutes'
  ) then
    update public.history set visited_at = now(), version = p_version,
           verse_start = coalesce(p_verse_start, verse_start), verse_end = coalesce(p_verse_end, verse_end)
    where id = (select id from public.history
                where user_id = auth.uid() and book = p_book and chapter = p_chapter
                order by visited_at desc limit 1);
  else
    insert into public.history (user_id, book, chapter, verse_start, verse_end, version)
    values (auth.uid(), p_book, p_chapter, p_verse_start, p_verse_end, p_version);
  end if;
end;
$$;
grant execute on function public.record_visit(text, int, text, int, int) to authenticated;

-- Export everything the user owns as one JSON document (R-10.4).
create or replace function public.export_my_data()
returns jsonb
language sql
security invoker
stable
as $$
  select jsonb_build_object(
    'exported_at', now(),
    'profile', (select to_jsonb(p) - 'user_id' from public.profiles p where p.user_id = auth.uid()),
    'highlights', coalesce((select jsonb_agg(to_jsonb(h) - 'user_id' order by h.created_at) from public.highlights h where h.user_id = auth.uid()), '[]'::jsonb),
    'notes', coalesce((select jsonb_agg(to_jsonb(n) - 'user_id' order by n.created_at) from public.notes n where n.user_id = auth.uid()), '[]'::jsonb),
    'history', coalesce((select jsonb_agg(to_jsonb(x) - 'user_id' order by x.visited_at) from public.history x where x.user_id = auth.uid()), '[]'::jsonb)
  );
$$;
grant execute on function public.export_my_data() to authenticated;

-- Delete the account. Cascades remove every personal row (R-10.4).
create or replace function public.delete_my_account()
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  delete from auth.users where id = auth.uid();
end;
$$;
grant execute on function public.delete_my_account() to authenticated;
