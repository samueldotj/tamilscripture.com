-- RLS and role suite for community review (README 3.4 / 7.8). Runs with
-- `supabase test db` (pgTAP) against the local stack after migrations.
-- Three users: a reader, a reviewer and a moderator, plus anon.
begin;
create extension if not exists pgtap with schema extensions;
select plan(25);

-- Fixed ids keep the assertions readable.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values
  ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'reader@test.local',    '{"name":"Reader"}',    now(), now()),
  ('00000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'reviewer@test.local',  '{"name":"Reviewer"}',  now(), now()),
  ('00000000-0000-0000-0000-00000000000c', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'moderator@test.local', '{"name":"Moderator"}', now(), now()),
  ('00000000-0000-0000-0000-00000000000d', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'other@test.local',     '{"name":"Other"}',     now(), now());
update public.profiles set role = 'reviewer'  where user_id = '00000000-0000-0000-0000-00000000000b';
update public.profiles set role = 'moderator' where user_id = '00000000-0000-0000-0000-00000000000c';

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

-- ---- anon ----
select set_config('role', 'anon', true);
select throws_ok(
  $$ select public.suggest_correction('name:IRVTAM:Damascus', 'x', 'தமஸ்கு') $$,
  '42501', null, 'anon cannot call suggest_correction');
select throws_ok($$ select * from public.entity_suggestions $$, '42501', null, 'anon cannot read suggestions');
select pg_temp.logout();

-- ---- reader ----
select pg_temp.login('00000000-0000-0000-0000-00000000000a');
select is(public.my_role(), 'reader', 'new users are readers');
select throws_ok(
  $$ update public.profiles set role = 'moderator' where user_id = '00000000-0000-0000-0000-00000000000a' $$,
  '42501', null, 'a reader cannot change their own role');
select lives_ok(
  $$ update public.profiles set display_name = 'Reader R' where user_id = '00000000-0000-0000-0000-00000000000a' $$,
  'a reader still edits the rest of their profile');
select throws_ok(
  $$ select public.suggest_correction('name:IRVTAM:Damascus', 'தமஸ்குவை', 'Damascus') $$,
  '22023', null, 'a suggestion must contain Tamil script');
select throws_ok(
  $$ select public.suggest_correction('bogus', 'x', 'தமஸ்கு') $$,
  '22023', null, 'target shape is enforced');
select lives_ok(
  $$ select public.suggest_correction('name:IRVTAM:Damascus', 'தமஸ்குவை', 'தமஸ்கு', 'base form') $$,
  'a reader suggests a name correction');
select lives_ok(
  $$ select public.suggest_correction('article:eastons/damascus#p1-ee1db5fc', '', 'கிழக்கு நகரங்களில் மிகப் பழமையானது.') $$,
  'a reader suggests a paragraph');
select is((select count(*) from public.entity_suggestions), 2::bigint, 'a reader sees only their own suggestions');
select throws_ok(
  $$ select public.accept_suggestion((select id from public.entity_suggestions limit 1), 'தமஸ்கு') $$,
  '42501', null, 'a reader cannot accept');
select throws_ok(
  $$ select public.set_role('00000000-0000-0000-0000-00000000000d', 'reviewer') $$,
  '42501', null, 'a reader cannot set roles');
select throws_ok(
  $$ insert into public.entity_suggestions (user_id, target, current_text, suggested_text) values ('00000000-0000-0000-0000-00000000000a', 'name:IRVTAM:X', '', 'x') $$,
  '42501', null, 'no direct inserts');
select pg_temp.logout();

-- Twenty open suggestions is the limit.
select pg_temp.login('00000000-0000-0000-0000-00000000000d');
select lives_ok($$
  select public.suggest_correction('name:IRVTAM:Name' || i, '', 'பெயர்' || i) from generate_series(1, 20) i
$$, 'twenty open suggestions are allowed');
select throws_ok(
  $$ select public.suggest_correction('name:IRVTAM:Name21', '', 'பெயர்') $$,
  '54000', null, 'the twenty-first open suggestion is refused');
select pg_temp.logout();

-- ---- reviewer ----
select pg_temp.login('00000000-0000-0000-0000-00000000000b');
select is((select count(*) from public.entity_suggestions), 22::bigint, 'a reviewer sees every suggestion');
select lives_ok($$
  select public.accept_suggestion(
    (select id from public.entity_suggestions where target = 'name:IRVTAM:Damascus'),
    'தமஸ்கு ')   -- edited: trailing space, trimmed on save
$$, 'a reviewer accepts with a final text');
select is((select text from public.entity_accepted where target = 'name:IRVTAM:Damascus'), 'தமஸ்கு', 'the final text is what gets exported');
select is((select status from public.entity_suggestions where target = 'name:IRVTAM:Damascus'), 'accepted', 'the suggestion is marked accepted');
select lives_ok($$
  select public.reject_suggestion((select id from public.entity_suggestions where target like 'article:%'), 'needs the full sentence')
$$, 'a reviewer rejects with a note');
select lives_ok($$ select public.correct_directly('name:TCV:Damascus', '', 'தமஸ்கு') $$, 'a reviewer corrects directly');
select throws_ok(
  $$ select public.set_role('00000000-0000-0000-0000-00000000000d', 'reviewer') $$,
  '42501', null, 'a reviewer cannot appoint reviewers');
select pg_temp.logout();

-- ---- moderator ----
select pg_temp.login('00000000-0000-0000-0000-00000000000c');
select lives_ok($$ select public.set_role('00000000-0000-0000-0000-00000000000d', 'reviewer') $$, 'a moderator appoints a reviewer');
select throws_ok(
  $$ select public.set_role('00000000-0000-0000-0000-00000000000d', 'moderator') $$,
  '42501', null, 'a moderator cannot create moderators');
select is((select count(*) from public.moderation_log where action in ('accept', 'reject', 'correct', 'set_role')), 4::bigint, 'every decision is logged');
select pg_temp.logout();

select * from finish();
rollback;
