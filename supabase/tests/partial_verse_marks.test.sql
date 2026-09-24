-- Sub-verse highlights and notes (R-10.15): offsets come with a version, and
-- an empty range is refused.
begin;
create extension if not exists pgtap with schema extensions;
select plan(6);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values ('00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000000',
        'authenticated', 'authenticated', 'p1@test.local', '{}'::jsonb, now(), now());

select lives_ok($$
  insert into public.highlights (user_id, book, chapter, verse_start, verse_end, color)
  values ('00000000-0000-0000-0000-000000000201', 'JHN', 3, 16, 16, 'yellow')
$$, 'a whole-verse highlight needs no offsets');
select lives_ok($$
  insert into public.highlights (user_id, book, chapter, verse_start, verse_end, color, version, char_start, char_end, quote)
  values ('00000000-0000-0000-0000-000000000201', 'JHN', 3, 16, 16, 'green', 'IRVTAM', 4, 20, 'words')
$$, 'a word range within one verse');
select lives_ok($$
  insert into public.notes (user_id, book, chapter, verse_start, verse_end, body, version, char_start, char_end)
  values ('00000000-0000-0000-0000-000000000201', 'JHN', 3, 16, 17, 'across two verses', 'IRVTAM', 30, 5)
$$, 'a range from part of one verse into the next');
select throws_ok($$
  insert into public.highlights (user_id, book, chapter, verse_start, verse_end, color, char_start, char_end)
  values ('00000000-0000-0000-0000-000000000201', 'JHN', 3, 16, 16, 'blue', 1, 5)
$$, '23514', null, 'offsets without a version are refused');
select throws_ok($$
  insert into public.notes (user_id, book, chapter, verse_start, verse_end, body, version, char_start, char_end)
  values ('00000000-0000-0000-0000-000000000201', 'JHN', 3, 16, 16, 'empty', 'IRVTAM', 7, 7)
$$, '23514', null, 'an empty range is refused');
select throws_ok($$
  insert into public.highlights (user_id, book, chapter, verse_start, verse_end, color, version, char_start, char_end)
  values ('00000000-0000-0000-0000-000000000201', 'JHN', 3, 16, 16, 'pink', 'IRVTAM', -1, 5)
$$, '23514', null, 'a negative offset is refused');

select * from finish();
rollback;
