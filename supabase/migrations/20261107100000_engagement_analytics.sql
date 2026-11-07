-- Engagement in the site analytics (docs/feature_analytics.md A11). The website
-- sends a `goal` event the first time in a visit a reader becomes engaged, under
-- the beacon's usual rules (no cookies, daily hashes, GPC/DNT honoured):
--
--   action  reader    at least two different pages (not the home page), adding
--                     up to two minutes on screen; pages seen under 10 s ignored
--           listener  60 s of the Audio Bible heard
--           atlas     60 s on the atlas pages
--           psalms    60 s in the Psalms explorer
--
-- The rules are the same as the Google Ads conversions (lib/analytics/engagement.ts),
-- but these are counted for every reader. Summaries keep, per day, the engaged
-- visitors for each goal (`goals`) and, for each landing referrer, the visitors
-- from it who became engaged (`goal_referrers`), so the report can show what
-- share of each source's visitors read on. analytics_engagement() is the report.
--
-- Also: ad landings, tagged utm:google-ads by the beacon, are their own source.

alter table public.analytics_events drop constraint analytics_events_kind_check;
alter table public.analytics_events add constraint analytics_events_kind_check
  check (kind in ('view', 'verse', 'audio', 'share', 'goal', 'read', 'search', 'commentary', 'plan', 'download'));

-- ---- collection ---------------------------------------------------------------------

-- As in 20261006100000_share_analytics.sql, plus `goal`.
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
  p_chapter int default null,
  p_action text default null,
  p_version text default null,
  p_amount int default null,
  p_detail text default null
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
  v_share boolean := p_kind = 'share';
  v_goal boolean := p_kind = 'goal';
  clip constant int := 200;
begin
  if p_kind not in ('view', 'verse', 'audio', 'share', 'goal') or p_path is null or p_path !~ '^/' then
    return;
  end if;
  if v_audio and (p_action is null or p_action not in ('play', 'next', 'jump', 'end', 'time')) then
    return;
  end if;
  if v_share and (p_action is null or p_action not in ('link', 'large', 'download', 'sheet', 'copy')) then
    return;
  end if;
  if v_goal and (p_action is null or p_action not in ('reader', 'listener', 'atlas', 'psalms')) then
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
     action, version, amount, detail)
  values (
    v_day, p_kind, left(p_path, clip), left(p_route, clip),
    case when p_kind in ('verse', 'audio', 'share') and p_verse ~ '^[1-3A-Z]{3}\.[0-9]{1,3}\.[0-9]{1,3}$' then p_verse end,
    case when p_book ~ '^[1-3A-Z]{3}$' then p_book end,
    case when p_chapter between 1 and 150 then p_chapter end,
    v_visitor, v_member,
    left(upper(p_country), 2), left(p_region, 60), left(p_city, 80),
    case when p_device in ('mobile', 'tablet', 'desktop') then p_device end,
    left(p_os, 30), left(p_browser, 30),
    case when p_screen ~ '^[0-9]{2,5}x[0-9]{2,5}$' then p_screen end,
    left(lower(p_referrer), 120),
    case when p_lang in ('ta', 'en') then p_lang end,
    case when v_audio or v_share or v_goal then p_action end,
    case when (v_audio or v_share) and p_version ~ '^[A-Z0-9]{2,12}$' then p_version end,
    case when v_audio and p_action = 'time' and p_amount between 1 and 3600 then p_amount end,
    case when v_share and p_action in ('download', 'sheet', 'copy') and p_detail ~ '^[a-z]{1,12}\.[a-z]{1,12}\.[a-z]{1,12}$' then p_detail end
  );
end;
$$;

-- ---- sources ---------------------------------------------------------------------------

-- As in 20260926130000_accounts_plans_sources.sql, plus google_ads: a landing from
-- one of our Google ads (the beacon tags gclid, gbraid and wbraid as google-ads).
create or replace function public.analytics_source(p_referrer text)
returns text
language sql
immutable
as $$
  select case
    when r is null or r = '' then null
    when r = '(direct)' then 'direct'
    when r in ('google-ads', 'googleads', 'adwords', 'gads') then 'google_ads'
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

-- ---- one day, summarised ------------------------------------------------------------

