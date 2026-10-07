-- Sharing in the site analytics (docs/feature_analytics.md A9): anyone may
-- record, only staff may read, and the report counts shares, sharers, image
-- shares and their templates. `supabase test db` (pgTAP).
begin;
create extension if not exists pgtap with schema extensions;
select plan(11);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values ('00000000-0000-0000-0000-0000000000c3', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 's-reviewer@test.local', '{"name":"S Reviewer"}', now(), now());
update public.profiles set role = 'reviewer' where user_id = '00000000-0000-0000-0000-0000000000c3';

create or replace function pg_temp.share(p_action text, p_verse text, p_detail text, p_ip text)
returns void language sql as $$
  select public.track(p_kind => 'share', p_path => '/irvtam/john/3.16', p_ip => p_ip, p_ua => 'Mozilla/5.0 (Android)',
    p_book => 'JHN', p_chapter => 3, p_verse => p_verse, p_action => p_action, p_version => 'IRVTAM', p_detail => p_detail)
$$;

select set_config('role', 'anon', true);
select lives_ok($$ select pg_temp.share('download', 'JHN.3.16', 'plate.square.light', '203.0.113.30') $$, 'anon records an image download');
select lives_ok($$ select pg_temp.share('sheet', 'JHN.3.16', 'initial.story.dark', '203.0.113.30') $$, 'and an image through the share sheet');
select lives_ok($$ select pg_temp.share('link', 'JHN.3.16', 'plate.square.light', '203.0.113.31') $$, 'and a link, whose detail is dropped');
select lives_ok($$ select pg_temp.share('print', 'JHN.3.16', null, '203.0.113.31') $$, 'an unknown action is ignored, not an error');
select throws_ok($$ select * from public.analytics_events $$, '42501', null, 'anon cannot read the events');
select set_config('role', 'postgres', true);

select is((select count(*) from public.analytics_events where kind = 'share'), 3::bigint, 'three share events stored');
select is((select count(*) from public.analytics_events where kind = 'share' and detail is not null), 2::bigint, 'only image shares keep a template');

select set_config('request.jwt.claims', json_build_object('sub', '00000000-0000-0000-0000-0000000000c3', 'role', 'authenticated')::text, true);
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-0000000000c3', true);
select set_config('role', 'authenticated', true);
select is((public.analytics_report(public.analytics_today(), public.analytics_today()) -> 'totals' ->> 'shares')::int, 3, 'a reviewer sees three shares');
select is((public.analytics_report(public.analytics_today(), public.analytics_today()) -> 'totals' ->> 'image_shares')::int, 2, 'two of them images');
select is((public.analytics_report(public.analytics_today(), public.analytics_today()) -> 'totals' ->> 'sharers')::int, 2, 'by two visitors');
select is(public.analytics_report(public.analytics_today(), public.analytics_today()) -> 'top' -> 'share_verses' -> 0 ->> 'key', 'JHN.3.16', 'and the verse shared');

select * from finish();
rollback;
