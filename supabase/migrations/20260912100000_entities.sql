-- M6: entity search. One row per place (people and articles join later),
-- loaded from the pipeline's entities.csv by scripts/load-search.sh. Names in
-- both scripts are normalised with the same tamil_norm as verses, so Tamil
-- letter folding, suffix stripping and prefix matching apply to place names.

create table public.entity_search (
  id text primary key,
  type text not null,
  slug text not null,
  name_en text not null,
  names_ta text not null default '',
  alt_en text not null default '',
  weight real not null default 0,
  norm text generated always as (public.tamil_norm(name_en || ' ' || names_ta || ' ' || alt_en)) stored,
  tsv tsvector generated always as (to_tsvector('simple', public.tamil_norm(name_en || ' ' || names_ta || ' ' || alt_en))) stored
);
create index entity_search_tsv on public.entity_search using gin (tsv);
create index entity_search_trgm on public.entity_search using gin (norm extensions.gin_trgm_ops);
grant select on public.entity_search to anon, authenticated;

-- Ranked entity lookup: full-text with prefix matching first, trigram
-- similarity as the fallback, mention weight as a tie-breaker.
create or replace function public.search_entities(q text, lim int default 8)
returns table (id text, type text, slug text, name_en text, names_ta text, rank real)
language sql
stable
parallel safe
as $$
  with p as (
    select public.tamil_norm(q) as nq, public.tamil_tsquery(q) as tq
  )
  select e.id, e.type, e.slug, e.name_en, e.names_ta,
         ((case when e.tsv @@ p.tq then 1.0 else 0.0 end)
          + similarity(e.norm, p.nq)
          + e.weight * 0.05)::real as rank
  from public.entity_search e, p
  where length(p.nq) >= 2
    and (e.tsv @@ p.tq or e.norm % p.nq)
  order by rank desc, e.name_en
  limit lim;
$$;

grant execute on function public.search_entities(text, int) to anon, authenticated;
