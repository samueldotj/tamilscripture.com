-- M8: site analytics for moderators (docs/feature_analytics.md).
-- No cookies, no stored IP address, no stored user id. Visitors and signed-in
-- users are daily-rotating hashes salted with a random value that is deleted
-- the next day. Only reviewers and moderators can read any of it.
--
-- A1 collect: analytics_salt, analytics_events, track()
-- A2 report:  analytics_report()
-- A3 rollups: analytics_daily, analytics_daily_totals, analytics_rollup(), retention jobs
-- A4 insight: book, chapter and site-section dimensions, search terms in the report
-- A5 live:    analytics_now(), previous-period totals in the report

-- ---- salts -----------------------------------------------------------------------

create table public.analytics_salt (
  day date primary key,
  salt bytea not null
);
alter table public.analytics_salt enable row level security;
revoke all on public.analytics_salt from anon, authenticated;
-- No policies: only the security-definer functions below touch it.

-- The day in India time: the audience's day, and the salt's.
create or replace function public.analytics_today()
returns date
language sql
stable
as $$ select (now() at time zone 'Asia/Kolkata')::date $$;

create or replace function public.analytics_salt_for(p_day date)
returns bytea
language plpgsql
security definer
set search_path = public
as $$
declare
  v_salt bytea;
begin
  select salt into v_salt from public.analytics_salt where day = p_day;
  if v_salt is null then
    insert into public.analytics_salt (day, salt)
    values (p_day, sha256(convert_to(gen_random_uuid()::text || gen_random_uuid()::text || clock_timestamp()::text, 'UTF8')))
    on conflict (day) do nothing;
    select salt into v_salt from public.analytics_salt where day = p_day;
  end if;
  return v_salt;
end;
$$;
revoke execute on function public.analytics_salt_for(date) from public, anon, authenticated;

-- ---- events ---------------------------------------------------------------------

create table public.analytics_events (
  id bigserial primary key,
  at timestamptz not null default now(),
  day date not null default public.analytics_today(),
  kind text not null check (kind in ('view', 'verse')),
  path text not null,
  route text,
  verse text,
  book text,
  chapter int,
  visitor text not null,
  member text,
  country text,
  region text,
  city text,
  device text,
  os text,
  browser text,
  screen text,
  referrer text,
  lang text
);
create index analytics_events_day on public.analytics_events (day);
create index analytics_events_at on public.analytics_events (at);
create index analytics_events_visitor_day on public.analytics_events (visitor, day);
alter table public.analytics_events enable row level security;
revoke all on public.analytics_events from anon, authenticated;
revoke all on sequence public.analytics_events_id_seq from anon, authenticated;
-- No policies: written by track(), read by the report functions.

-- ---- collection -------------------------------------------------------------------

-- Called by the site's /api/t function with what it learned from the request.
-- The IP address, user agent and user id are hashed here with today's salt and
-- never stored.
create or replace function public.track(
  p_kind text,
  p_path text,
  p_route text default null,
  p_verse text default null,
  p_ip text default '',
  p_ua text default '',
  p_user text default null,
  p_country text default null,
  p_region text default null,
  p_city text default null,
  p_device text default null,
  p_os text default null,
  p_browser text default null,
  p_screen text default null,
  p_referrer text default null,
  p_lang text default null,
  p_book text default null,
  p_chapter int default null
)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_day date := public.analytics_today();
  v_salt bytea := public.analytics_salt_for(v_day);
  v_visitor text;
  v_member text;
  clip constant int := 200;
begin
  if p_kind not in ('view', 'verse') or p_path is null or p_path !~ '^/' then
    return;
  end if;
  v_visitor := left(encode(sha256(v_salt || convert_to(coalesce(p_ip, '') || '|' || coalesce(p_ua, ''), 'UTF8')), 'hex'), 16);
  if p_user is not null and p_user ~ '^[0-9a-f-]{36}$' then
    v_member := left(encode(sha256(v_salt || convert_to('member|' || p_user, 'UTF8')), 'hex'), 16);
  end if;
  -- A runaway or forged client stops counting after 600 events in a day.
  if (select count(*) from public.analytics_events where visitor = v_visitor and day = v_day) >= 600 then
    return;
  end if;
  insert into public.analytics_events
    (day, kind, path, route, verse, book, chapter, visitor, member, country, region, city, device, os, browser, screen, referrer, lang)
  values (
    v_day, p_kind, left(p_path, clip), left(p_route, clip),
    case when p_kind = 'verse' and p_verse ~ '^[1-3A-Z]{3}\.[0-9]{1,3}\.[0-9]{1,3}$' then p_verse end,
    case when p_book ~ '^[1-3A-Z]{3}$' then p_book end,
    case when p_chapter between 1 and 150 then p_chapter end,
    v_visitor, v_member,
    left(upper(p_country), 2), left(p_region, 60), left(p_city, 80),
    case when p_device in ('mobile', 'tablet', 'desktop') then p_device end,
    left(p_os, 30), left(p_browser, 30),
    case when p_screen ~ '^[0-9]{2,5}x[0-9]{2,5}$' then p_screen end,
    left(lower(p_referrer), 120),
    case when p_lang in ('ta', 'en') then p_lang end
  );
