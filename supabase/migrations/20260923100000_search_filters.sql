-- Search may be restricted to a testament, a book or a chapter range (R-5.8).
-- Books are given by canonical order (book_ord, 1-66), so a testament is a
-- range of books and a single book is book_min = book_max. A chapter range
-- applies within that book; the chapter is the middle part of the verse id
-- ('JHN.3.16'). Every new parameter defaults to "no limit", so callers that
-- pass only the first five arguments get the same results as before.
drop function if exists public.search_verses(text, text[], boolean, int, int);

create function public.search_verses(
  q text, versions text[], exact boolean default false, lim int default 50, off int default 0,
  book_min smallint default null, book_max smallint default null,
  ch_min int default null, ch_max int default null)
returns table (verse_id text, version text, text text, rank real, book_ord smallint, total bigint)
language sql
stable
parallel safe
as $$
  with p as (
    select trim(public.tamil_norm(q)) as nq,
           public.tamil_tsquery(q) as tq,
           websearch_to_tsquery('english', q) as eq
  ),
  -- Inlined into each branch below, so the full-text and trigram indexes still apply.
  scope as not materialized (
    select v.* from public.verse_search v
    where v.version = any(versions)
      and (book_min is null or v.book_ord >= book_min)
      and (book_max is null or v.book_ord <= book_max)
      and (ch_min is null or split_part(v.verse_id, '.', 2)::int between ch_min and coalesce(ch_max, ch_min))
  ),
  fts as (
    select v.verse_id, v.version, v.text, v.book_ord,
           ts_rank_cd(v.tsv, case when v.lang = 'en' then p.eq else p.tq end) as rank
    from scope v, p
    where not exact
      and p.nq <> ''
      and ((v.lang = 'en' and v.tsv @@ p.eq)
        or (v.lang <> 'en' and v.tsv @@ p.tq))
  ),
  exact_hits as (
    select v.verse_id, v.version, v.text, v.book_ord, 1.0::real as rank
    from scope v, p
    where exact
      and p.nq <> ''
      and v.text_norm like '%' || p.nq || '%'   -- trigram-indexed prefilter
      and v.text ilike '%' || q || '%'           -- confirm on the display text
  ),
  fuzzy as (
    select v.verse_id, v.version, v.text, v.book_ord,
           (word_similarity(p.nq, v.text_norm) * 0.5)::real as rank
    from scope v, p
    where not exact
      and p.nq <> ''
      and length(p.nq) >= 3
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

grant execute on function public.search_verses(text, text[], boolean, int, int, smallint, smallint, int, int) to anon, authenticated;
