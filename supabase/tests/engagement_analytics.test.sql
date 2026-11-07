-- Engagement in the site analytics (docs/feature_analytics.md A11): anyone may
-- record a goal, only staff may read, and analytics_engagement() counts engaged
-- visitors per goal and per landing source. `supabase test db` (pgTAP).
begin;
create extension if not exists pgtap with schema extensions;
select plan(15);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'e-reviewer@test.local', '{"name":"E Reviewer"}', now(), now());
update public.profiles set role = 'reviewer' where user_id = '00000000-0000-0000-0000-0000000000e1';

-- A landing page view (with its referrer) and goals, for one visitor.
create or replace function pg_temp.land(p_referrer text, p_ip text)
returns void language sql as $$
  select public.track(p_kind => 'view', p_path => '/irvtam/john/3', p_route => '/[versions=versions]/[book=book]/[chapter=int]',
    p_ip => p_ip, p_ua => 'Mozilla/5.0 (Android)', p_referrer => p_referrer)
$$;
create or replace function pg_temp.goal(p_action text, p_ip text)
returns void language sql as $$
  select public.track(p_kind => 'goal', p_path => '/irvtam/john/4', p_ip => p_ip, p_ua => 'Mozilla/5.0 (Android)', p_action => p_action)
$$;

select set_config('role', 'anon', true);
-- Three visitors: from an ad (reader and listener), from Google search (reader), direct (nothing).
select lives_ok($$ select pg_temp.land('utm:google-ads', '203.0.113.40') $$, 'anon records an ad landing');
select lives_ok($$ select pg_temp.goal('reader', '203.0.113.40') $$, 'and an engaged reader');
select lives_ok($$ select pg_temp.goal('listener', '203.0.113.40') $$, 'and an engaged listener');
select lives_ok($$ select pg_temp.goal('reader', '203.0.113.40') $$, 'a repeated goal is stored but counted once');
select lives_ok($$ select pg_temp.land('google.com', '203.0.113.41') $$, 'a landing from Google search');
select lives_ok($$ select pg_temp.goal('reader', '203.0.113.41') $$, 'who read on');
select lives_ok($$ select pg_temp.land('(direct)', '203.0.113.42') $$, 'a direct visitor who did not read on');
select lives_ok($$ select pg_temp.goal('signup', '203.0.113.42') $$, 'an unknown goal is ignored, not an error');
select throws_ok($$ select public.analytics_engagement(public.analytics_today(), public.analytics_today()) $$, '42501', null, 'anon cannot call the report');
select set_config('role', 'postgres', true);

select is((select count(*) from public.analytics_events where kind = 'goal'), 4::bigint, 'four goal events stored');
select is(public.analytics_source('utm:google-ads'), 'google_ads', 'ad landings are their own source');

select set_config('request.jwt.claims', json_build_object('sub', '00000000-0000-0000-0000-0000000000e1', 'role', 'authenticated')::text, true);
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-0000000000e1', true);
select set_config('role', 'authenticated', true);
select is((public.analytics_engagement(public.analytics_today(), public.analytics_today()) -> 'range' ->> 'reader')::int, 2, 'a reviewer sees two engaged readers');
select is((public.analytics_engagement(public.analytics_today(), public.analytics_today()) -> 'range' ->> 'listener')::int, 1, 'and one engaged listener');
select is(
  (select (s ->> 'u')::int from jsonb_array_elements(public.analytics_engagement(public.analytics_today(), public.analytics_today()) -> 'sources') s
    where s ->> 'key' = 'google_ads' and s ->> 'extra' = 'reader'),
  1, 'one engaged reader came from an ad');
select is(
  (select count(*)::int from jsonb_array_elements(public.analytics_engagement(public.analytics_today(), public.analytics_today()) -> 'sources') s
    where s ->> 'key' = 'direct'),
  0, 'the direct visitor is not an engaged source');

select * from finish();
rollback;