end;
$$;
revoke execute on function public.track(text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, int) from public;
grant execute on function public.track(text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, int) to anon, authenticated;

-- ---- one day, summarised ------------------------------------------------------------

-- Which part of the site a route belongs to.
create or replace function public.analytics_section(p_route text)
returns text
language sql
immutable
as $$
  select case
    when p_route is null then 'other'
    when p_route = '/' then 'home'
    when p_route like '%[chapter=int]%' then 'reading'
    when p_route like '/atlas%' then 'atlas'
    when p_route like '/dictionary%' then 'dictionary'
    when p_route like '/place/%' then 'places'
    when p_route like '/person/%' then 'people'
    when p_route like '/search%' then 'search'
    when p_route like '/heatmap%' then 'heatmap'
    when p_route like '/about%' then 'about'
    when p_route like '/mod%' then 'moderation'
    when p_route like '/me%' or p_route like '/signin%' or p_route like '/auth%' then 'account'
    else 'other'
  end
$$;

-- Every ranked dimension for one day: n = events, u = distinct visitors that day.
-- Summing u over days gives visitor-days, which is what "visitors" means here.
create or replace function public.analytics_day_rows(p_day date)
returns table (dim text, key text, extra text, n bigint, u bigint)
language sql
stable
security definer
set search_path = public
as $$
  with e as (select * from public.analytics_events where day = p_day),
  vw as (select * from e where kind = 'view')
  select 'pages', path, '', count(*), count(distinct visitor) from vw group by path
  union all select 'sections', public.analytics_section(route), '', count(*), count(distinct visitor) from vw group by 2
  union all select 'books', book, '', count(*), count(distinct visitor) from vw where book is not null group by book
  union all select 'chapters', book || '.' || chapter, '', count(*), count(distinct visitor) from vw where book is not null and chapter is not null group by book, chapter
  union all select 'verses', verse, '', count(*), count(distinct visitor) from e where kind = 'verse' and verse is not null group by verse
  union all select 'verse_books', split_part(verse, '.', 1), '', count(*), count(distinct visitor) from e where kind = 'verse' and verse is not null group by 2
  union all select 'countries', coalesce(country, '?'), '', count(*), count(distinct visitor) from vw group by country
  union all select 'cities', coalesce(city, '?'), coalesce(country, '?'), count(*), count(distinct visitor) from vw group by city, country
  union all select 'devices', coalesce(device, '?'), '', count(*), count(distinct visitor) from vw group by device
  union all select 'os', coalesce(os, '?'), '', count(*), count(distinct visitor) from vw group by os
  union all select 'browsers', coalesce(browser, '?'), '', count(*), count(distinct visitor) from vw group by browser
  union all select 'screens', coalesce(screen, '?'), '', count(*), count(distinct visitor) from vw group by screen
  union all select 'referrers', referrer, '', count(*), count(distinct visitor) from vw where referrer is not null group by referrer
  union all select 'langs', coalesce(lang, '?'), '', count(*), count(distinct visitor) from vw group by lang
$$;
revoke execute on function public.analytics_day_rows(date) from public, anon, authenticated;

create or replace function public.analytics_day_totals(p_day date)
returns table (views bigint, visitors bigint, unique_views bigint, members bigint, verse_clicks bigint)
language sql
stable
security definer
set search_path = public
as $$
  select count(*) filter (where kind = 'view'),
         count(distinct visitor),
         count(distinct (visitor, path)) filter (where kind = 'view'),
         count(distinct member),
         count(*) filter (where kind = 'verse')
    from public.analytics_events
   where day = p_day
