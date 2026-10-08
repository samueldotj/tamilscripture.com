-- Traffic report by source (20261007100000_traffic_source_filter.sql): /mod
-- pages are left out, and the report and live panel filter by website or app,
-- before and after a rollup. `supabase test db` (pgTAP).
begin;
create extension if not exists pgtap with schema extensions;
select plan(10);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values ('00000000-0000-0000-0000-0000000000d4', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 't-reviewer@test.local', '{"name":"T Reviewer"}', now(), now());
update public.profiles set role = 'reviewer' where user_id = '00000000-0000-0000-0000-0000000000d4';

select set_config('role', 'anon', true);
select public.track(p_kind => 'view', p_path => '/irvtam/john/3', p_ip => '203.0.113.40', p_ua => 'Mozilla/5.0 (Android)', p_book => 'JHN', p_chapter => 3);
select public.track(p_kind => 'view', p_path => '/mod/traffic', p_ip => '203.0.113.41', p_ua => 'Mozilla/5.0 (Windows)');
select public.track(p_kind => 'view', p_path => '/mod', p_ip => '203.0.113.41', p_ua => 'Mozilla/5.0 (Windows)');
select public.track_app_batch(
  jsonb_build_object('install', '4a1d3b6f-8e5c-4b4f-8c2d-1b2c3d4e5f60', 'app', '0.1.0', 'device', 'phone', 'os', 'Android 17', 'lang', 'ta',
    'events', jsonb_build_array(
      jsonb_build_object('id', '9a9a9a9a-1111-4111-8111-111111111111', 'at', now(), 'kind', 'view', 'version', 'IRVTAM', 'book', 'PSA', 'chapter', 23),
      jsonb_build_object('id', '9a9a9a9a-2222-4222-8222-222222222222', 'at', now(), 'kind', 'view', 'version', 'IRVTAM', 'book', 'PSA', 'chapter', 24))),
  'IN', 'TN', 'Chennai');
select set_config('role', 'postgres', true);

select set_config('request.jwt.claims', json_build_object('sub', '00000000-0000-0000-0000-0000000000d4', 'role', 'authenticated')::text, true);
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-0000000000d4', true);
select set_config('role', 'authenticated', true);

select is((public.analytics_report(public.analytics_today(), public.analytics_today()) -> 'totals' ->> 'views')::int, 3, 'all sources: three views, /mod left out');
select is((public.analytics_report(public.analytics_today(), public.analytics_today()) -> 'totals' ->> 'visitors')::int, 2, 'and two visitors');
select is((public.analytics_report(public.analytics_today(), public.analytics_today(), 'web') -> 'totals' ->> 'views')::int, 1, 'the website alone: one view');
select is((public.analytics_report(public.analytics_today(), public.analytics_today(), 'android') -> 'totals' ->> 'views')::int, 2, 'the app alone: two views');
select is(public.analytics_report(public.analytics_today(), public.analytics_today(), 'android') -> 'top' -> 'books' -> 0 ->> 'key', 'PSA', 'and the book read in the app');
select is((public.analytics_now('android') ->> 'views')::int, 2, 'the live panel filters by source');
select is((public.analytics_now() ->> 'views')::int, 3, 'and leaves out /mod');
select throws_ok($$ select public.analytics_report(public.analytics_today(), public.analytics_today(), 'ios') $$, '22023', null, 'an unknown source is refused');

select set_config('role', 'postgres', true);
select public.analytics_rollup(public.analytics_today());
select set_config('role', 'authenticated', true);
select is((public.analytics_report(public.analytics_today(), public.analytics_today(), 'android') -> 'totals' ->> 'views')::int, 2, 'after the rollup the app still has two views');
select is((public.analytics_report(public.analytics_today(), public.analytics_today()) -> 'daily' -> 0 ->> 'views')::int, 3, 'and the day sums both sources');

select * from finish();
rollback;
