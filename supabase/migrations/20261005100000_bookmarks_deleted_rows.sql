-- Bookmarks, and a record of deleted rows so the Android app can sync by cursor
-- (app roadmap M6-1, design §13.3). Nothing here changes existing rows.

create table public.bookmarks (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  book        text not null,
  chapter     smallint not null,
  verse       smallint not null,
  version     text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (user_id, book, chapter, verse)
);
alter table public.bookmarks enable row level security;
create policy "own bookmarks" on public.bookmarks
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create trigger bookmarks_touch before update on public.bookmarks for each row execute function public.touch_updated_at();

-- One row per deleted highlight, note or bookmark. A client that last synced at T
-- asks for rows changed since T and for deletions since T. Kept 90 days; a client
-- away longer does a full pull.
create table public.deleted_rows (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references auth.users(id) on delete cascade,
  table_name  text not null check (table_name in ('highlights', 'notes', 'bookmarks')),
  row_id      uuid not null,
  deleted_at  timestamptz not null default now()
);
create index deleted_rows_user_time on public.deleted_rows (user_id, deleted_at);
alter table public.deleted_rows enable row level security;
create policy "own deletions" on public.deleted_rows for select using (auth.uid() = user_id);

create or replace function public.record_deleted_row()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  -- Account deletion cascades through here too; those rows go with the user.
  if exists (select 1 from auth.users where id = old.user_id) then
    insert into public.deleted_rows (user_id, table_name, row_id) values (old.user_id, tg_table_name, old.id);
  end if;
  delete from public.deleted_rows where user_id = old.user_id and deleted_at < now() - interval '90 days';
  return old;
end;
$$;
create trigger highlights_deleted after delete on public.highlights for each row execute function public.record_deleted_row();
create trigger notes_deleted after delete on public.notes for each row execute function public.record_deleted_row();
create trigger bookmarks_deleted after delete on public.bookmarks for each row execute function public.record_deleted_row();

-- Export now includes bookmarks (R-10.4).
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
    'bookmarks', coalesce((select jsonb_agg(to_jsonb(b) - 'user_id' order by b.created_at) from public.bookmarks b where b.user_id = auth.uid()), '[]'::jsonb),
    'history', coalesce((select jsonb_agg(to_jsonb(x) - 'user_id' order by x.visited_at) from public.history x where x.user_id = auth.uid()), '[]'::jsonb)
  );
$$;
