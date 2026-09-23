-- "Most highlighted this month" (R-2.5): three or more opted-in readers in the
-- last 30 days, never a user id, readable by anyone.
begin;
create extension if not exists pgtap with schema extensions;
select plan(6);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at)
select ('00000000-0000-0000-0000-0000000001' || lpad(i::text, 2, '0'))::uuid, '00000000-0000-0000-0000-000000000000',
       'authenticated', 'authenticated', 'm' || i || '@test.local', '{}'::jsonb, now(), now()
from generate_series(1, 4) i;
-- Reader 4 does not share aggregates.
update public.profiles set share_aggregates = false where user_id = '00000000-0000-0000-0000-000000000104';

-- John 3:16: readers 1-3 this month. Psalm 23:1-2: readers 1-2 this month, reader 4 (not shared).
-- Romans 8:28: readers 1-3, but two months ago.
insert into public.highlights (user_id, book, chapter, verse_start, verse_end, color)
select ('00000000-0000-0000-0000-0000000001' || lpad(i::text, 2, '0'))::uuid, 'JHN', 3, 16, 16, 'yellow' from generate_series(1, 3) i;
insert into public.highlights (user_id, book, chapter, verse_start, verse_end, color)
select ('00000000-0000-0000-0000-0000000001' || lpad(i::text, 2, '0'))::uuid, 'PSA', 23, 1, 2, 'green' from unnest(array[1, 2, 4]) i;
-- Dated at insert: highlights_touch resets updated_at on every update.
insert into public.highlights (user_id, book, chapter, verse_start, verse_end, color, created_at, updated_at)
select ('00000000-0000-0000-0000-0000000001' || lpad(i::text, 2, '0'))::uuid, 'ROM', 8, 28, 28, 'blue', now() - interval '60 days', now() - interval '60 days' from generate_series(1, 3) i;

refresh materialized view public.verse_highlight_month;

select is((select users from public.verse_highlight_month where book = 'JHN' and chapter = 3 and verse = 16), 3, 'three readers this month are counted');
select is((select count(*)::int from public.verse_highlight_month where book = 'PSA'), 0, 'a reader who does not share is not counted, so two is below the threshold');
select is((select count(*)::int from public.verse_highlight_month where book = 'ROM'), 0, 'highlights older than 30 days are left out');
select is((select count(*)::int from public.verse_highlight_month), 1, 'only John 3:16 qualifies');
select hasnt_column('public', 'verse_highlight_month', 'user_id', 'no user id in the view');
select ok(has_table_privilege('anon', 'public.verse_highlight_month', 'select'), 'anonymous readers may read it');

select * from finish();
rollback;
