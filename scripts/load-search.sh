#!/usr/bin/env bash
# Load the pipeline's search CSVs into public.verse_search.
# Usage: scripts/load-search.sh <content-dir> <postgres-url>
# Rows are upserted per version and stale rows for that version removed, so
# search stays available during the load.
set -euo pipefail

content="${1:?content dir}"
db="${2:?postgres url}"

# The direct host (db.<ref>.supabase.co) is IPv6-only and unreachable from
# GitHub runners. Use the Session pooler string from the dashboard's Connect
# dialog instead: postgres.<ref>@aws-N-<region>.pooler.supabase.com:5432.
if [[ "$db" == *"@db."*".supabase.co"* ]]; then
  echo "error: SUPABASE_DB_URL is the direct connection; use the Session pooler URI (IPv4)." >&2
  exit 2
fi
build=$(python3 -c "import json,sys; print(json.load(open('$content/manifest.json', encoding='utf-8'))['build'])")
dir="$content/$build/search"

for csv in "$dir"/*.csv; do
  version=$(basename "$csv" .csv)
  echo "loading $version from $csv"
  psql "$db" -v ON_ERROR_STOP=1 -q <<SQL
begin;
create temp table stage (like public.verse_search including defaults) on commit drop;
alter table stage drop column text_norm, drop column tsv;
\\copy stage (verse_id, version, lang, book_ord, text) from '$csv' with (format csv, header true, encoding 'UTF8')
insert into public.verse_search (verse_id, version, lang, book_ord, text)
  select verse_id, version, lang, book_ord, text from stage
  on conflict (version, verse_id) do update
    set lang = excluded.lang, book_ord = excluded.book_ord, text = excluded.text
    where public.verse_search.text is distinct from excluded.text;
delete from public.verse_search v
  where v.version = '$version'
    and not exists (select 1 from stage s where s.verse_id = v.verse_id);
commit;
SQL
done
psql "$db" -Atc "select version, count(*) from public.verse_search group by 1 order by 1"

# Entities (M6): places from entity-ingest, one table, replaced as a whole.
entities="$dir/entities.csv"
if [[ -f "$entities" ]]; then
  echo "loading entities from $entities"
  psql "$db" -v ON_ERROR_STOP=1 -q <<SQL
begin;
create temp table estage (id text, type text, slug text, name_en text, names_ta text, alt_en text, weight real) on commit drop;
\copy estage (id, type, slug, name_en, names_ta, alt_en, weight) from '$entities' with (format csv, header true, encoding 'UTF8')
insert into public.entity_search (id, type, slug, name_en, names_ta, alt_en, weight)
  select id, type, slug, name_en, names_ta, alt_en, weight from estage
  on conflict (id) do update
    set type = excluded.type, slug = excluded.slug, name_en = excluded.name_en,
        names_ta = excluded.names_ta, alt_en = excluded.alt_en, weight = excluded.weight
    where (public.entity_search.name_en, public.entity_search.names_ta, public.entity_search.alt_en, public.entity_search.weight)
          is distinct from (excluded.name_en, excluded.names_ta, excluded.alt_en, excluded.weight);
delete from public.entity_search e where not exists (select 1 from estage s where s.id = e.id);
commit;
SQL
  psql "$db" -Atc "select type, count(*) from public.entity_search group by 1 order by 1"
fi
