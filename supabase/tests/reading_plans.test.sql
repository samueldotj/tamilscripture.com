-- Reading plans (docs/feature_reading_plans.md): everyone reads published
-- community plans, moderators alone see drafts and write, and each reader's
-- progress is theirs alone.
begin;
create extension if not exists pgtap with schema extensions;
select plan(26);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'rp-mod@test.local', '{"name":"RP Mod"}', now(), now()),
  ('00000000-0000-0000-0000-0000000000e2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'rp-reader@test.local', '{"name":"RP Reader"}', now(), now()),
  ('00000000-0000-0000-0000-0000000000e3', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'rp-other@test.local', '{"name":"RP Other"}', now(), now());
update public.profiles set role = 'moderator' where user_id = '00000000-0000-0000-0000-0000000000e1';

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

-- ---- shapes ----
select ok(public.check_plan_tracks('[{"name":"நீதிமொழிகள்","from":"PRO","to":"PRO"}]'), 'one track is a valid plan');
select ok(not public.check_plan_tracks('[]'), 'a plan needs a track');
select ok(not public.check_plan_tracks('[{"name":"x","from":"pro","to":"PRO"}]'), 'books are USFM codes');
select ok(not public.check_plan_tracks('[{"name":"x","from":"PRO","to":"PRO","text":"verse"}]'), 'unknown keys are refused');
select ok(not public.check_plan_tracks((select jsonb_agg(jsonb_build_object('name', 't', 'from', 'GEN', 'to', 'GEN')) from generate_series(1, 7))), 'at most six tracks');
select ok(public.check_plan_done('{0-0,12-1,729-5}'), 'day-track keys');
select ok(not public.check_plan_done('{a-0}'), 'keys are numbers');
select ok(not public.check_plan_done('{01-0}'), 'no leading zeros');
select ok(not public.check_plan_done('{3-6}'), 'at most six tracks in a key');

-- ---- a moderator ----
select pg_temp.login('00000000-0000-0000-0000-0000000000e1');
select lives_ok($$ insert into public.reading_plans (id, title_ta, title_en, days, tracks, status, published_at, created_by)
  values ('00000000-0000-0000-0000-00000000aa01', 'நீதிமொழிகள் · 31 நாள்', 'Proverbs · a month', 30, '[{"name":"நீதிமொழிகள்","from":"PRO","to":"PRO"}]', 'published', now(), '00000000-0000-0000-0000-0000000000e1') $$,
  'a moderator publishes a plan');
select lives_ok($$ insert into public.reading_plans (id, title_ta, days, tracks, created_by)
  values ('00000000-0000-0000-0000-00000000aa02', '', 90, '[{"name":"x","from":"MAT","to":"JHN"}]', '00000000-0000-0000-0000-0000000000e1') $$,
  'a draft may have no name yet');
select throws_ok($$ update public.reading_plans set status = 'published' where id = '00000000-0000-0000-0000-00000000aa02' $$, '23514', null, 'a published plan needs a Tamil name');
select throws_ok($$ update public.reading_plans set days = 1000 where id = '00000000-0000-0000-0000-00000000aa01' $$, '23514', null, 'at most two years');
select is((select count(*) from public.reading_plans), 2::bigint, 'a moderator sees drafts');
select pg_temp.logout();

-- ---- a reader ----
select pg_temp.login('00000000-0000-0000-0000-0000000000e2');
select is((select count(*) from public.reading_plans), 1::bigint, 'a reader sees published plans only');
select throws_ok($$ insert into public.reading_plans (title_ta, days, tracks, created_by)
  values ('x', 30, '[{"name":"x","from":"PRO","to":"PRO"}]', '00000000-0000-0000-0000-0000000000e2') $$, '42501', null, 'a reader cannot write a plan');
update public.reading_plans set title_ta = 'hijack';  -- touches no rows under RLS
delete from public.reading_plans;
select lives_ok($$ insert into public.plan_progress (user_id, plan, start_date, done)
  values ('00000000-0000-0000-0000-0000000000e2', 'bible-1y', '2026-01-01', '{0-0,0-1}') $$, 'a reader joins a built-in plan');
select lives_ok($$ insert into public.plan_progress (user_id, plan, start_date)
  values ('00000000-0000-0000-0000-0000000000e2', '00000000-0000-0000-0000-00000000aa01', '2026-09-01') $$, 'and a community plan');
select throws_ok($$ insert into public.plan_progress (user_id, plan, start_date) values ('00000000-0000-0000-0000-0000000000e3', 'bible-1y', '2026-01-01') $$, '42501', null, 'progress cannot be written for another user');
select throws_ok($$ update public.plan_progress set done = '{bad}' where plan = 'bible-1y' $$, '23514', null, 'malformed progress is refused');
select throws_ok($$ insert into public.plan_progress (user_id, plan, start_date) values ('00000000-0000-0000-0000-0000000000e2', 'Bad Plan!', '2026-01-01') $$, '23514', null, 'plan ids are slugs or uuids');
select is((select jsonb_array_length((public.export_my_data())->'reading_plans')), 2, 'the data export carries reading plans');
select pg_temp.logout();
select is((select title_ta from public.reading_plans where id = '00000000-0000-0000-0000-00000000aa01'), 'நீதிமொழிகள் · 31 நாள்', 'a reader changes no plan');

-- ---- another reader ----
select pg_temp.login('00000000-0000-0000-0000-0000000000e3');
select is((select count(*) from public.plan_progress), 0::bigint, 'another reader sees no progress');
select pg_temp.logout();

-- ---- anon ----
select set_config('role', 'anon', true);
select is((select count(*) from public.reading_plans), 1::bigint, 'anon reads published plans');
select throws_ok($$ select * from public.plan_progress $$, '42501', null, 'anon cannot read progress');
select pg_temp.logout();

select * from finish();
rollback;
