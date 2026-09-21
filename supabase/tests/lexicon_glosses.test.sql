-- Tamil glosses for Strong's numbers (docs/feature_concordance.md, C5): the
-- gloss target is accepted, bounded and Tamil-only, and flows through
-- suggestion and acceptance like names and paragraphs.
begin;
create extension if not exists pgtap with schema extensions;
select plan(7);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'g-reader@test.local',   '{"name":"G Reader"}',   now(), now()),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'g-reviewer@test.local', '{"name":"G Reviewer"}', now(), now());
update public.profiles set role = 'reviewer' where user_id = '00000000-0000-0000-0000-0000000000c2';

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

select lives_ok($$ select public.check_correction('gloss:G0026', 'அன்பு') $$, 'a Tamil gloss for a Strong''s number is valid');
select lives_ok($$ select public.check_correction('gloss:H1121a', 'மகன்') $$, 'lower-case extensions are valid');
select throws_ok($$ select public.check_correction('gloss:X0026', 'அன்பு') $$, '22023', null, 'an unknown prefix is refused');
select throws_ok($$ select public.check_correction('gloss:G0026', 'love') $$, '22023', null, 'a gloss must be Tamil');
select throws_ok($$ select public.check_correction('gloss:G0026', repeat('அ', 201)) $$, '22023', null, 'a gloss is at most 200 characters');

select pg_temp.login('00000000-0000-0000-0000-0000000000c1');
select lives_ok($$ select public.suggest_correction('gloss:G0026', '', 'அன்பு') $$, 'a reader suggests a gloss');
select pg_temp.logout();

select pg_temp.login('00000000-0000-0000-0000-0000000000c2');
select public.accept_suggestion((select id from public.entity_suggestions where target = 'gloss:G0026'), 'அன்பு');
select pg_temp.logout();
select is((select text from public.entity_accepted where target = 'gloss:G0026'), 'அன்பு', 'the accepted gloss is ready for export');

select * from finish();
rollback;
