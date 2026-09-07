-- Initial schema for tamilscripture.com.
-- Scripture text lives in static files; Postgres holds the search table now
-- and personal data from M3. See docs/design.md sections 6 and 7.

create extension if not exists pg_trgm with schema extensions;

-- Placeholder normaliser. M2 replaces the body with the table-driven function
-- generated from crates/tamil-norm and rebuilds the generated columns.
create or replace function public.tamil_norm(t text)
returns text
language sql
immutable
parallel safe
as $$
  select lower(normalize(t, NFC));
$$;

create table public.verse_search (
  verse_id   text     not null,                      -- 'JHN.3.16'
  version    text     not null,                      -- 'IRVTAM'
  lang       text     not null check (lang in ('ta', 'en')),
  book_ord   smallint not null,                      -- canonical book order, 1..66
  text       text     not null,                      -- NFC, as displayed
  text_norm  text generated always as (public.tamil_norm(text)) stored,
  tsv        tsvector generated always as (
               case lang
                 when 'en' then to_tsvector('english', text)
                 else to_tsvector('simple', public.tamil_norm(text))
               end) stored,
  primary key (version, verse_id)
);

create index verse_search_tsv  on public.verse_search using gin (tsv);
create index verse_search_trgm on public.verse_search using gin (text_norm extensions.gin_trgm_ops);
create index verse_search_book on public.verse_search (version, book_ord);

-- Read-only for everyone; writes only via the deploy job's database role.
alter table public.verse_search enable row level security;
create policy "verse_search is public" on public.verse_search
  for select using (true);
grant select on public.verse_search to anon, authenticated;
