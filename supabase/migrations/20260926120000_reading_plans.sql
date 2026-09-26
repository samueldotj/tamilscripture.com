-- Reading plans (docs/feature_reading_plans.md, design 14A).
--
-- Two tables. reading_plans holds the community plans moderators write; the
-- built-in plans (whole Bible in one or two years, New Testament and Psalms in
-- six months) live in lib/plans/schedule.ts and never touch the database.
-- plan_progress holds each reader's joined plans: the start date and the
-- passages read, one row per reader per plan, keyed by the plan's id (a
-- built-in key such as 'bible-1y' or a reading_plans uuid).
--
-- A plan stores only its shape (tracks of book ranges and a length in days);
-- the daily schedule is computed in the browser, so a passage is named by
-- "day-track" ('12-0': day 13, first track) and the database never holds text.

-- ---- the plan shape --------------------------------------------------------------
-- Mirrors LIMITS in lib/plans/schedule.ts: 1-6 tracks, each a name and a
-- range of USFM book codes. Book order is checked in the browser, which has
-- the book list; a reversed range there is dropped, not read backwards.
create or replace function public.check_plan_tracks(t jsonb)
returns boolean
language sql
immutable
as $$
  select jsonb_typeof(t) = 'array'
     and jsonb_array_length(t) between 1 and 6
     and coalesce((
       select bool_and(
                jsonb_typeof(x) = 'object'
            and (select bool_and(k in ('name', 'from', 'to')) from jsonb_object_keys(x) k)
            and jsonb_typeof(x->'name') = 'string' and length(x->>'name') <= 60
            and coalesce(x->>'from', '') ~ '^[1-3A-Z]{3}$'
            and coalesce(x->>'to', '') ~ '^[1-3A-Z]{3}$')
       from jsonb_array_elements(t) x), false);
$$;

-- Passages read: "day-track" keys, day 0-729 and track 0-5.
create or replace function public.check_plan_done(ks text[])
returns boolean
language sql
immutable
as $$
  select cardinality(ks) <= 4380
     and coalesce((select bool_and(k ~ '^(0|[1-9][0-9]{0,2})-[0-5]$') from unnest(ks) k), true);
$$;

-- ---- community plans ---------------------------------------------------------------
create table public.reading_plans (
  id           uuid primary key default gen_random_uuid(),
  title_ta     text not null default '' check (length(title_ta) <= 120),
  title_en     text not null default '' check (length(title_en) <= 120),
  blurb        text not null default '' check (length(blurb) <= 1000),
  days         smallint not null check (days between 7 and 730),
  tracks       jsonb not null check (public.check_plan_tracks(tracks)),
  status       text not null default 'draft' check (status in ('draft', 'published')),
  created_by   uuid references auth.users(id) on delete set null,
  published_at timestamptz,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  -- a published plan needs a Tamil name; a draft may be half-written
  check (status = 'draft' or length(btrim(title_ta)) > 0)
);
create index reading_plans_published on public.reading_plans (published_at) where status = 'published';
create trigger reading_plans_touch before update on public.reading_plans for each row execute function public.touch_updated_at();

-- Everyone reads published plans; moderators alone see drafts and write.
alter table public.reading_plans enable row level security;
create policy "published plans" on public.reading_plans
  for select to anon, authenticated using (status = 'published');
create policy "moderators read plans" on public.reading_plans
  for select to authenticated using (public.my_role() = 'moderator');
create policy "moderators write plans" on public.reading_plans
  for insert to authenticated with check (public.my_role() = 'moderator' and created_by = auth.uid());
create policy "moderators edit plans" on public.reading_plans
  for update to authenticated using (public.my_role() = 'moderator') with check (public.my_role() = 'moderator');
create policy "moderators delete plans" on public.reading_plans
  for delete to authenticated using (public.my_role() = 'moderator');
revoke all on public.reading_plans from anon;
grant select on public.reading_plans to anon;
grant select, insert, update, delete on public.reading_plans to authenticated;
-- created_by is set on insert and never moved to another user afterwards.
revoke update on public.reading_plans from authenticated;
grant update (title_ta, title_en, blurb, days, tracks, status, published_at) on public.reading_plans to authenticated;

-- ---- a reader's progress -----------------------------------------------------------
create table public.plan_progress (
  user_id    uuid not null references auth.users(id) on delete cascade,
  plan       text not null check (plan ~ '^[a-z0-9-]{2,40}$'),
  start_date date not null,
  done       text[] not null default '{}' check (public.check_plan_done(done)),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, plan)
);
create trigger plan_progress_touch before update on public.plan_progress for each row execute function public.touch_updated_at();

alter table public.plan_progress enable row level security;
create policy "own plan progress" on public.plan_progress
  for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
revoke all on public.plan_progress from anon;
grant select, insert, update, delete on public.plan_progress to authenticated;

-- ---- export (R-10.4) -----------------------------------------------------------------
-- The user's export now carries their reading plans too.
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
    'presentations', coalesce((select jsonb_agg(to_jsonb(r) - 'user_id' order by r.created_at) from public.presentations r where r.user_id = auth.uid()), '[]'::jsonb),
    'reading_plans', coalesce((select jsonb_agg(to_jsonb(g) - 'user_id' order by g.created_at) from public.plan_progress g where g.user_id = auth.uid()), '[]'::jsonb)
  );
$$;
grant execute on function public.export_my_data() to authenticated;