-- As in 20261007100000_traffic_source_filter.sql, plus engagement:
--   goals           key goal; n events, u engaged visitors
--   goal_referrers  key the landing referrer, extra goal; n = u = visitors who
--                   landed from it that day and reached the goal
create or replace function public.analytics_day_rows(p_day date, p_source text)
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
  sh as (select * from e where kind = 'share'),
  gl as (select distinct visitor, action from e where kind = 'goal' and action is not null),
  landed as (select distinct on (visitor) visitor, referrer from vw where referrer is not null order by visitor, at)
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
  union all select 'goals', action, '', count(*), count(distinct visitor) from e where kind = 'goal' and action is not null group by action
  union all select 'goal_referrers', l.referrer, g.action, count(*), count(*) from gl g join landed l using (visitor) group by l.referrer, g.action
$$;
revoke execute on function public.analytics_day_rows(date, text) from public, anon, authenticated;

-- ---- the report ------------------------------------------------------------------------

-- Engaged visitors for a range (staff only), from the nightly summaries for
-- finished days and live counts for the rest:
--   daily     [{day, reader, listener, atlas, psalms}]  engaged visitors per day
--   range     {reader, listener, atlas, psalms}         summed over the range
--   previous  the same for the range just before
--   sources   [{key, extra, u}]  key an analytics_source() source, extra a goal,
--             u visitors from that source who reached it (compare with the
--             report's sources[].u, the visitors from each source)
create or replace function public.analytics_engagement(p_from date, p_to date, p_source text default null)
returns jsonb
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  result jsonb;
  v_len int := greatest(1, p_to - p_from + 1);
  v_start date := p_from - greatest(1, p_to - p_from + 1);
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
  with days as (select generate_series(v_start, p_to, interval '1 day')::date as day),
  rolled as (select distinct day from public.analytics_daily_totals where day between v_start and p_to),
  rows as (
    select r.day, r.dim, r.key, r.extra, r.u from public.analytics_daily r
     where r.day between v_start and p_to and r.dim in ('goals', 'goal_referrers') and (p_source is null or r.source = p_source)
    union all
    select d.day, x.dim, x.key, coalesce(x.extra, ''), x.u from days d cross join lateral public.analytics_day_rows(d.day, p_source) x
     where d.day not in (select day from rolled) and x.dim in ('goals', 'goal_referrers') and x.key is not null
  ),
  goals as (select day, key as goal, sum(u)::bigint as u from rows where dim = 'goals' group by day, key),
  sums as (
    select jsonb_build_object(
      'reader', coalesce(sum(u) filter (where goal = 'reader'), 0),
      'listener', coalesce(sum(u) filter (where goal = 'listener'), 0),
      'atlas', coalesce(sum(u) filter (where goal = 'atlas'), 0),
      'psalms', coalesce(sum(u) filter (where goal = 'psalms'), 0)) as j,
      day >= p_from as is_current
      from goals group by day >= p_from
  )
  select jsonb_build_object(
    'from', p_from,
    'to', p_to,
    'source', p_source,
    'daily', (
      select coalesce(jsonb_agg(jsonb_build_object(
        'day', d.day,
        'reader', coalesce((select u from goals g where g.day = d.day and g.goal = 'reader'), 0),
        'listener', coalesce((select u from goals g where g.day = d.day and g.goal = 'listener'), 0),
        'atlas', coalesce((select u from goals g where g.day = d.day and g.goal = 'atlas'), 0),
        'psalms', coalesce((select u from goals g where g.day = d.day and g.goal = 'psalms'), 0)
      ) order by d.day), '[]'::jsonb)
      from days d where d.day >= p_from
    ),
    'range', coalesce((select j from sums where is_current), '{"reader":0,"listener":0,"atlas":0,"psalms":0}'::jsonb),
    'previous', coalesce((select j from sums where not is_current), '{"reader":0,"listener":0,"atlas":0,"psalms":0}'::jsonb),
    'sources', (
      select coalesce(jsonb_agg(jsonb_build_object('key', k, 'extra', extra, 'u', u) order by u desc, k, extra), '[]'::jsonb)
      from (
        select public.analytics_source(key) as k, extra, sum(u)::bigint as u
          from rows where dim = 'goal_referrers' and day >= p_from group by 1, 2
      ) s
      where k is not null
    )
  ) into result;
  return result;
end;
$$;
revoke execute on function public.analytics_engagement(date, date, text) from public, anon;
grant execute on function public.analytics_engagement(date, date, text) to authenticated;
