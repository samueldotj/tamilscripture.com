-- A8: accounts, reading plans and traffic sources on /mod/traffic
-- (docs/feature_analytics.md). Counts only, staff only, like the rest of the
-- report: no moderator can see who signed up, who signed in or who follows a
-- plan.
--
--   analytics_accounts(from, to)  sign-ups, sign-ins and active signed-in users
--                                 over the last day, week and month; sign-ups
--                                 per day in the range; the peak days
--   analytics_plans(from, to)     readers on a plan, the most-followed plans
--   analytics_source(referrer)    a referrer host (or tag) as a source: google,
--                                 whatsapp, facebook, direct, …
--   analytics_report(from, to)    now also carries `sources`
--
-- The collector now marks each visit's landing page: '(direct)' when it came
-- with no referrer, 'utm:<tag>' when the link carried ?utm_source=<tag>, else
-- the referring host as before (Android apps arrive as 'com.whatsapp' and the
-- like, from Chrome's android-app:// referrer).

-- ---- sources -------------------------------------------------------------------------

create or replace function public.analytics_source(p_referrer text)
returns text
language sql
immutable
as $$
  select case
    when r is null or r = '' then null
    when r = '(direct)' then 'direct'
    when r ~ '(^|\.)(chatgpt\.com|openai\.com|perplexity\.ai|claude\.ai|gemini\.google\.com|copilot\.microsoft\.com)$'
      or r in ('chatgpt', 'openai', 'perplexity', 'claude', 'gemini', 'copilot') then 'ai'
    when r ~ '(^|\.)(mail\.google\.com|outlook\.live\.com|outlook\.office\.com|outlook\.office365\.com|mail\.yahoo\.com)$'
      or r like 'com.google.android.gm%' or r like 'com.microsoft.office.outlook%'
      or r in ('email', 'mail', 'newsletter', 'gmail') then 'email'
    when r ~ '(^|\.)(whatsapp\.com|whatsapp\.net|wa\.me)$' or r like 'com.whatsapp%' or r in ('whatsapp', 'wa') then 'whatsapp'
    when r ~ '(^|\.)(facebook\.com|fb\.com|fb\.me|messenger\.com)$' or r like 'com.facebook.%'
      or r in ('facebook', 'fb', 'messenger') then 'facebook'
    when r ~ '(^|\.)instagram\.com$' or r like 'com.instagram.%' or r in ('instagram', 'ig') then 'instagram'
    when r ~ '(^|\.)(youtube\.com|youtu\.be)$' or r = 'com.google.android.youtube' or r in ('youtube', 'yt') then 'youtube'
    when r ~ '(^|\.)(t\.me|telegram\.me|telegram\.org)$' or r like 'org.telegram.%' or r in ('telegram', 'tg') then 'telegram'
    when r ~ '(^|\.)(t\.co|twitter\.com|x\.com)$' or r = 'com.twitter.android' or r in ('twitter', 'x') then 'x'
    when r ~ '(^|\.)(linkedin\.com|lnkd\.in)$' or r = 'com.linkedin.android' or r = 'linkedin' then 'linkedin'
    when r ~ '(^|\.)reddit\.com$' or r = 'com.reddit.frontpage' or r = 'reddit' then 'reddit'
    when r ~ '(^|\.)google\.[a-z]{2,3}(\.[a-z]{2})?$' or r like 'com.google.android.googlequicksearchbox%' or r = 'google' then 'google'
    when r ~ '(^|\.)bing\.com$' or r = 'bing' then 'bing'
    when r ~ '(^|\.)duckduckgo\.com$' or r = 'duckduckgo' then 'duckduckgo'
    when r ~ '(^|\.)(yahoo\.com|yandex\.[a-z]+|baidu\.com|ecosia\.org|search\.brave\.com|startpage\.com|qwant\.com)$' then 'search'
    else 'other'
  end
  from (select regexp_replace(lower(p_referrer), '^utm:', '') as r) x
$$;

-- ---- accounts ------------------------------------------------------------------------

-- Sign-ups (accounts created), sign-ins (auth.users.last_sign_in_at: a user
-- who signed in at least once in the window) and active signed-in users (a
-- session used in the window: the site refreshes its token hourly while open)
-- over the last 24 hours, 7 days and 30 days. Sign-ups per India day for the
-- range and the one before it, and the busiest days ever. Staff only.
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
    select day, members from public.analytics_daily_totals
    union all
    select public.analytics_today(), (select t.members from public.analytics_day_totals(public.analytics_today()) t)
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

-- ---- reading plans ---------------------------------------------------------------------

-- Signed-in readers on a plan (plans joined while signed out stay in that
-- browser and are not counted), and each plan's readers: all, started in the
-- range, reading in the last 7 days (a passage ticked), passages read.
-- Community plans carry their titles; built-in keys are named by the page.
create or replace function public.analytics_plans(p_from date, p_to date)
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
  with pp as (
    select user_id, plan, cardinality(done) as read, updated_at,
           (created_at at time zone 'Asia/Kolkata')::date as joined,
           updated_at > now() - interval '7 days' and cardinality(done) > 0 as active
      from public.plan_progress
  ),
  per_plan as (
    select plan, count(*) as readers,
           count(*) filter (where joined between p_from and p_to) as started,
           count(*) filter (where active) as active,
           coalesce(sum(read), 0) as passages
      from pp group by plan
  )
  select jsonb_build_object(
    'readers', (select count(distinct user_id) from pp),
    'subscriptions', (select count(*) from pp),
    'started', (select count(*) from pp where joined between p_from and p_to),
    'started_previous', (select count(*) from pp where joined between p_from - v_len and p_from - 1),
    'active', (select count(distinct user_id) from pp where active),
    'plans', (
      select coalesce(jsonb_agg(jsonb_build_object(
               'key', p.plan, 'title_ta', nullif(r.title_ta, ''), 'title_en', nullif(r.title_en, ''),
               'readers', p.readers, 'started', p.started, 'active', p.active, 'passages', p.passages
             ) order by p.readers desc, p.active desc, p.plan), '[]'::jsonb)
        from (select * from per_plan order by readers desc, active desc, plan limit 25) p
        left join public.reading_plans r on r.id::text = p.plan
    )
  ) into result;
  return result;
end;
$$;
revoke execute on function public.analytics_plans(date, date) from public, anon;
grant execute on function public.analytics_plans(date, date) to authenticated;

-- ---- the report, with sources -------------------------------------------------------------

-- As in 20260926100000_audio_analytics.sql, plus `sources`: every referrer row
-- in the range (not only the top 25) summed by analytics_source(). Landings
-- recorded before the collector marked direct visits have no '(direct)' row.
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
    'sources', (
      select coalesce(jsonb_agg(jsonb_build_object('key', k, 'extra', null, 'n', n, 'u', u) order by n desc, k), '[]'::jsonb)
      from (
        select public.analytics_source(key) as k, sum(n)::bigint as n, sum(u)::bigint as u
          from agg where dim = 'referrers' group by 1
      ) s
      where k is not null
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
