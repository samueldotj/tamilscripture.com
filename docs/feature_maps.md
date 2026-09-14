# Feature design: places and maps

Milestone M6 in the [README](../README.md#milestones). Status: design, 12 Sep 2026. Nothing here is built.

Places are the first biblical entities the site learns about, and the maps are how it shows them. This document also defines the **entity foundation** (pipeline, entity model, Tamil name alignment, entity search) that [feature_dictionary.md](feature_dictionary.md) builds on for people, articles and community review.

The design keeps the site's rule: scripture and reference content are static build outputs served from the CDN; Postgres holds only search and personal data; every reading page has a budget guarded in CI. Nothing here adds a blocking request to a reading page.

## 1. Decisions

| Question | Decision |
|---|---|
| Order of features | Places and maps first; dictionary and people follow on the same entity foundation. |
| Map style | Version 1 is a plain outline: coastline, seas, lakes, rivers, our own labels. No terrain, no modern roads, cities or borders. |
| Base map data | Natural Earth (public domain). OpenStreetMap is avoided in version 1 because its ODbL licence would put a share-alike duty on the derived tile archive. |
| Tile hosting | A PMTiles archive on Vercel Blob in the same account. No tile server, no second provider. |
| Journeys and regions | Whatever open data exists at usable quality ships in version 1; the rest is hand-authored later. |
| Tamil place names | Drafted inside the pipeline from verse co-occurrence, never transliterated by a model; corrected by the community (feature_dictionary.md §6). |
| Search | Places appear in the one search box and in the reference box suggestions, using the existing Tamil normaliser. |

## 2. Data sources

Every source lives under `data/entities/<source>/` with `LICENSE`, `SOURCE.md` (URL, download date, file hash) and the raw download, the convention already used for `data/versions/` and `data/xrefs/`. The build refuses a source directory without a licence file. Licences are as recorded in the planning discussion and must be verified against the exact file before it is committed.

| Source | Role | Licence to verify | Directory |
|---|---|---|---|
| OpenBible Geocoding | Place identity, coordinates, precision, verse-to-place links, alternate names | CC BY 4.0 | `data/entities/openbible-geo/` |
| TIPNR (STEP Bible) | Place identity cross-check, original-language names, verse links; the same file supplies people for M7 | Open, attribution terms to check per file | `data/entities/tipnr/` |
| Natural Earth | Coastline, ocean, lakes, rivers for the tile archive and the static maps | Public domain | Downloaded in CI, not committed |
| UBS Bible Routes (Project MARBLE, Leen Ritmeyer) | 179 GeoJSON route files for Bible stories, drawn instead of straight legs on journey maps; added 13 Sep 2026 | CC BY-SA 4.0 (verified); ShareAlike kept in its own directory, journey maps that include the lines are CC BY-SA | `data/entities/geo/ubs-routes-sa/` |
| Wikidata | Years, coordinates and Tamil labels for the early-church roster (fathers, councils, sees and the cities scripture does not name); added 14 Sep 2026 | CC0 | resolved into `data/entities/church/church.json` |
| Cliopatria (Seshat Global History Databank) | Polity borders with the years they apply to; the atlas timeline, 3400 BCE onward. 1,148 rows and 174 polities inside Europe, the Middle East, Egypt and India; added 14 Sep 2026 | CC BY 4.0 (verified) | `data/entities/geo/polities/` |
| Journeys and regions GeoJSON | Routes and historical borders from open sources or hand-authored | Per file; our own work is CC BY | `data/entities/geo/` |

## 3. Entity foundation

### Pipeline

A new crate `crates/entity-ingest` joins the Cargo workspace. It runs after `usfm-ingest` in the content build and reads the chapter JSON so it can locate Tamil surface forms.

```text
data/entities/*            usfm-ingest output           data/entities/names-ta.toml
       │                          │                       data/entities/overrides/
       └──────────┬───────────────┴──────────────────────────────┘
                  ▼
           entity-ingest (Rust)
                  │
   ┌──────────────┼──────────────────┬──────────────────────┬────────────────────┐
   ▼              ▼                  ▼                      ▼                    ▼
entities/      mentions/          articles/             geo/                entities.csv
{type}/{id}    {BOOK}/{ch}.json   (see dictionary       places.geojson      (search loader)
.json          verse → ids         design)              journeys.geojson
                                                        regions.geojson
```

Outputs land in `content/{build}/entities/…` and are served like chapter JSON. The build is deterministic and validated: every mention resolves to an entity, every entity has at least one English name, every place has coordinates or an explicit `unlocated: true`, and the CI determinism diff covers the new files.

### Entity model

```jsonc
// content/{build}/entities/place/damascus.json
{
  "id": "place/damascus",
  "type": "place",
  "names": {
    "en": "Damascus",
    "ta": { "IRVTAM": ["தமஸ்கு"], "TCV": ["தமஸ்கு"] },
    "he": "דַּמֶּשֶׂק", "el": "Δαμασκός",
    "alt": ["Darmesek"]
  },
  "geo": { "lat": 33.51, "lon": 36.29, "precision": "city", "source": "openbible-geo" },
  "mentions": ["GEN.14.15", "GEN.15.2", "ACT.9.2"],   // capped in the file; full list under mentions/
  "related": { "people": ["person/paul", "person/ananias-of-damascus"], "journeys": ["journey/paul-2"] },
  "articles": [ { "source": "eastons", "id": "damascus", "lang": "en", "licence": "PD" } ],
  "provenance": { "identity": "tipnr:…", "geo": "openbible-geo:…" }
}
```

Articles are separate files owned by the dictionary design; an entity only points at them, so licences never mix.

Per-chapter mentions, fetched only when the context panel opens:

```jsonc
// content/{build}/entities/mentions/ACT/13.json
{ "ACT.13.1": ["place/antioch-syria", "person/barnabas", "person/saul"],
  "ACT.13.4": ["place/seleucia", "place/cyprus"], … }
```

### Tamil name alignment

`data/entities/names-ta.toml` maps each **name string** (not each entity: the thirty people called Zechariah share one Tamil form, and TIPNR's verse lists tell them apart) to its Tamil surface forms per version.

`entity-ingest --draft-names` proposes forms by co-occurrence: for each name, collect the verses it appears in, tokenise the Tamil text of those verses, apply the existing `tamil-norm` folding and suffix stripping, and rank tokens that recur across the name's verses and rarely elsewhere. Candidates are therefore always words present in the text. A model may only break ties between candidates, never transliterate from English or Hebrew, because a form that differs by one letter links to no verse and no search hit. Each row carries a confidence; low-confidence rows show a "draft" badge until a reviewer accepts them through the community review flow.

Build rule: every accepted form must occur in at least one of that name's verses in that version, or the build fails. Expect roughly 1,200 place names and 2,500 names in total once people are added.

### Entity search

One new table, `entity_search (id, type, names_norm tsvector, names_ta, names_en, weight)`, loaded by the same `load-search.sh` step from `entities.csv` and indexed with the existing `tamil_tsvector`, so misspellings and Tamil letter folding work for names. The search page runs entity and verse queries together and shows matching entities as cards above the verse hits. The reference box adds entity rows beneath book suggestions, so typing "Damasc" or "தமஸ்" offers the place directly. The wasm reference parser is unchanged.

### Licensing layout

Each entity records provenance per field. Attribution appears under every map and on the About page's new source table. Our own GeoJSON, the alignment table and override files are released CC BY.

## 4. Maps

Two tiers.

### Static tier

For every chapter with located places, and for every journey, the content build renders a WebP (plus a small PNG fallback) of an outline map with the places labelled, using a headless renderer in the GitHub Actions job. Files go to `content/{build}/entities/maps/{BOOK}/{ch}.webp` and `…/maps/journeys/{id}.webp`, about 20–40 kB each. The reader shows the image with no JavaScript. Light and dark variants are rendered from the theme tokens so the map sits on either ground.

The render step has a time budget of five minutes in CI; if entity data grows past that, it moves to its own workflow triggered only when `data/entities/` changes.

### Interactive tier

MapLibre GL JS, loaded only when a reader taps "Explore map". There is no tile service: the base map is our own GeoJSON, built by `scripts/build-basemap.py` from Natural Earth and served from `content/…/entities/geo/base/` — land, coastline, lakes and rivers at 1:10m over the biblical world, plus a 1:110m `world` silhouette for everything outside it, so the map zooms out to the whole globe (no names out there) instead of stopping at the clip. Places and journeys are our own GeoJSON layers from `content/…/entities/geo/`. Colours are read from the theme tokens and re-read when the theme changes. MapLibre is code-split so the reader route budget (120 kB gzipped) is untouched; the explore route gets its own size-limit entry and Lighthouse URL.

The journeys are listed down the right of the map, grouped by period in chronological order, each a checkbox with the colour and line style it is drawn in (eight hues from `--j-1 … --j-8` crossed with four dash patterns, so no two journeys share an appearance) and a link to its own page. Hovering a row picks its route out and lights up its stops. Above the map, a pair of buttons switches the dots between every located place and only the stops of the journeys that are switched on. Clicking a route names it and links to the journey page; clicking a place enlarges it and names it. `?journey=`, `?place=` and `?chapter=` set the opening view.

### Journeys and regions

```text
journey
  id, name_en, name_ta, period
  stops[]        ordered: place id, passage, note
  route          LineString or MultiLineString
  passages[]     verse ranges

region
  id, name_en, name_ta
  period, start_year, end_year
  geometry       Polygon or MultiPolygon
  source, licence
```

Regions carry period metadata so a period selector can come later; the selector is built only when at least two periods exist. Version 1 ships whatever open data passes review; the Exodus, Jesus' ministry and Paul's four journeys are the hand-authored minimum if no open file qualifies.

### The timeline

Kingdoms and regions come from Cliopatria rather than being hand-drawn. `scripts/build-polities.py` clips it to lon −12…92, lat 5…62 and to 4000 BCE – 350 CE, simplifies to 0.05°, and writes one `polities.geojson` in which every row carries the `from`/`to` years it applies to, a point and bbox span to hang its name on, and its Wikipedia and Wikidata ids. Because the years are in the data, the explore map fetches the file once and filters it in the browser: the slider has one step per year at which a border actually changes (147 of them), and moving it costs no request. The file is 2.9 MB, so it is fetched only when a reader turns Kingdoms on, never on the first paint.

Tamil names for the polities live in `data/entities/geo/polities-ta.toml`, seeded from Wikidata labels by `build-polities.py --fetch-ta` and merged into the GeoJSON as `name_ta`. They are drafts (`draft = true`, and `draft_ta` on the feature) until a maintainer confirms them, and the map marks a drafted name; Wikidata is not a reliable namer on its own. Where the Tamil Bible has a spelling — Assyria, Elam, Phoenicia, Babylonia, Israel, Judah — that spelling wins.

These polygons sit on a present-day coastline, like everything else here: the Nile delta, the head of the Persian Gulf and the Dead Sea were all a different shape in 2000 BCE.

### The early church

`data/entities/church/roster.toml` is the editorial part: who is on the list of fathers, which councils are shown, which sees, and the city each belongs to. Everything datable is resolved from Wikidata by `scripts/build-church.py` — the years a father lived, the year of a council, the coordinates of a city — so no date is typed from memory; where a father's city is left open, his Wikidata work location supplies it. The result is `church.json`, committed, and `entity-ingest` joins it to the gazetteer: an entry names a place in `places.json` when scripture names the city, and otherwise one of the fifteen sites the church data carries of its own (Nicaea, Chalcedon, Hippo Regius, Lugdunum and so on). Anything that cannot be located is reported and dropped rather than drawn at (0, 0).

Several of those sites only have coordinates through the item for the modern city, so the roster gives the ancient name and the build keeps the modern one to show beside it: Edessa (today Şanlıurfa), Nisibis (Nusaybin), Caesarea in Cappadocia (Kayseri), Nicomedia (İzmit), Elvira (Granada).

On the map, the early church is one pin per city — Rome holds four fathers and a see — with a creed mark where a council met, and a popup listing what the city holds with its dates and Wikipedia links. The sidebar lists the councils by year and the fathers by tradition. Tamil names come from `church-ta.toml`, seeded from Wikidata and drafts until confirmed, the same arrangement as the polities.

## 5. URLs

| Route | Rendering | Content |
|---|---|---|
| `/place/{slug}` | ISR | Names in both scripts, static map, verses that mention it grouped by book, related people and journeys, articles |
| `/atlas` | Prerender | Map index: journeys and regions, entry to the interactive map |
| `/atlas/{journey}` | ISR | Journey page: static map, ordered stops, passages |
| `/atlas/explore` | Client-only | Interactive MapLibre map: journey checkboxes, the places toggle, the Kingdoms timeline, the early church, and an optional `?journey=`, `?place=` or `?chapter=` |
| `/api/entities/search` | Server | Entity search for the search box and reference box |

Place pages are ISR, not prerendered, for the same reason chapters are (design ADR-1, the Vercel route cap). Tamil paths such as `/இடம்/தமஸ்கு` redirect to the English slug (ADR-7).

## 6. Reader integration

**Withdrawn 13 Sep 2026:** the owner decided the reading page shows only the text and related verses, so the reader has no Places tab. Mentions and chapter maps are still built for a later use. The original design follows for the record. The context panel (desktop) and bottom sheet (phones) were to gain a **Places** tab when a verse is selected: the static chapter map with the selected verse's places emphasised, then the list. A row opens the place page, or on desktop swaps the panel to that place. An "Explore map" link opens the interactive tier focused on the chapter's places. Verse text is not decorated; the optional name underline belongs to the dictionary design.

## 7. Performance

- Reading pages: no new blocking requests; mentions and map images load when the panel opens; layout-shift budget unchanged.
- Place and journey pages: 500 ms target like verse pages, static image only.
- Explore: MapLibre plus PMTiles headers under 250 kB gzipped before tiles; own size-limit entry; own Lighthouse URL with a relaxed performance threshold.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Tamil name alignment is noisy for rare names | Draft carries confidence; low-confidence rows stay marked draft until reviewed; places first, where names are most regular |
| A source's file licence differs from the discussion | Task 6.1 verifies each file and records the hash; build refuses missing licences |
| Map rendering slows the content build | Time budget; separate workflow keyed on entity data changes |
| Route count on Vercel | Entity pages are ISR; only indexes are prerendered |
| Journey and region data of poor quality | Ship only reviewed files; hand-author the short list |

## 9. Owner items

1. Approve the verified source list after task 6.1.
2. Review the drafted Tamil place names, or delegate to reviewers once M7's review flow exists.
