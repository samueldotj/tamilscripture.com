-- Site analytics (docs/feature_analytics.md): anyone may record an event,
-- nobody but staff may read, and nothing identifying is stored. Runs with
-- `supabase test db` (pgTAP) against the local stack after migrations.
begin;
create extension if not exists pgtap with schema extensions;
select plan(25);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values
  ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 't-reader@test.local',   '{"name":"T Reader"}',   now(), now()),
  ('00000000-0000-0000-0000-0000000000b2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 't-reviewer@test.local', '{"name":"T Reviewer"}', now(), now());
update public.profiles set role = 'reviewer' where user_id = '00000000-0000-0000-0000-0000000000b2';

create or replace function pg_temp.login(p_user uuid) returns void language plpgsql as $$
begin
  perform set_config('request.jwt.claims', json_build_object('sub', p_user, 'role', 'authenticated')::text, true);
  perform set_config('request.jwt.claim.sub', p_user::text, true);
  perform set_config('role', 'authenticated', true);
end $$;
create or replace function pg_temp.logout() returns void language plpgsql as $$
begin
  perform set_config('request.jwt.claims', '', true);
  perform set_config('request.jwt.claim.sub', '', true);
  perform set_config('role', 'postgres', true);
end $$;

-- ---- anyone can record; nobody can read the tables ----
select set_config('role', 'anon', true);
select lives_ok($$ select public.track('view', '/irvtam/john/3', '/[versions=versions]/[book=book]/[chapter=int]', null, '203.0.113.7', 'Mozilla/5.0 (iPhone)', null, 'IN', 'TN', 'Chennai', 'mobile', 'iOS', 'Safari', '390x844', 'google.com', 'ta', 'JHN', 3) $$, 'anon records a page view');
select lives_ok($$ select public.track('verse', '/irvtam/john/3', null, 'JHN.3.16', '203.0.113.7', 'Mozilla/5.0 (iPhone)', null, 'IN', 'TN', 'Chennai', 'mobile', 'iOS', 'Safari', '390x844', null, 'ta') $$, 'anon records a verse click');
select lives_ok($$ select public.track('view', '/irvtam/john/3', '/[versions=versions]/[book=book]/[chapter=int]', null, '198.51.100.9', 'Mozilla/5.0 (Windows)', '00000000-0000-0000-0000-0000000000b1', 'LK', null, 'Jaffna', 'desktop', 'Windows', 'Chrome', '1920x1080', null, 'en') $$, 'a signed-in view');
select lives_ok($$ select public.track('view', 'https://evil.example/', null, null, '1.2.3.4', 'x') $$, 'a bad path is ignored, not an error');
select throws_ok($$ select * from public.analytics_events $$, '42501', null, 'anon cannot read events');
select throws_ok($$ select * from public.analytics_salt $$, '42501', null, 'anon cannot read salts');
select throws_ok($$ select public.analytics_report(current_date - 1, current_date + 1) $$, '42501', null, 'anon cannot run the report');
select throws_ok($$ select public.analytics_rollup(current_date) $$, '42501', null, 'anon cannot trigger a rollup');
select throws_ok($$ select public.analytics_now() $$, '42501', null, 'anon cannot read the live panel');
select pg_temp.logout();

-- ---- nothing identifying is stored ----
select is((select count(*) from public.analytics_events), 3::bigint, 'three events stored, the bad path dropped');
select is((select count(*) from public.analytics_events where visitor ~ '^[0-9a-f]{16}$'), 3::bigint, 'visitors are 16-hex hashes');
select is((select count(*) from public.analytics_events where path like '%203.0.113%' or visitor like '%203%' or member = '00000000-0000-0000-0000-0000000000b1'), 0::bigint, 'no IP address or user id is stored');
select is((select count(*) from public.analytics_events where member is not null), 1::bigint, 'the signed-in view carries a member hash');

-- ---- readers get nothing, staff get the report ----
select pg_temp.login('00000000-0000-0000-0000-0000000000b1');
select is(public.analytics_report(current_date - 1, current_date + 1), null, 'a reader gets no report');
select is(public.analytics_now(), null, 'a reader gets no live panel');
select throws_ok($$ select * from public.analytics_events $$, '42501', null, 'a reader cannot read events');
select pg_temp.logout();

select pg_temp.login('00000000-0000-0000-0000-0000000000b2');
select is((public.analytics_report(public.analytics_today() - 1, public.analytics_today() + 1) -> 'totals' ->> 'views')::int, 2, 'a reviewer sees two page views');
select is((public.analytics_report(public.analytics_today() - 1, public.analytics_today() + 1) -> 'totals' ->> 'visitors')::int, 2, 'and two visitors');
select is(public.analytics_report(public.analytics_today() - 1, public.analytics_today() + 1) -> 'top' -> 'verses' -> 0 ->> 'key', 'JHN.3.16', 'and the tapped verse');
select is(public.analytics_report(public.analytics_today() - 1, public.analytics_today() + 1) -> 'top' -> 'books' -> 0 ->> 'key', 'JHN', 'and the book read');
select is(public.analytics_report(public.analytics_today() - 1, public.analytics_today() + 1) -> 'top' -> 'sections' -> 0 ->> 'key', 'reading', 'and the part of the site');
select is((public.analytics_now() ->> 'views')::int, 2, 'the live panel counts the last 30 minutes');
select pg_temp.logout();

-- ---- a rollup gives the same numbers as the live count ----
select lives_ok($$ select public.analytics_rollup(public.analytics_today()) $$, 'today rolls up');
select pg_temp.login('00000000-0000-0000-0000-0000000000b2');
select is((public.analytics_report(public.analytics_today() - 1, public.analytics_today() + 1) -> 'totals' ->> 'views')::int, 2, 'views are unchanged after the rollup');
select is((public.analytics_report(public.analytics_today() - 1, public.analytics_today() + 1) -> 'totals' ->> 'unique_views')::int, 2, 'and unique views');
select pg_temp.logout();

select * from finish();
rollback;
