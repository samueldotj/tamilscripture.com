-- Tamil is agglutinative: அன்பு should also find அன்பாக and அன்புகூர்ந்தார்.
-- Query tokens of three or more characters match as prefixes (GIN supports
-- prefix matching on tsvector). Also removes the temporary diagnostic.
create or replace function public.tamil_tsquery(q text)
returns tsquery
language sql
immutable
parallel safe
as $$
  select coalesce(
    (select string_agg(
              case when length(w) >= 3 then format('%L:*', w) else format('%L', w) end,
              ' & ')
       from unnest(string_to_array(public.tamil_norm(q), ' ')) as u(w)
      where w <> '')::tsquery,
    ''::tsquery);
$$;

drop function if exists public.search_debug(text);
