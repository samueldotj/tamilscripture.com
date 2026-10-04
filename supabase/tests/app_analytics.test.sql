-- Android app analytics (20261004100000_app_analytics.sql): anyone may record a
-- batch, duplicates are dropped by event id, bad events are skipped, nothing raw
-- is stored, and search events reach the search log. `supabase test db` (pgTAP).
begin;
create extension if not exists pgtap with schema extensions;
select plan(9);

create or replace function pg_temp.batch(p_events jsonb) returns int language sql as $$
  select public.track_app_batch(
    jsonb_build_object('install', '3f0c2a5e-7d4b-4a3e-9b1c-0a1b2c3d4e5f', 'app', '0.1.0', 'device', 'phone',
                       'window', 'compact', 'os', 'Android 17', 'lang', 'ta', 'events', p_events),
    'IN', 'TN', 'Chennai')
$$;

select set_config('role', 'anon', true);
select is(pg_temp.batch(jsonb_build_array(
  jsonb_build_object('id', '11111111-1111-4111-8111-111111111111', 'at', now(), 'kind', 'view', 'version', 'IRVTAM', 'book', 'JHN', 'chapter', 3, 'source', 'pack'),
  jsonb_build_object('id', '22222222-2222-4222-8222-222222222222', 'at', now(), 'kind', 'read', 'verse', 'JHN.3.16', 'version', 'IRVTAM', 'amount', 2400),
  jsonb_build_object('id', '33333333-3333-4333-8333-333333333333', 'at', now(), 'kind', 'audio', 'action', 'time', 'version', 'IRVTAM', 'book', 'JHN', 'chapter', 3, 'amount', 120),
  jsonb_build_object('id', '44444444-4444-4444-8444-444444444444', 'at', now(), 'kind', 'search', 'query', 'அன்பு', 'amount', 1198)
)), 4, 'anon stores a batch of four events');

select is(pg_temp.batch(jsonb_build_array(
  jsonb_build_object('id', '22222222-2222-4222-8222-222222222222', 'at', now(), 'kind', 'read', 'verse', 'JHN.3.16', 'version', 'IRVTAM', 'amount', 2400)
)), 0, 'a resent event is dropped by its id');

select is(pg_temp.batch(jsonb_build_array(
  jsonb_build_object('id', '55555555-5555-4555-8555-555555555555', 'at', now(), 'kind', 'hack'),
  jsonb_build_object('id', '66666666-6666-4666-8666-666666666666', 'at', now() - interval '60 days', 'kind', 'view'),
  jsonb_build_object('id', '77777777-7777-4777-8777-777777777777', 'at', 'not a date', 'kind', 'view'),
  jsonb_build_object('id', '88888888-8888-4888-8888-888888888888', 'at', now(), 'kind', 'audio', 'action', 'stop')
)), 0, 'unknown kinds, old or bad dates and unknown audio actions are skipped');

select is(public.track_app_batch('{"install": "not-a-uuid", "events": []}'::jsonb), 0, 'a batch without a valid install id stores nothing');
select throws_ok($$ select * from public.analytics_events $$, '42501', null, 'anon cannot read the events');
select set_config('role', 'postgres', true);

select is((select count(*) from public.analytics_events where source = 'android'), 4::bigint, 'four app events stored');
select is((select path from public.analytics_events where event_id = '11111111-1111-4111-8111-111111111111'), '/app/irvtam/JHN/3', 'a view gets an app path');
select ok((select bool_and(visitor !~ '3f0c2a5e' and country = 'IN') from public.analytics_events where source = 'android'),
  'the install id is hashed, never stored, and location comes from the route');
select is((select count(*) from public.search_log where query = 'அன்பு'), 1::bigint, 'a search reaches the search log');

select * from finish();
rollback;
