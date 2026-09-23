-- "Most highlighted this month" on the home page (R-2.5): the verses most
-- readers highlighted in the last 30 days. The same rules as
-- verse_highlight_counts (ADR-8): opted-in profiles only, distinct readers,
-- nothing below three, no user id leaves Postgres. A highlight counts from its
-- last change (setHighlight re-inserts a range, so that is when it was made).
-- Refreshed hourly, five minutes after the all-time counts.
create materialized view public.verse_highlight_month as
  select h.book, h.chapter, v as verse, count(distinct h.user_id)::int as users
  from public.highlights h
  join public.profiles p on p.user_id = h.user_id and p.share_aggregates
  cross join lateral generate_series(h.verse_start::int, h.verse_end::int) as v
  where h.updated_at >= now() - interval '30 days'
  group by h.book, h.chapter, v
  having count(distinct h.user_id) >= 3;
create unique index verse_highlight_month_key on public.verse_highlight_month (book, chapter, verse);
create index verse_highlight_month_users on public.verse_highlight_month (users desc);
grant select on public.verse_highlight_month to anon, authenticated;

select cron.schedule('refresh-verse-highlight-month', '10 * * * *',
  $$refresh materialized view concurrently public.verse_highlight_month$$);
