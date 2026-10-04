-- Bookmarks are private, one per verse; deleting a highlight, note or bookmark
-- leaves a deleted_rows entry its owner (only) can read.
begin;
create extension if not exists pgtap with schema extensions;
select plan(7);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at) values
  ('00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'b1@test.local', '{}'::jsonb, now(), now()),
  ('00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'b2@test.local', '{}'::jsonb, now(), now());

set local role authenticated;
set local request.jwt.claims = '{"sub":"00000000-0000-0000-0000-000000000301","role":"authenticated"}';

select lives_ok($$
  insert into public.bookmarks (id, user_id, book, chapter, verse, version)
  values ('00000000-0000-0000-0000-0000000003b1', '00000000-0000-0000-0000-000000000301', 'JHN', 3, 16, 'IRVTAM')
$$, 'a reader bookmarks a verse');
select throws_ok($$
  insert into public.bookmarks (user_id, book, chapter, verse) values ('00000000-0000-0000-0000-000000000301', 'JHN', 3, 16)
$$, '23505', null, 'one bookmark per verse');
select throws_ok($$
  insert into public.bookmarks (user_id, book, chapter, verse) values ('00000000-0000-0000-0000-000000000302', 'JHN', 3, 1)
$$, '42501', null, 'nobody bookmarks for someone else');

insert into public.highlights (id, user_id, book, chapter, verse_start, verse_end, color)
values ('00000000-0000-0000-0000-0000000003a1', '00000000-0000-0000-0000-000000000301', 'JHN', 3, 16, 16, 'yellow');
delete from public.highlights where id = '00000000-0000-0000-0000-0000000003a1';
delete from public.bookmarks where id = '00000000-0000-0000-0000-0000000003b1';

select is((select count(*)::int from public.deleted_rows), 2, 'both deletions are recorded');
select is((select table_name from public.deleted_rows where row_id = '00000000-0000-0000-0000-0000000003a1'), 'highlights', 'with the table they came from');
select ok((public.export_my_data()) ? 'bookmarks', 'the export carries bookmarks');

set local request.jwt.claims = '{"sub":"00000000-0000-0000-0000-000000000302","role":"authenticated"}';
select is((select count(*)::int from public.deleted_rows), 0, 'another reader sees none of them');

select * from finish();
rollback;
