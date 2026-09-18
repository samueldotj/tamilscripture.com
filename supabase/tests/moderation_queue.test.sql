-- The queue screen's own functions (design 8A): the tab counts, the stats
-- strip, and the contributor standing that mod_queue now carries. Runs with
-- `supabase test db` (pgTAP) against the local stack after migrations.
-- Same three users as community_review.test.sql; this file stands alone.
begin;
create extension if not exists pgtap with schema extensions;
select plan(13);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values
  ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'q-reader@test.local',   '{"name":"Q Reader"}',   now(), now()),
  ('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'q-reviewer@test.local', '{"name":"Q Reviewer"}', now(), now()),
  ('00000000-0000-0000-0000-0000000000a3', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'q-other@test.local',    '{"name":"Q Other"}',    now(), now());
update public.profiles set role = 'reviewer' where user_id = '00000000-0000-0000-0000-0000000000a2';

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

-- ---- only staff may see any of it ----
select set_config('role', 'anon', true);
select throws_ok($$ select * from public.mod_counts() $$, '42501', null, 'anon cannot read the counts');
select throws_ok($$ select * from public.mod_stats() $$, '42501', null, 'anon cannot read the stats');
select pg_temp.logout();

select pg_temp.login('00000000-0000-0000-0000-0000000000a1');
select is((select count(*) from public.mod_counts()), 0::bigint, 'a reader gets no counts');
select is((select count(*) from public.mod_stats()), 0::bigint, 'a reader gets no stats');

-- ---- one contributor, three suggestions ----
select public.suggest_correction('article:eastons/jehovah#p1-aaaaaaaa', 'old one',   'புதிய ஒன்று',  'wrong-word');
select public.suggest_correction('article:smiths/jehovah#p1-bbbbbbbb',  'old two',   'புதிய இரண்டு', 'grammar: missing a word');
select public.suggest_correction('article:aquifer/zion#p2-cccccccc',    'old three', 'புதிய மூன்று');
select pg_temp.logout();

-- ---- the reviewer decides two of them ----
select pg_temp.login('00000000-0000-0000-0000-0000000000a2');
select public.accept_suggestion(
  (select id from public.entity_suggestions where target = 'article:eastons/jehovah#p1-aaaaaaaa'), 'புதிய ஒன்று');
select public.reject_suggestion(
  (select id from public.entity_suggestions where target = 'article:smiths/jehovah#p1-bbbbbbbb'), 'not this time');

select is((select open      from public.mod_counts()), 1::bigint, 'one suggestion is still open');
select is((select accepted  from public.mod_counts()), 1::bigint, 'one was accepted');
select is((select rejected  from public.mod_counts()), 1::bigint, 'one was rejected');

-- ---- the standing travels with the row ----
select is(
  (select author_accepted from public.mod_queue('open') where target = 'article:aquifer/zion#p2-cccccccc'),
  1::bigint, 'the queue carries what this contributor has had accepted');
select is(
  (select author_rejected from public.mod_queue('open') where target = 'article:aquifer/zion#p2-cccccccc'),
  1::bigint, 'and what has been rejected');
select is(
  (select author from public.mod_queue('open') where target = 'article:aquifer/zion#p2-cccccccc'),
  'Q Reader', 'and still names the author');

-- ---- the stats strip ----
select is((select accepted_this_month from public.mod_stats()), 1::bigint, 'one acceptance this month');
select is((select contributors from public.mod_stats()), 1::bigint, 'one distinct contributor');
select ok((select avg_wait_hours from public.mod_stats()) >= 0, 'the average wait is a number, not null');

select pg_temp.logout();
select * from finish();
rollback;