$$;
revoke execute on function public.analytics_day_totals(date) from public, anon, authenticated;

-- ---- rollups (A3) ------------------------------------------------------------------

create table public.analytics_daily (
  day date not null,
  dim text not null,
  key text not null,
  extra text not null default '',
  n bigint not null,
  u bigint not null,
  primary key (day, dim, key, extra)
);
create table public.analytics_daily_totals (
  day date primary key,
  views bigint not null,
  visitors bigint not null,
  unique_views bigint not null,
  members bigint not null,
  verse_clicks bigint not null
);
alter table public.analytics_daily enable row level security;
alter table public.analytics_daily_totals enable row level security;
revoke all on public.analytics_daily, public.analytics_daily_totals from anon, authenticated;

-- Summarise one finished day. Idempotent: re-running replaces that day.
create or replace function public.analytics_rollup(p_day date)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  delete from public.analytics_daily where day = p_day;
  delete from public.analytics_daily_totals where day = p_day;
  insert into public.analytics_daily (day, dim, key, extra, n, u)
    select p_day, r.dim, r.key, coalesce(r.extra, ''), r.n, r.u from public.analytics_day_rows(p_day) r where r.key is not null;
  insert into public.analytics_daily_totals (day, views, visitors, unique_views, members, verse_clicks)
    select p_day, t.* from public.analytics_day_totals(p_day) t;
end;
$$;
revoke execute on function public.analytics_rollup(date) from public, anon, authenticated;

-- Every finished day that has events but no rollup yet.
create or replace function public.analytics_rollup_pending()
returns int
language plpgsql
security definer
set search_path = public
as $$
declare
  d date;
  n int := 0;
begin
  for d in
    select distinct e.day from public.analytics_events e
     where e.day < public.analytics_today()
       and not exists (select 1 from public.analytics_daily_totals t where t.day = e.day)
     order by 1
  loop
    perform public.analytics_rollup(d);
    n := n + 1;
  end loop;
  return n;
end;
$$;
revoke execute on function public.analytics_rollup_pending() from public, anon, authenticated;

-- ---- the report (A2, A3, A4, A5) ---------------------------------------------------------

-- Totals for a range: rollups for finished days, live counts for the rest.
create or replace function public.analytics_range_totals(p_from date, p_to date)
returns table (views bigint, visitors bigint, unique_views bigint, members bigint, verse_clicks bigint)
language sql
stable
security definer
set search_path = public
as $$
  with days as (select generate_series(p_from, p_to, interval '1 day')::date as day),
  t as (
    select r.views, r.visitors, r.unique_views, r.members, r.verse_clicks
      from public.analytics_daily_totals r where r.day between p_from and p_to
    union all
    select x.* from days d cross join lateral public.analytics_day_totals(d.day) x
     where not exists (select 1 from public.analytics_daily_totals r where r.day = d.day)
  )
  select coalesce(sum(t.views), 0)::bigint, coalesce(sum(t.visitors), 0)::bigint, coalesce(sum(t.unique_views), 0)::bigint,
         coalesce(sum(t.members), 0)::bigint, coalesce(sum(t.verse_clicks), 0)::bigint
    from t
$$;
revoke execute on function public.analytics_range_totals(date, date) from public, anon, authenticated;

-- Everything /mod/traffic shows for a range of days, as one JSON document.
-- Staff only: anyone else gets null.
create or replace function public.analytics_report(p_from date, p_to date)
returns jsonb
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  result jsonb;
  v_len int := greatest(1, p_to - p_from + 1);
