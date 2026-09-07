#!/usr/bin/env bash
# Load the pipeline's search CSVs into public.verse_search.
# Usage: scripts/load-search.sh <content-dir> <postgres-url>
# Rows are upserted per version and stale rows for that version removed, so
# search stays available during the load.
set -euo pipefail

content="${1:?content dir}"
db="${2:?postgres url}"
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
