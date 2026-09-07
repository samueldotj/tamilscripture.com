-- M4: community aggregates (design §8, ADR-8). Distinct users per verse from
-- opted-in profiles, thresholded inside the view so no count below three and
-- no user id ever leaves Postgres. Refreshed hourly by pg_cron.

create materialized view public.verse_highlight_counts as
  select h.book, h.chapter, v as verse, count(distinct h.user_id)::int as users
  from public.highlights h
  join public.profiles p on p.user_id = h.user_id and p.share_aggregates
  cross join lateral generate_series(h.verse_start::int, h.verse_end::int) as v
  group by h.book, h.chapter, v
  having count(distinct h.user_id) >= 3;
create unique index verse_highlight_counts_key on public.verse_highlight_counts (book, chapter, verse);
create index verse_highlight_counts_book on public.verse_highlight_counts (book);
grant select on public.verse_highlight_counts to anon, authenticated;

select cron.schedule('refresh-verse-highlight-counts', '5 * * * *',
  $$refresh materialized view concurrently public.verse_highlight_counts$$);
