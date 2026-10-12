-- Keep junk out of common searches. Crawlers fill in the home page's schema.org
-- SearchAction literally ("{search_term_string}"), and a client that loses the
-- encoding sends Tamil as "????". A real search has at least one English or
-- Tamil letter and no template braces or markup.
create or replace function public.is_real_search(q text)
returns boolean
language sql
immutable
as $$
  select q ~ '[A-Za-z஀-௿]' and q !~ '[{}<>]';
$$;

create or replace function public.log_search(q text, lang text, results int)
returns void
language sql
security definer
set search_path = public
as $$
  insert into public.search_log (query, lang, results)
  select trim(q), lang, results
  where length(trim(q)) between 2 and 120
    and public.is_real_search(trim(q));
$$;

-- The view also filters, so junk already in the log drops out at the next refresh.
drop materialized view public.common_searches;
create materialized view public.common_searches as
  select lower(query) as query, lang,
         count(*)::int as count_30d,
         count(distinct searched_at::date)::int as days
  from public.search_log
  where searched_at > now() - interval '30 days'
    and lower(query) not in (select query from public.search_blocklist)
    and public.is_real_search(query)
  group by lower(query), lang
  having count(distinct searched_at::date) >= 5
  order by count(*) desc;
create unique index common_searches_key on public.common_searches (query, lang);
grant select on public.common_searches to anon, authenticated;
