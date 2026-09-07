-- Search, second pass. The first production queries showed:
--   * Tamil full-text timed out: the default text-search parser splits Tamil
--     at vowel signs and virama, so tsvectors did not contain whole words.
--     Build tsvector/tsquery from our own normalised tokens instead.
--   * Fuzzy matching compared the query word against whole verses with `%`;
--     word similarity (`<%`) is the right operator and is GIN-indexed.
--   * Exact phrase scanned every row with lower(); use the trigram index on
--     text_norm as a prefilter and confirm on the display text.

-- Tokens are the space-separated words of tamil_norm(); positions preserved.
create or replace function public.tamil_tsvector(t text)
returns tsvector
language sql
immutable
parallel safe
as $$
  select coalesce(
    (select string_agg(format('%L:%s', w, i), ' ')
       from unnest(string_to_array(public.tamil_norm(t), ' ')) with ordinality as u(w, i)
      where w <> '')::tsvector,
    ''::tsvector);
$$;

-- All words must match (AND), same normalisation as the index.
create or replace function public.tamil_tsquery(q text)
returns tsquery
language sql
immutable
parallel safe
as $$
  select coalesce(
    (select string_agg(format('%L', w), ' & ')
       from unnest(string_to_array(public.tamil_norm(q), ' ')) as u(w)
      where w <> '')::tsquery,
    ''::tsquery);
$$;

alter table public.verse_search drop column tsv;
alter table public.verse_search
  add column tsv tsvector generated always as (
    case lang
      when 'en' then to_tsvector('english', text)
      else public.tamil_tsvector(text)
    end) stored;
create index verse_search_tsv on public.verse_search using gin (tsv);

create or replace function public.search_verses(
  q text, versions text[], exact boolean default false, lim int default 50, off int default 0)
returns table (verse_id text, version text, text text, rank real, book_ord smallint, total bigint)
language sql
stable
parallel safe
as $$
  with p as (
    select public.tamil_norm(q) as nq,
           public.tamil_tsquery(q) as tq,
           websearch_to_tsquery('english', q) as eq
  ),
  fts as (
    select v.verse_id, v.version, v.text, v.book_ord,
           ts_rank_cd(v.tsv, case when v.lang = 'en' then p.eq else p.tq end) as rank
    from public.verse_search v, p
    where not exact
      and v.version = any(versions)
      and ((v.lang = 'en' and v.tsv @@ p.eq)
        or (v.lang <> 'en' and v.tsv @@ p.tq))
  ),
  exact_hits as (
    select v.verse_id, v.version, v.text, v.book_ord, 1.0::real as rank
    from public.verse_search v, p
    where exact
      and v.version = any(versions)
      and v.text_norm like '%' || p.nq || '%'   -- trigram-indexed prefilter
      and v.text ilike '%' || q || '%'           -- confirm on the display text
  ),
  fuzzy as (
    select v.verse_id, v.version, v.text, v.book_ord,
           (word_similarity(p.nq, v.text_norm) * 0.5)::real as rank
    from public.verse_search v, p
    where not exact
      and v.version = any(versions)
      and (select count(*) from fts) < 5
      and p.nq <% v.text_norm
      and not exists (select 1 from fts f where f.verse_id = v.verse_id and f.version = v.version)
  ),
  hits as (
    select * from fts
    union all select * from exact_hits
    union all select * from fuzzy
  )
  select verse_id, version, text, rank, book_ord, count(*) over () as total
  from hits
  order by rank desc, book_ord, verse_id
  limit lim offset off;
$$;
