-- Verse presentations (docs/feature_presentation.md): slides of verse
-- references with Markdown notes, made by a signed-in user and shown from a
-- permalink. No verse text is stored: a slide names book, chapter and verses,
-- and the page reads the words from the site's own content in whichever
-- version is chosen when it is shown, so a presentation follows a change of
-- translation. The owner reads and writes through PostgREST under RLS; the
-- audience reads through one security-definer function that returns only
-- presentations shared by link, and never the owner's id.

-- ---- slide shape --------------------------------------------------------------
-- Mirrors LIMITS in apps/web/src/lib/present/types.ts. Change both together.
create or replace function public.check_slides(p jsonb)
returns boolean
language plpgsql
immutable
as $$
declare
  s jsonb;
  v jsonb;
begin
  if p is null or jsonb_typeof(p) <> 'array' then return false; end if;
  if jsonb_array_length(p) > 200 then return false; end if;
  if length(p::text) > 400000 then return false; end if;
  for s in select * from jsonb_array_elements(p) loop
    if jsonb_typeof(s) <> 'object' then return false; end if;
    if exists (select 1 from jsonb_object_keys(s) k where k not in ('id', 'title', 'notes', 'verses')) then return false; end if;
    if jsonb_typeof(s->'id') <> 'string' or length(s->>'id') not between 1 and 32 then return false; end if;
    if s ? 'title' and (jsonb_typeof(s->'title') <> 'string' or length(s->>'title') > 200) then return false; end if;
    if jsonb_typeof(s->'notes') <> 'string' or length(s->>'notes') > 20000 then return false; end if;
    if jsonb_typeof(s->'verses') <> 'array' or jsonb_array_length(s->'verses') > 20 then return false; end if;
    for v in select * from jsonb_array_elements(s->'verses') loop
      if jsonb_typeof(v) <> 'object' then return false; end if;
      if exists (select 1 from jsonb_object_keys(v) k where k not in ('book', 'chapter', 'start', 'end', 'version')) then return false; end if;
      if jsonb_typeof(v->'book') <> 'string' or (v->>'book') !~ '^[1-3A-Z]{3}$' then return false; end if;
      if jsonb_typeof(v->'chapter') <> 'number' or (v->>'chapter') !~ '^[0-9]{1,3}$' or (v->>'chapter')::int not between 1 and 150 then return false; end if;
      if jsonb_typeof(v->'start') <> 'number' or (v->>'start') !~ '^[0-9]{1,3}$' or (v->>'start')::int not between 1 and 176 then return false; end if;
      if jsonb_typeof(v->'end') <> 'number' or (v->>'end') !~ '^[0-9]{1,3}$' or (v->>'end')::int not between (v->>'start')::int and 176 then return false; end if;
      if v ? 'version' and (jsonb_typeof(v->'version') <> 'string' or (v->>'version') !~ '^[A-Z0-9]{2,12}$') then return false; end if;
    end loop;
  end loop;
  return true;
end;
$$;

-- ---- table ----------------------------------------------------------------------
create table public.presentations (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  slug        text not null unique check (slug ~ '^[a-z0-9]{8,16}$'),   -- the permalink: /present/{slug}
  title       text not null default '' check (length(title) <= 200),
  subtitle    text check (length(subtitle) <= 200),
  version     text not null default 'IRVTAM' check (version ~ '^[A-Z0-9]{2,12}$'),  -- default version for the verses
  visibility  text not null default 'link' check (visibility in ('private', 'link')),
  slides      jsonb not null default '[]'::jsonb check (public.check_slides(slides)),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index presentations_user on public.presentations (user_id, updated_at desc);
create trigger presentations_touch before update on public.presentations for each row execute function public.touch_updated_at();

alter table public.presentations enable row level security;
create policy "own presentations" on public.presentations
  for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
revoke all on public.presentations from anon;
grant select, insert, update, delete on public.presentations to authenticated;

-- ---- the permalink ----------------------------------------------------------------
-- What the audience gets: the presentation without its owner, only when it is
-- shared by link. Returns null otherwise, so a private presentation and a
-- missing one look the same from outside.
create or replace function public.presentation_by_slug(p_slug text)
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  select jsonb_build_object(
    'id', id, 'slug', slug, 'title', title, 'subtitle', subtitle, 'version', version,
    'visibility', visibility, 'slides', slides, 'created_at', created_at, 'updated_at', updated_at)
  from public.presentations
  where slug = p_slug and visibility = 'link';
$$;
grant execute on function public.presentation_by_slug(text) to anon, authenticated;

-- ---- export (R-10.4) -----------------------------------------------------------------
-- The user's export now carries their presentations too.
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
    'history', coalesce((select jsonb_agg(to_jsonb(x) - 'user_id' order by x.visited_at) from public.history x where x.user_id = auth.uid()), '[]'::jsonb),
    'presentations', coalesce((select jsonb_agg(to_jsonb(r) - 'user_id' order by r.created_at) from public.presentations r where r.user_id = auth.uid()), '[]'::jsonb)
  );
$$;
grant execute on function public.export_my_data() to authenticated;
