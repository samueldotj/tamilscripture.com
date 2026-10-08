-- Traffic report: the moderators' own pages left out, and a filter by where the
-- traffic came from (docs/feature_analytics.md A10).
--
-- * Events on /mod and /mod/* (the queue, this report) are not counted anywhere:
--   the collector stops sending them, and the summaries below skip any already
--   stored.
-- * Rollups are kept per source, 'web' or 'android' (the app, 20261004100000).
--   A web visitor and an app install never share a hash, so every count, the
--   per-day visitor counts included, adds up across sources: "all" is the sum.
-- * analytics_report() and analytics_now() take p_source: null for everything,
--   'web' for the website, 'android' for the app.
--
-- Raw events are kept for 90 days, so the days still held are rolled up again at
-- the end, which splits them by source and drops the /mod events from them.

create or replace function public.analytics_counted(p_path text)
returns boolean
language sql
immutable
as $$ select p_path is not null and p_path <> '/mod' and p_path not like '/mod/%' $$;

-- ---- rollups by source --------------------------------------------------------------------

alter table public.analytics_daily add column source text not null default 'web';
alter table public.analytics_daily drop constraint analytics_daily_pkey;
alter table public.analytics_daily add primary key (day, source, dim, key, extra);

alter table public.analytics_daily_totals add column source text not null default 'web';
alter table public.analytics_daily_totals drop constraint analytics_daily_totals_pkey;
alter table public.analytics_daily_totals add primary key (day, source);

-- As in 20261006100000_share_analytics.sql, for one source, without /mod.
drop function public.analytics_day_rows(date);
create function public.analytics_day_rows(p_day date, p_source text)
returns table (dim text, key text, extra text, n bigint, u bigint)
language sql
stable
security definer
set search_path = public
as $$
  with e as (
    select * from public.analytics_events
     where day = p_day and (p_source is null or source = p_source) and public.analytics_counted(path)
  ),
  vw as (select * from e where kind = 'view'),
  au as (select * from e where kind = 'audio'),
  sh as (select * from e where kind = 'share')
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
  union all select 'share_methods', action, '', count(*), count(distinct visitor) from sh where action is not null group by action
  union all select 'share_verses', verse, '', count(*), count(distinct visitor) from sh where verse is not null group by verse
  union all select 'share_templates', split_part(detail, '.', 1), '', count(*), count(distinct visitor) from sh where detail is not null group by 2
  union all select 'share_sizes', split_part(detail, '.', 2), '', count(*), count(distinct visitor) from sh where detail is not null group by 2
$$;
revoke execute on function public.analytics_day_rows(date, text) from public, anon, authenticated;

drop function public.analytics_day_totals(date);
create function public.analytics_day_totals(p_day date, p_source text)
returns table (views bigint, visitors bigint, unique_views bigint, members bigint, verse_clicks bigint,
               audio_starts bigint, listeners bigint, listen_seconds bigint, audio_ends bigint,
               shares bigint, sharers bigint, image_shares bigint)
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
         count(*) filter (where kind = 'audio' and action = 'end'),
         count(*) filter (where kind = 'share'),
         count(distinct visitor) filter (where kind = 'share'),
         count(*) filter (where kind = 'share' and action in ('download', 'sheet', 'copy'))
    from public.analytics_events
   where day = p_day and (p_source is null or source = p_source) and public.analytics_counted(path)
$$;
revoke execute on function public.analytics_day_totals(date, text) from public, anon, authenticated;

-- Summarise one finished day, a row of totals for each source. Idempotent.
create or replace function public.analytics_rollup(p_day date)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  s text;
begin
  delete from public.analytics_daily where day = p_day;
  delete from public.analytics_daily_totals where day = p_day;
  foreach s in array array['web', 'android'] loop
    insert into public.analytics_daily (day, source, dim, key, extra, n, u)
      select p_day, s, r.dim, r.key, coalesce(r.extra, ''), r.n, r.u from public.analytics_day_rows(p_day, s) r where r.key is not null;
    insert into public.analytics_daily_totals
      (day, source, views, visitors, unique_views, members, verse_clicks, audio_starts, listeners, listen_seconds, audio_ends,
       shares, sharers, image_shares)
      select p_day, s, t.views, t.visitors, t.unique_views, t.members, t.verse_clicks, t.audio_starts, t.listeners, t.listen_seconds, t.audio_ends,
             t.shares, t.sharers, t.image_shares
        from public.analytics_day_totals(p_day, s) t;
  end loop;
end;
$$;
revoke execute on function public.analytics_rollup(date) from public, anon, authenticated;

-- ---- the report ------------------------------------------------------------------------

drop function public.analytics_range_totals(date, date);
create function public.analytics_range_totals(p_from date, p_to date, p_source text default null)
returns table (views bigint, visitors bigint, unique_views bigint, members bigint, verse_clicks bigint,
               audio_starts bigint, listeners bigint, listen_seconds bigint, audio_ends bigint,
               shares bigint, sharers bigint, image_shares bigint)
language sql
stable
security definer
set search_path = public
as $$
  with days as (select generate_series(p_from, p_to, interval '1 day')::date as day),
  t as (
    select r.views, r.visitors, r.unique_views, r.members, r.verse_clicks, r.audio_starts, r.listeners, r.listen_seconds, r.audio_ends,
           r.shares, r.sharers, r.image_shares
      from public.analytics_daily_totals r
     where r.day between p_from and p_to and (p_source is null or r.source = p_source)
    union all
    select x.views, x.visitors, x.unique_views, x.members, x.verse_clicks, x.audio_starts, x.listeners, x.listen_seconds, x.audio_ends,
           x.shares, x.sharers, x.image_shares
      from days d cross join lateral public.analytics_day_totals(d.day, p_source) x
     where not exists (select 1 from public.analytics_daily_totals r where r.day = d.day)
  )
  select coalesce(sum(t.views), 0)::bigint, coalesce(sum(t.visitors), 0)::bigint, coalesce(sum(t.unique_views), 0)::bigint,
         coalesce(sum(t.members), 0)::bigint, coalesce(sum(t.verse_clicks), 0)::bigint,
         coalesce(sum(t.audio_starts), 0)::bigint, coalesce(sum(t.listeners), 0)::bigint,
         coalesce(sum(t.listen_seconds), 0)::bigint, coalesce(sum(t.audio_ends), 0)::bigint,
         coalesce(sum(t.shares), 0)::bigint, coalesce(sum(t.sharers), 0)::bigint, coalesce(sum(t.image_shares), 0)::bigint
    from t
$$;
revoke execute on function public.analytics_range_totals(date, date, text) from public, anon, authenticated;

-- As in 20261006100000_share_analytics.sql, for one source or all of them.
drop function public.analytics_report(date, date);
create function public.analytics_report(p_from date, p_to date, p_source text default null)
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
  if p_source is not null and p_source not in ('web', 'android') then
    raise exception 'source must be web or android' using errcode = '22023';
  end if;
  with days as (select generate_series(p_from, p_to, interval '1 day')::date as day),
  rolled as (select distinct day from public.analytics_daily_totals where day between p_from and p_to),
  per_day_parts as (
    select r.day, r.views, r.visitors, r.unique_views, r.members, r.verse_clicks, r.audio_starts, r.listeners, r.listen_seconds, r.audio_ends,
           r.shares, r.sharers, r.image_shares
      from public.analytics_daily_totals r
     where r.day between p_from and p_to and (p_source is null or r.source = p_source)
    union all
    select d.day, x.views, x.visitors, x.unique_views, x.members, x.verse_clicks, x.audio_starts, x.listeners, x.listen_seconds, x.audio_ends,
           x.shares, x.sharers, x.image_shares
      from days d cross join lateral public.analytics_day_totals(d.day, p_source) x
     where d.day not in (select day from rolled)
  ),
  per_day as (
    select day, sum(views) as views, sum(visitors) as visitors, sum(unique_views) as unique_views, sum(members) as members,
           sum(verse_clicks) as verse_clicks, sum(audio_starts) as audio_starts, sum(listeners) as listeners,
           sum(listen_seconds) as listen_seconds, sum(audio_ends) as audio_ends,
           sum(shares) as shares, sum(sharers) as sharers, sum(image_shares) as image_shares
      from per_day_parts group by day
  ),
  rows as (
    select r.dim, r.key, r.extra, r.n, r.u from public.analytics_daily r
     where r.day between p_from and p_to and (p_source is null or r.source = p_source)
    union all
    select x.dim, x.key, coalesce(x.extra, ''), x.n, x.u from days d cross join lateral public.analytics_day_rows(d.day, p_source) x
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
    'source', p_source,
    'totals', (select to_jsonb(t) from public.analytics_range_totals(p_from, p_to, p_source) t),
    'previous', (select to_jsonb(t) from public.analytics_range_totals(p_from - v_len, p_from - 1, p_source) t),
    'daily', (
      select coalesce(jsonb_agg(jsonb_build_object(
        'day', d.day,
        'views', coalesce(p.views, 0), 'visitors', coalesce(p.visitors, 0), 'unique_views', coalesce(p.unique_views, 0),
        'members', coalesce(p.members, 0), 'verse_clicks', coalesce(p.verse_clicks, 0),
        'audio_starts', coalesce(p.audio_starts, 0), 'listeners', coalesce(p.listeners, 0),
        'listen_seconds', coalesce(p.listen_seconds, 0), 'audio_ends', coalesce(p.audio_ends, 0),
        'shares', coalesce(p.shares, 0), 'sharers', coalesce(p.sharers, 0), 'image_shares', coalesce(p.image_shares, 0)
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
    'sources', (
      select coalesce(jsonb_agg(jsonb_build_object('key', k, 'extra', null, 'n', n, 'u', u) order by n desc, k), '[]'::jsonb)
      from (
        select public.analytics_source(key) as k, sum(n)::bigint as n, sum(u)::bigint as u
          from agg where dim = 'referrers' group by 1
      ) s
      where k is not null
    ),
    -- The search log does not record where a search came from: always every source.
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
revoke execute on function public.analytics_report(date, date, text) from public, anon;
grant execute on function public.analytics_report(date, date, text) to authenticated;

-- As in 20260926100000_audio_analytics.sql, for one source or all, without /mod.
drop function public.analytics_now();
create function public.analytics_now(p_source text default null)
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
  with e as (
    select * from public.analytics_events
     where at > now() - interval '30 minutes' and (p_source is null or source = p_source) and public.analytics_counted(path)
  )
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
revoke execute on function public.analytics_now(text) from public, anon;
grant execute on function public.analytics_now(text) to authenticated;

-- As in 20260926130000_accounts_plans_sources.sql, with the busiest day for signed-in
-- users summed over sources.
create or replace function public.analytics_accounts(p_from date, p_to date)
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
  with u as (
    select id, created_at, last_sign_in_at, (created_at at time zone 'Asia/Kolkata')::date as joined
      from auth.users where deleted_at is null
  ),
  s as (select user_id, updated_at from auth.sessions),
  members as (
    select day, sum(members) as members from public.analytics_daily_totals group by day
    union all
    select public.analytics_today(), (select t.members from public.analytics_day_totals(public.analytics_today(), null) t)
  )
  select jsonb_build_object(
    'total', (select count(*) from u),
    'signups', jsonb_build_object(
      'day', (select count(*) from u where created_at > now() - interval '1 day'),
      'week', (select count(*) from u where created_at > now() - interval '7 days'),
      'month', (select count(*) from u where created_at > now() - interval '30 days')),
    'signins', jsonb_build_object(
      'day', (select count(*) from u where last_sign_in_at > now() - interval '1 day'),
      'week', (select count(*) from u where last_sign_in_at > now() - interval '7 days'),
      'month', (select count(*) from u where last_sign_in_at > now() - interval '30 days')),
    'active', jsonb_build_object(
      'day', (select count(distinct user_id) from s where updated_at > now() - interval '1 day'),
      'week', (select count(distinct user_id) from s where updated_at > now() - interval '7 days'),
      'month', (select count(distinct user_id) from s where updated_at > now() - interval '30 days')),
    'range', (select count(*) from u where joined between p_from and p_to),
    'previous', (select count(*) from u where joined between p_from - v_len and p_from - 1),
    'daily', (
      select coalesce(jsonb_agg(jsonb_build_object('day', d.day, 'n', coalesce(c.n, 0)) order by d.day), '[]'::jsonb)
        from (select generate_series(p_from, p_to, interval '1 day')::date as day) d
        left join (select joined, count(*) as n from u group by joined) c on c.joined = d.day
    ),
    'peak_signups', (
      select jsonb_build_object('day', joined, 'n', n)
        from (select joined, count(*) as n from u group by joined) c order by n desc, joined desc limit 1
    ),
    'peak_members', (
      select jsonb_build_object('day', day, 'n', members)
        from members where members > 0 order by members desc, day desc limit 1
    )
  ) into result;
  return result;
end;
$$;
revoke execute on function public.analytics_accounts(date, date) from public, anon;
grant execute on function public.analytics_accounts(date, date) to authenticated;

-- ---- the days still held, again ------------------------------------------------------------

do $$
declare
  d date;
begin
  for d in select distinct day from public.analytics_events where day < public.analytics_today() order by 1 loop
    perform public.analytics_rollup(d);
  end loop;
end;
$$;
