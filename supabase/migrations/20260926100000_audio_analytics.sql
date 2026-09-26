-- A7: Audio Bible listening in the site analytics (docs/feature_analytics.md,
-- docs/feature_audio.md). The player sends `audio` events through the same
-- beacon, under the same rules: no cookies, daily hashes, GPC/DNT honoured.
--
--   action  play   a reader started a chapter (verse set when started from a verse)
--           next   the next or previous chapter started, by itself or by ⏮/⏭
--           jump   a jump to a verse inside the playing chapter
--           end    a chapter heard to its end
--           time   seconds listened (amount), sent when the chapter changes,
--                  the bar closes or the tab is hidden
--   version the recording's version code (IRVTAM, BSB, …)

alter table public.analytics_events
  add column action text,
  add column version text,
  add column amount int;
alter table public.analytics_events drop constraint analytics_events_kind_check;
alter table public.analytics_events add constraint analytics_events_kind_check check (kind in ('view', 'verse', 'audio'));

alter table public.analytics_daily_totals
  add column audio_starts bigint not null default 0,
  add column listeners bigint not null default 0,
  add column listen_seconds bigint not null default 0,
  add column audio_ends bigint not null default 0;

-- ---- collection ---------------------------------------------------------------------

drop function public.track(text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, int);
create function public.track(
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
  p_chapter int default null,
  p_action text default null,
  p_version text default null,
  p_amount int default null
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
  v_audio boolean := p_kind = 'audio';
  clip constant int := 200;
begin
  if p_kind not in ('view', 'verse', 'audio') or p_path is null or p_path !~ '^/' then
    return;
  end if;
  if v_audio and (p_action is null or p_action not in ('play', 'next', 'jump', 'end', 'time')) then
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
    (day, kind, path, route, verse, book, chapter, visitor, member, country, region, city, device, os, browser, screen, referrer, lang,
     action, version, amount)
  values (
    v_day, p_kind, left(p_path, clip), left(p_route, clip),
    case when p_kind in ('verse', 'audio') and p_verse ~ '^[1-3A-Z]{3}\.[0-9]{1,3}\.[0-9]{1,3}$' then p_verse end,
    case when p_book ~ '^[1-3A-Z]{3}$' then p_book end,
    case when p_chapter between 1 and 150 then p_chapter end,
    v_visitor, v_member,
    left(upper(p_country), 2), left(p_region, 60), left(p_city, 80),
    case when p_device in ('mobile', 'tablet', 'desktop') then p_device end,
    left(p_os, 30), left(p_browser, 30),
    case when p_screen ~ '^[0-9]{2,5}x[0-9]{2,5}$' then p_screen end,
    left(lower(p_referrer), 120),
    case when p_lang in ('ta', 'en') then p_lang end,
    case when v_audio then p_action end,
    case when v_audio and p_version ~ '^[A-Z0-9]{2,12}$' then p_version end,
    case when v_audio and p_action = 'time' and p_amount between 1 and 3600 then p_amount end
  );
end;
$$;
revoke execute on function public.track(text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, int, text, text, int) from public;
grant execute on function public.track(text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, text, int, text, text, int) to anon, authenticated;

-- ---- one day, summarised ------------------------------------------------------------

-- Every ranked dimension for one day: n = events, u = distinct visitors that day.
-- Audio: plays count `play` and `next`; audio_time sums seconds listened.
create or replace function public.analytics_day_rows(p_day date)
returns table (dim text, key text, extra text, n bigint, u bigint)
language sql
stable
security definer
set search_path = public
as $$
  with e as (select * from public.analytics_events where day = p_day),
  vw as (select * from e where kind = 'view'),
  au as (select * from e where kind = 'audio')
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
  union all select 'audio_versions', version, '', count(*), count(distinct visitor) from au where action in ('play', 'next') and version is not null group by version
  union all select 'audio_time', version, '', coalesce(sum(amount), 0), count(distinct visitor) from au where action = 'time' and version is not null group by version
  union all select 'audio_chapters', book || '.' || chapter, coalesce(version, '?'), count(*), count(distinct visitor) from au where action in ('play', 'next') and book is not null and chapter is not null group by book, chapter, version
  union all select 'audio_sources', case when action = 'play' and verse is not null then 'verse' else action end, '', count(*), count(distinct visitor) from au where action in ('play', 'next', 'jump') group by 2
  union all select 'audio_verses', verse, '', count(*), count(distinct visitor) from au where action in ('play', 'jump') and verse is not null group by verse
$$;
revoke execute on function public.analytics_day_rows(date) from public, anon, authenticated;

drop function public.analytics_day_totals(date);
create function public.analytics_day_totals(p_day date)
returns table (views bigint, visitors bigint, unique_views bigint, members bigint, verse_clicks bigint,
               audio_starts bigint, listeners bigint, listen_seconds bigint, audio_ends bigint)
language sql
stable
security definer
set search_path = public
as $$
  select count(*) filter (where kind = 'view'),
         count(distinct visitor),
         count(distinct (visitor, path)) filter (where kind = 'view'),
         count(distinct member),
         count(*) filter (where kind = 'verse'),
         count(*) filter (where kind = 'audio' and action in ('play', 'next')),
         count(distinct visitor) filter (where kind = 'audio'),
         coalesce(sum(amount) filter (where kind = 'audio' and action = 'time'), 0)::bigint,
         count(*) filter (where kind = 'audio' and action = 'end')
    from public.analytics_events
   where day = p_day
$$;
revoke execute on function public.analytics_day_totals(date) from public, anon, authenticated;

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
  insert into public.analytics_daily_totals
    (day, views, visitors, unique_views, members, verse_clicks, audio_starts, listeners, listen_seconds, audio_ends)
    select p_day, t.views, t.visitors, t.unique_views, t.members, t.verse_clicks, t.audio_starts, t.listeners, t.listen_seconds, t.audio_ends
      from public.analytics_day_totals(p_day) t;
end;
$$;
revoke execute on function public.analytics_rollup(date) from public, anon, authenticated;

-- ---- the report ------------------------------------------------------------------------

drop function public.analytics_range_totals(date, date);
create function public.analytics_range_totals(p_from date, p_to date)
returns table (views bigint, visitors bigint, unique_views bigint, members bigint, verse_clicks bigint,
               audio_starts bigint, listeners bigint, listen_seconds bigint, audio_ends bigint)
language sql
stable
security definer
set search_path = public
as $$
  with days as (select generate_series(p_from, p_to, interval '1 day')::date as day),
  t as (
    select r.views, r.visitors, r.unique_views, r.members, r.verse_clicks, r.audio_starts, r.listeners, r.listen_seconds, r.audio_ends
      from public.analytics_daily_totals r where r.day between p_from and p_to
    union all
    select x.views, x.visitors, x.unique_views, x.members, x.verse_clicks, x.audio_starts, x.listeners, x.listen_seconds, x.audio_ends
      from days d cross join lateral public.analytics_day_totals(d.day) x
     where not exists (select 1 from public.analytics_daily_totals r where r.day = d.day)
  )
  select coalesce(sum(t.views), 0)::bigint, coalesce(sum(t.visitors), 0)::bigint, coalesce(sum(t.unique_views), 0)::bigint,
         coalesce(sum(t.members), 0)::bigint, coalesce(sum(t.verse_clicks), 0)::bigint,
         coalesce(sum(t.audio_starts), 0)::bigint, coalesce(sum(t.listeners), 0)::bigint,
         coalesce(sum(t.listen_seconds), 0)::bigint, coalesce(sum(t.audio_ends), 0)::bigint
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
    select r.day, r.views, r.visitors, r.unique_views, r.members, r.verse_clicks, r.audio_starts, r.listeners, r.listen_seconds, r.audio_ends
      from public.analytics_daily_totals r where r.day between p_from and p_to
    union all
    select d.day, x.views, x.visitors, x.unique_views, x.members, x.verse_clicks, x.audio_starts, x.listeners, x.listen_seconds, x.audio_ends
      from days d cross join lateral public.analytics_day_totals(d.day) x
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
        'members', coalesce(p.members, 0), 'verse_clicks', coalesce(p.verse_clicks, 0),
        'audio_starts', coalesce(p.audio_starts, 0), 'listeners', coalesce(p.listeners, 0),
        'listen_seconds', coalesce(p.listen_seconds, 0), 'audio_ends', coalesce(p.audio_ends, 0)
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

-- The last 30 minutes, for the "now" panel, with who is listening. Staff only.
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
    'listeners', (select count(distinct visitor) from e where kind = 'audio'),
    'pages', (
      select coalesce(jsonb_agg(jsonb_build_object('key', path, 'n', n) order by n desc, path), '[]'::jsonb)
      from (select path, count(*) as n from e where kind = 'view' group by path order by n desc, path limit 8) p
    ),
    'listening', (
      select coalesce(jsonb_agg(jsonb_build_object('key', k, 'extra', version, 'n', n) order by n desc, k), '[]'::jsonb)
      from (
        select book || '.' || chapter as k, version, count(distinct visitor) as n
          from e where kind = 'audio' and book is not null and chapter is not null
         group by book, chapter, version order by n desc, k limit 6
      ) a
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
