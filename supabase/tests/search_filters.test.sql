-- Search restricted to a testament, a book or a chapter range (R-5.8).
begin;
create extension if not exists pgtap with schema extensions;
select plan(11);

insert into public.verse_search (verse_id, version, lang, book_ord, text) values
  ('GEN.29.20', 'TSTEN', 'en', 1, 'Jacob served seven years for Rachel, yet they seemed but a few days because of his love for her.'),
  ('JHN.3.16', 'TSTEN', 'en', 43, 'For God so loved the world that He gave His one and only Son.'),
  ('JHN.4.10', 'TSTEN', 'en', 43, 'If you knew the gift of God, you would have asked Him, and He would have given you living water, for love.'),
  ('JHN.13.34', 'TSTEN', 'en', 43, 'A new commandment I give you: Love one another.'),
  ('ROM.5.8', 'TSTEN', 'en', 45, 'But God proves His love for us in this: While we were still sinners, Christ died for us.');

select is((select count(*)::int from public.search_verses('love', array['TSTEN'])), 5, 'no limits: every book');
select is((select max(total)::int from public.search_verses('love', array['TSTEN'])), 5, 'total counts every hit');
select is((select count(*)::int from public.search_verses('love', array['TSTEN'], book_min => 1::smallint, book_max => 39::smallint)), 1, 'Old Testament only');
select is((select count(*)::int from public.search_verses('love', array['TSTEN'], book_min => 40::smallint, book_max => 66::smallint)), 4, 'New Testament only');
select is((select count(*)::int from public.search_verses('love', array['TSTEN'], book_min => 43::smallint, book_max => 43::smallint)), 3, 'one book');
select is((select count(*)::int from public.search_verses('love', array['TSTEN'], book_min => 43::smallint, book_max => 43::smallint, ch_min => 3)), 1, 'one chapter');
select is((select count(*)::int from public.search_verses('love', array['TSTEN'], book_min => 43::smallint, book_max => 43::smallint, ch_min => 3, ch_max => 4)), 2, 'a chapter range');
select is((select count(*)::int from public.search_verses('love', array['TSTEN'], false, 50, 0)), 5, 'the five-argument call still works');
select ok(has_function_privilege('anon', 'public.search_verses(text, text[], boolean, int, int, smallint, smallint, int, int)', 'execute'), 'anonymous readers may search');

-- A version in any language can be loaded (R-3.6), but only a language code.
select lives_ok($$ insert into public.verse_search (verse_id, version, lang, book_ord, text) values ('JHN.3.16', 'TSTML', 'ml', 43, 'ദൈവം ലോകത്തെ സ്നേഹിച്ചു') $$, 'a Malayalam row loads');
select throws_ok($$ insert into public.verse_search (verse_id, version, lang, book_ord, text) values ('JHN.3.17', 'TSTML', 'Malayalam', 43, 'x') $$, '23514', null, 'lang must be a language code');

select * from finish();
rollback;
