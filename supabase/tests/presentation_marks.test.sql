-- Verse presentations: highlighted words on a slide verse (marks), per
-- version, as verse.word positions, never text.
begin;
create extension if not exists pgtap with schema extensions;
select plan(9);

select ok(public.check_slides('[{"id":"a1","notes":"","verses":[{"book":"JHN","chapter":3,"start":16,"end":16,"marks":{"IRVTAM":["16.0","16.3"],"KJV":["16.7"]}}]}]'::jsonb), 'marks per version');
select ok(public.check_slides('[{"id":"a1","notes":"","verses":[{"book":"JHN","chapter":3,"start":16,"end":16,"marks":{}}]}]'::jsonb), 'empty marks');
select ok(not public.check_slides('[{"id":"a1","notes":"","verses":[{"book":"JHN","chapter":3,"start":16,"end":16,"marks":["16.0"]}]}]'::jsonb), 'marks must be an object');
select ok(not public.check_slides('[{"id":"a1","notes":"","verses":[{"book":"JHN","chapter":3,"start":16,"end":16,"marks":{"irvtam":["16.0"]}}]}]'::jsonb), 'version keys are codes');
select ok(not public.check_slides('[{"id":"a1","notes":"","verses":[{"book":"JHN","chapter":3,"start":16,"end":16,"marks":{"KJV":["God"]}}]}]'::jsonb), 'a mark is a position, never a word');
select ok(not public.check_slides('[{"id":"a1","notes":"","verses":[{"book":"JHN","chapter":3,"start":16,"end":16,"marks":{"KJV":[16]}}]}]'::jsonb), 'positions are strings');
select ok(not public.check_slides(('[{"id":"a1","notes":"","verses":[{"book":"JHN","chapter":3,"start":16,"end":16,"marks":{"KJV":' || (select jsonb_agg('16.' || i) from generate_series(1, 301) i)::text || '}}]}]')::jsonb), 'at most 300 marks a version');

select ok(public.check_slides('[{"id":"a1","notes":"","verses":[{"book":"JHN","chapter":3,"start":16,"end":16,"marks":{"KJV":["16.0","16.1:g","16.2:r"]}}]}]'::jsonb), 'a colour after the position');
select ok(not public.check_slides('[{"id":"a1","notes":"","verses":[{"book":"JHN","chapter":3,"start":16,"end":16,"marks":{"KJV":["16.1:#f00"]}}]}]'::jsonb), 'only the known colours');

select * from finish();
rollback;
