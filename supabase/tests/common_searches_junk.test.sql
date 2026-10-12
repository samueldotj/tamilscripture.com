-- Crawler templates and encoding-mangled queries never reach common searches.
begin;
create extension if not exists pgtap with schema extensions;
select plan(7);

select ok(public.is_real_search('anbu'), 'an English-letter search is real');
select ok(public.is_real_search('அன்பு'), 'a Tamil search is real');
select ok(public.is_real_search('"நித்திய ஜீவன்"'), 'a quoted phrase is real');
select ok(not public.is_real_search('{search_term_string}'), 'the SearchAction template is not');
select ok(not public.is_real_search('????'), 'question marks alone are not');

delete from public.search_log;
select public.log_search('{search_term_string}', 'en', 0);
select public.log_search('????', 'en', 0);
select public.log_search('love', 'en', 12);
select is((select array_agg(query) from public.search_log), array['love'], 'only the real search is logged');

-- Junk logged before the fix drops out of the view.
insert into public.search_log (query, lang, results, searched_at)
select q, 'en', 0, now() - (d || ' days')::interval
from unnest(array['{search_term_string}', '????', 'faith']) q, generate_series(1, 5) d;
refresh materialized view public.common_searches;
select is((select array_agg(query) from public.common_searches), array['faith'], 'common searches keep only real ones');

select * from finish();
rollback;
