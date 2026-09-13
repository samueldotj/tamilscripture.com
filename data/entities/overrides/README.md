# Accepted corrections

Written by `scripts/export-overrides.mjs` (workflow `export-overrides.yml`) from
the `entity_accepted` table every 12 hours or on "Publish now". Do not edit by
hand: the next export overwrites these files.

- `names.toml` — `[Name.VERSION] forms = ["…"]`, applied over `names-ta.toml`.
- `articles/{source}/{slug}.toml` — `[[paragraphs]] id / text`, applied over
  the English article and any draft in `../drafts/ta/`.

The build (`entity-ingest`) applies them after the corpus check and marks the
result `provenance = "community"` (or `"owner"` when `owner = true`).
Contributions are CC BY 4.0 (see docs/feature_dictionary.md §6).