begin
  if not public.is_staff() then
    return null;
  end if;
  if p_to < p_from or v_len > 800 then
    raise exception 'range must be 1 to 800 days' using errcode = '22023';
  end if;
  with days as (select generate_series(p_from, p_to, interval '1 day')::date as day),
  rolled as (select day from public.analytics_daily_totals where day between p_from and p_to),
  per_day as (
    select r.day, r.views, r.visitors, r.unique_views, r.members, r.verse_clicks
      from public.analytics_daily_totals r where r.day between p_from and p_to
    union all
    select d.day, x.* from days d cross join lateral public.analytics_day_totals(d.day) x
     where d.day not in (select day from rolled)
  ),
  rows as (
    select r.dim, r.key, r.extra, r.n, r.u from public.analytics_daily r where r.day between p_from and p_to
    union all
    select x.dim, x.key, coalesce(x.extra, ''), x.n, x.u from days d cross join lateral public.analytics_day_rows(d.day) x
     where d.day not in (select day from rolled) and x.key is not null
  ),
  agg as (select dim, key, extra, sum(n)::bigint as n, sum(u)::bigint as u from rows group by dim, key, extra),
  ranked as (select *, row_number() over (partition by dim order by n desc, key) as rk from agg),
  searches as (
    select query, lang, count(*) as n, count(*) filter (where results = 0) as empty
      from public.search_log
     where (searched_at at time zone 'Asia/Kolkata')::date between p_from and p_to
     group by query, lang
  )
  select jsonb_build_object(
    'from', p_from,
    'to', p_to,
    'totals', (select to_jsonb(t) from public.analytics_range_totals(p_from, p_to) t),
    'previous', (select to_jsonb(t) from public.analytics_range_totals(p_from - v_len, p_from - 1) t),
    'daily', (
      select coalesce(jsonb_agg(jsonb_build_object(
        'day', d.day,
        'views', coalesce(p.views, 0), 'visitors', coalesce(p.visitors, 0), 'unique_views', coalesce(p.unique_views, 0),
        'members', coalesce(p.members, 0), 'verse_clicks', coalesce(p.verse_clicks, 0)
      ) order by d.day), '[]'::jsonb)
      from days d left join per_day p on p.day = d.day
    ),
    'top', (
      select coalesce(jsonb_object_agg(dim, list), '{}'::jsonb)
      from (
        select dim, jsonb_agg(jsonb_build_object('key', key, 'extra', nullif(extra, ''), 'n', n, 'u', u) order by rk) as list
          from ranked
         where rk <= case when dim in ('books', 'verse_books', 'sections') then 80 else 25 end
         group by dim
      ) q
    ),
    'searches', (
      select coalesce(jsonb_agg(jsonb_build_object('key', query, 'extra', lang, 'n', n, 'u', empty) order by n desc, query), '[]'::jsonb)
      from (select * from searches order by n desc, query limit 25) s
    ),
    'searches_empty', (
      select coalesce(jsonb_agg(jsonb_build_object('key', query, 'extra', lang, 'n', empty, 'u', n) order by empty desc, query), '[]'::jsonb)
      from (select * from searches where empty > 0 order by empty desc, query limit 15) s
    )
  ) into result;
  return result;
end;
$$;
revoke execute on function public.analytics_report(date, date) from public, anon;
grant execute on function public.analytics_report(date, date) to authenticated;

-- The last 30 minutes, for the "now" panel (A5). Staff only.
create or replace function public.analytics_now()
returns jsonb
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  result jsonb;
begin
  if not public.is_staff() then
    return null;
  end if;
  with e as (select * from public.analytics_events where at > now() - interval '30 minutes')
  select jsonb_build_object(
    'views', (select count(*) from e where kind = 'view'),
    'visitors', (select count(distinct visitor) from e),
    'verse_clicks', (select count(*) from e where kind = 'verse'),
    'pages', (
      select coalesce(jsonb_agg(jsonb_build_object('key', path, 'n', n) order by n desc, path), '[]'::jsonb)
      from (select path, count(*) as n from e where kind = 'view' group by path order by n desc, path limit 8) p
    ),
    'countries', (
      select coalesce(jsonb_agg(jsonb_build_object('key', c, 'n', n) order by n desc, c), '[]'::jsonb)
      from (select coalesce(country, '?') as c, count(distinct visitor) as n from e group by 1 order by n desc, c limit 6) c
    )
  ) into result;
  return result;
end;
$$;
revoke execute on function public.analytics_now() from public, anon;
grant execute on function public.analytics_now() to authenticated;

-- ---- retention ---------------------------------------------------------------------------

-- 06:00 India time: summarise yesterday; drop salts older than today, so their
-- hashes can no longer be recomputed from an IP address; raw events go after
-- 90 days and rollups after two years.
select cron.schedule('analytics-rollup', '30 0 * * *', $$select public.analytics_rollup_pending()$$);
select cron.schedule('analytics-drop-salts', '35 0 * * *',
  $$delete from public.analytics_salt where day < public.analytics_today()$$);
select cron.schedule('analytics-purge', '40 0 * * *',
  $$delete from public.analytics_events where day < public.analytics_today() - 90;
    delete from public.analytics_daily where day < public.analytics_today() - 730;
    delete from public.analytics_daily_totals where day < public.analytics_today() - 730$$);
