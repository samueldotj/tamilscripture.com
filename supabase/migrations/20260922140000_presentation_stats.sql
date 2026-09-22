-- Statistics for a presentation's owner (docs/feature_presentation.md §4):
-- how often its link was opened, by how many people, when, from where and on
-- what, plus the votes. Nothing new is collected: the site's analytics
-- already record a view of /present/{slug} (no cookies, daily-rotating
-- visitor hashes, bots dropped, GPC and DNT honoured). Finished days come
-- from the rollups, which keep per-page counts for two years; today and the
-- last 90 days of detail (countries, devices, last opened) from the raw
-- events. Only the owner may ask, and only about their own presentations.

create or replace function public.presentation_stats(p_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  v_path text;
  v_row record;
  result jsonb;
begin
  select id, slug, votes_up, votes_down, created_at into v_row
    from public.presentations where id = p_id and user_id = auth.uid();
  if not found then return null; end if;
  v_path := '/present/' || v_row.slug;

  with rolled as (
    select day, n, u from public.analytics_daily where dim = 'pages' and key = v_path
  ),
  live as (
    select day, count(*)::bigint as n, count(distinct visitor)::bigint as u
      from public.analytics_events
     where kind = 'view' and path = v_path
       and day not in (select day from public.analytics_daily_totals)
     group by day
  ),
  daily as (select * from rolled union all select * from live),
  recent as (
    select * from public.analytics_events
     where kind = 'view' and path = v_path and day >= current_date - 90
  )
  select jsonb_build_object(
    'views', coalesce((select sum(n) from daily), 0),
    'visitors', coalesce((select sum(u) from daily), 0),
    'days', (select count(*) from daily),
    'first_day', (select min(day) from daily),
    'last_at', (select max(at) from recent),
    'daily', coalesce((select jsonb_agg(jsonb_build_object('day', day, 'n', n, 'u', u) order by day)
                         from daily where day >= current_date - 90), '[]'::jsonb),
    'countries', coalesce((select jsonb_agg(jsonb_build_object('key', key, 'n', n, 'u', u) order by n desc, key)
                             from (select coalesce(country, '?') as key, count(*) as n, count(distinct visitor) as u
                                     from recent group by 1 order by n desc limit 8) c), '[]'::jsonb),
    'devices', coalesce((select jsonb_agg(jsonb_build_object('key', key, 'n', n, 'u', u) order by n desc, key)
                           from (select coalesce(device, '?') as key, count(*) as n, count(distinct visitor) as u
                                   from recent group by 1 order by n desc limit 4) d), '[]'::jsonb),
    'votes_up', v_row.votes_up,
    'votes_down', v_row.votes_down,
    'created_at', v_row.created_at
  ) into result;
  return result;
end;
$$;
revoke execute on function public.presentation_stats(uuid) from public, anon;
grant execute on function public.presentation_stats(uuid) to authenticated;

-- One line per presentation for the owner's list: views and visitors over
-- all time, and when the link was last opened (within the last 90 days).
create or replace function public.my_presentations_stats()
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  with mine as (select id, '/present/' || slug as path from public.presentations where user_id = auth.uid()),
  rolled as (
    select m.id, d.n, d.u from mine m join public.analytics_daily d on d.dim = 'pages' and d.key = m.path
  ),
  live as (
    select m.id, count(*)::bigint as n, count(distinct e.visitor)::bigint as u
      from mine m join public.analytics_events e on e.kind = 'view' and e.path = m.path
     where e.day not in (select day from public.analytics_daily_totals)
     group by m.id
  ),
  last as (
    select m.id, max(e.at) as last_at
      from mine m join public.analytics_events e on e.kind = 'view' and e.path = m.path
     group by m.id
  ),
  sums as (select id, sum(n) as views, sum(u) as visitors from (select * from rolled union all select * from live) x group by id)
  select coalesce(jsonb_object_agg(m.id, jsonb_build_object(
           'views', coalesce(s.views, 0), 'visitors', coalesce(s.visitors, 0), 'last_at', l.last_at)), '{}'::jsonb)
    from mine m left join sums s on s.id = m.id left join last l on l.id = m.id;
$$;
revoke execute on function public.my_presentations_stats() from public, anon;
grant execute on function public.my_presentations_stats() to authenticated;
