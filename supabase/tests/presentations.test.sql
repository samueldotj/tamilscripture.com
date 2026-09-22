-- Verse presentations (docs/feature_presentation.md): the owner alone reads
-- and writes through the table, the audience reads only shared presentations
-- through presentation_by_slug() and never the owner's id, and the slide
-- shape is checked in the database.
begin;
create extension if not exists pgtap with schema extensions;
select plan(20);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values
  ('00000000-0000-0000-0000-0000000000d1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p-owner@test.local', '{"name":"P Owner"}', now(), now()),
  ('00000000-0000-0000-0000-0000000000d2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p-other@test.local', '{"name":"P Other"}', now(), now());

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

-- ---- the slide shape ----
select ok(public.check_slides('[]'::jsonb), 'no slides is a valid start');
select ok(public.check_slides('[{"id":"a1","title":"தேவ அன்பு","notes":"## அன்பின் அளவு\n- **இவ்வளவாய்**","verses":[{"book":"JHN","chapter":3,"start":16,"end":16},{"book":"ROM","chapter":5,"start":6,"end":8,"version":"TCV"}]}]'::jsonb), 'a slide with verses, a title and notes');
select ok(not public.check_slides('{}'::jsonb), 'slides must be an array');
select ok(not public.check_slides('[{"id":"a1","notes":"","verses":[{"book":"JHN","chapter":0,"start":16,"end":16}]}]'::jsonb), 'chapter 0 is refused');
select ok(not public.check_slides('[{"id":"a1","notes":"","verses":[{"book":"JHN","chapter":3,"start":18,"end":16}]}]'::jsonb), 'a range must not run backwards');
select ok(not public.check_slides('[{"id":"a1","notes":"","verses":[{"book":"john","chapter":3,"start":16,"end":16}]}]'::jsonb), 'books are USFM codes');
select ok(not public.check_slides('[{"id":"a1","notes":"","verses":[],"text":"hard-coded verse"}]'::jsonb), 'unknown keys are refused, so verse text is never stored');
select ok(not public.check_slides(('[{"id":"a1","notes":"' || repeat('x', 20001) || '","verses":[]}]')::jsonb), 'notes are at most 20,000 characters');
select ok(not public.check_slides((select jsonb_agg(jsonb_build_object('id', 's' || i, 'notes', '', 'verses', '[]'::jsonb)) from generate_series(1, 201) i)), 'at most 200 slides');

-- ---- the owner ----
select pg_temp.login('00000000-0000-0000-0000-0000000000d1');
select lives_ok($$ insert into public.presentations (user_id, slug, title, subtitle, version, slides)
  values ('00000000-0000-0000-0000-0000000000d1', 'abcd2345', 'தேவ அன்பு', 'Sunday sermon', 'IRVTAM',
          '[{"id":"a1","title":"தேவ அன்பு","notes":"","verses":[]},{"id":"a2","notes":"## அன்பின் அளவு","verses":[{"book":"JHN","chapter":3,"start":16,"end":16}]}]') $$,
  'the owner creates a presentation');
select throws_ok($$ insert into public.presentations (user_id, slug, title) values ('00000000-0000-0000-0000-0000000000d2', 'spoof2345', 'x') $$, '42501', null, 'a row cannot be written for another user');
select throws_ok($$ update public.presentations set slides = '{"not":"an array"}' where slug = 'abcd2345' $$, '23514', null, 'a malformed slide list is refused on write');
select is((select title from public.presentations where slug = 'abcd2345'), 'தேவ அன்பு', 'the owner reads their presentation');
select is((select jsonb_array_length((public.export_my_data())->'presentations')), 1, 'the data export carries presentations');
select pg_temp.logout();

-- ---- another signed-in user ----
select pg_temp.login('00000000-0000-0000-0000-0000000000d2');
select is((select count(*) from public.presentations), 0::bigint, 'another user sees no rows through the table');
select is((with u as (update public.presentations set title = 'hijack' where slug = 'abcd2345' returning 1) select count(*) from u), 0::bigint, 'another user changes nothing');
select is((public.presentation_by_slug('abcd2345'))->>'title', 'தேவ அன்பு', 'a signed-in viewer opens a shared presentation by its link');
select pg_temp.logout();

-- ---- the audience (anon) ----
select set_config('role', 'anon', true);
select throws_ok($$ select * from public.presentations $$, '42501', null, 'anon cannot read the table');
select ok((public.presentation_by_slug('abcd2345')) ? 'slides' and not ((public.presentation_by_slug('abcd2345')) ? 'user_id'), 'the permalink returns the slides and never the owner');
select pg_temp.logout();

-- ---- private presentations ----
update public.presentations set visibility = 'private' where slug = 'abcd2345';
select set_config('role', 'anon', true);
select is(public.presentation_by_slug('abcd2345'), null, 'a private presentation is invisible from its link');
select pg_temp.logout();

select * from finish();
rollback;
