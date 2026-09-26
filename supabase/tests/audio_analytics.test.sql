-- Audio Bible listening in the site analytics (docs/feature_analytics.md A7):
-- anyone may record, only staff may read, and the report counts plays,
-- listeners, listening time and completions. `supabase test db` (pgTAP).
begin;
create extension if not exists pgtap with schema extensions;
select plan(12);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'a-reviewer@test.local', '{"name":"A Reviewer"}', now(), now());
update public.profiles set role = 'reviewer' where user_id = '00000000-0000-0000-0000-0000000000c2';

create or replace function pg_temp.audio(p_action text, p_book text, p_chapter int, p_verse text, p_version text, p_amount int, p_ip text)
returns void language sql as $$
  select public.track(p_kind => 'audio', p_path => '/irvtam/john/3', p_ip => p_ip, p_ua => 'Mozilla/5.0 (Android)',
    p_book => p_book, p_chapter => p_chapter, p_verse => p_verse, p_action => p_action, p_version => p_version, p_amount => p_amount)
$$;

select set_config('role', 'anon', true);
select lives_ok($$ select pg_temp.audio('play', 'JHN', 3, null, 'IRVTAM', null, '203.0.113.20') $$, 'anon records a chapter play');
select lives_ok($$ select pg_temp.audio('jump', 'JHN', 3, 'JHN.3.16', 'IRVTAM', null, '203.0.113.20') $$, 'and a jump to a verse');
select lives_ok($$ select pg_temp.audio('time', 'JHN', 3, null, 'IRVTAM', 300, '203.0.113.20') $$, 'and time listened');
select lives_ok($$ select pg_temp.audio('end', 'JHN', 3, null, 'IRVTAM', null, '203.0.113.20') $$, 'and a completed chapter');
select lives_ok($$ select pg_temp.audio('next', 'JHN', 4, null, 'IRVTAM', null, '203.0.113.20') $$, 'and the next chapter');
select lives_ok($$ select pg_temp.audio('stop', 'JHN', 4, null, 'IRVTAM', null, '203.0.113.20') $$, 'an unknown action is ignored, not an error');
select throws_ok($$ select * from public.analytics_events $$, '42501', null, 'anon cannot read the events');
select set_config('role', 'postgres', true);

select is((select count(*) from public.analytics_events where kind = 'audio'), 5::bigint, 'five audio events stored');

select set_config('request.jwt.claims', json_build_object('sub', '00000000-0000-0000-0000-0000000000c2', 'role', 'authenticated')::text, true);
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-0000000000c2', true);
select set_config('role', 'authenticated', true);
select is((public.analytics_report(public.analytics_today(), public.analytics_today()) -> 'totals' ->> 'audio_starts')::int, 2, 'a reviewer sees two chapter plays');
select is((public.analytics_report(public.analytics_today(), public.analytics_today()) -> 'totals' ->> 'listen_seconds')::int, 300, 'and five minutes listened');
select is(public.analytics_report(public.analytics_today(), public.analytics_today()) -> 'top' -> 'audio_verses' -> 0 ->> 'key', 'JHN.3.16', 'and the verse played from');
select is((public.analytics_now() ->> 'listeners')::int, 1, 'the live panel counts one listener');

select * from finish();
rollback;
