# Roadmap: places, dictionary, people and maps

Status: proposal for prioritisation, 12 Sep 2026. Nothing here is built.

This document turns the data-source discussion (`bible_project_maps_data_summary.md`) into a plan that fits the site as it stands: scripture is static content built by the Rust pipeline and served from the CDN; Postgres holds only search and personal data; every reading page has a performance budget guarded in CI. The new features follow the same rule. Entities, articles and map layers are content build outputs. The database gains one search table. The reader gains tabs in the context panel it already has.

## 1. Decisions taken

| Question | Decision |
|---|---|
| Tamil descriptions | Owner supplies Tamil translations later; until then articles are English with a visible language badge. Names get Tamil forms from the alignment table in phase A1. |
| Tamil name alignment | Generated from verse co-occurrence, then reviewed by the owner before it ships. |
| Order | Places, then dictionary, then people, then the interactive map. |
| ShareAlike sources | Allowed, kept in their own directories with their own licence files, never merged into a public-domain file. |
| Theological fit | Reformed sources only. Public-domain candidates: Easton (Matthew George Easton, Presbyterian), ISBE 1915 (James Orr, United Free Church of Scotland). Smith's (Anglican) and Aquifer are held for owner review of sample articles before inclusion. |
| Map style | Version 1 is a plain outline: coastline, seas, rivers, our own labels. No terrain, no modern layers. |
| Journeys and regions | Whatever open data exists at usable quality ships in version 1; the rest is hand-authored later. |
| Tile hosting | Vercel Blob, same account, no second provider. |
| Search | Places, people and articles appear in the one search box and in the reference box suggestions, with the existing Tamil normaliser. |

## 2. Data sources

Every source lives under `data/entities/<source>/` with `LICENSE`, `SOURCE.md` (URL, download date, file hash) and the raw download, the same convention as `data/versions/` and `data/xrefs/`. The build refuses a source directory without a licence file. Licences below are what the discussion recorded; each must be verified against the exact file before it is committed.

| Source | Role | Licence to verify | Directory |
|---|---|---|---|
| OpenBible Geocoding | Place identity, coordinates, verse-to-place links, alternate names | CC BY 4.0 | `data/entities/openbible-geo/` |
| TIPNR (STEP Bible) | People and place identity, original-language names, verse links, disambiguation of same-named people | Open, attribution terms to check per file | `data/entities/tipnr/` |
| Easton's Bible Dictionary | Readable articles for people, places, terms | Public domain | `data/entities/eastons/` |
| ISBE, 1915 edition | Long-form reference articles, shown as "Read more" | Public domain (US) | `data/entities/isbe/` |
| Smith's Bible Dictionary | Additional articles | Public domain edition to confirm | Held pending review |
| Aquifer Open Bible Dictionary | Modern readable articles | CC BY-SA, to confirm | Held pending review; own directory if approved |
| Theographic knowledge graph | Events, periods, relationships | CC BY-SA, to confirm | Deferred to phase A5 |
| Journeys and regions GeoJSON | Routes and historical borders | Per file; own work is CC BY | `data/entities/geo/` |
| Base map extract | Coastline, water, rivers for the tile archive | Natural Earth (public domain) preferred over OpenStreetMap (ODbL) for version 1 | Built in CI, not committed |

Natural Earth is chosen for the outline map because it is public domain and small. OpenStreetMap's ODbL would add a share-alike obligation on the derived tile archive; it can be revisited if terrain or detail is wanted later.

## 3. Architecture

### Pipeline

A new crate `crates/entity-ingest` joins the Cargo workspace. It runs after `usfm-ingest` in the content build and reads the chapter JSON so it can locate Tamil surface forms.

```text
data/entities/*            usfm-ingest output           data/entities/names-ta.toml
       │                          │                              │  (owner-reviewed)
       └──────────┬───────────────┴──────────────────────────────┘
                  ▼
           entity-ingest (Rust)
                  │
   ┌──────────────┼──────────────────┬──────────────────────┬────────────────────┐
   ▼              ▼                  ▼                      ▼                    ▼
entities/      mentions/          articles/             geo/                entities.csv
{type}/{id}    {BOOK}/{ch}.json   {source}/{id}.json    places.geojson      (search loader)
.json          verse → ids        one per article       journeys.geojson
                                                        regions.geojson
```

Outputs land in `content/{build}/entities/…` and are served like chapter JSON. The build is deterministic and validated: every mention must resolve to an entity, every entity must have at least one English name, every place must have coordinates or an explicit `unlocated: true`, and the CI determinism diff covers the new files.

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
  "mentions": ["GEN.14.15", "GEN.15.2", "ACT.9.2"],   // verse ids, capped in the file, full list in mentions/
  "related": { "people": ["person/paul", "person/ananias-of-damascus"], "events": [] },
  "articles": [
    { "source": "eastons", "id": "damascus", "lang": "en", "licence": "PD" },
    { "source": "isbe", "id": "damascus", "lang": "en", "licence": "PD" }
  ],
  "provenance": { "identity": "tipnr:…", "geo": "openbible-geo:…" }
}
```

People carry `role`, `father`, `tribe` and `period` where TIPNR provides them, and `disambiguation` text for same-named people ("Zechariah, son of Berechiah, the prophet"). Articles are separate files keyed by source so licences never mix; an entity only points at them.

Per-chapter mentions:

```jsonc
// content/{build}/entities/mentions/ACT/13.json
{ "ACT.13.1": ["place/antioch-syria", "person/barnabas", "person/simeon-niger", "person/lucius-of-cyrene", "person/manaen", "person/saul"],
  "ACT.13.4": ["place/seleucia", "place/cyprus"], … }
```

### Tamil name alignment

`data/entities/names-ta.toml` maps each entity to its Tamil surface forms per version. `entity-ingest` has a `--draft-names` mode that proposes forms by co-occurrence: for each entity, collect the verses it appears in, tokenise the Tamil text of those verses, apply the existing `tamil-norm` folding, and rank tokens that recur across the entity's verses and rarely elsewhere. The draft is written with a confidence score; the owner reviews and edits the TOML; the build reads only the reviewed file and fails on entities marked `review = true`. Expect roughly 1,200 places and 3,000 people; places first.

### Reformed-content gate

Inclusion is decided per source, and a `data/entities/blocklist.toml` lets the owner exclude individual articles by source and id with a reason. The build drops blocked articles and the site never links to them. Sample articles from Smith's and Aquifer are generated in phase A2 for the owner's review before either source is added.

### Maps

Two tiers, as discussed.

- **Static tier.** For every chapter with located places, and for every journey, the content build renders a WebP (and a small PNG fallback) of an outline map with the places labelled, using a headless renderer in the GitHub Actions job. Files go to `content/{build}/entities/maps/{BOOK}/{ch}.webp` and `…/journeys/{id}.webp`, about 20–40 kB each. The reader shows this image with no JavaScript.
- **Interactive tier.** MapLibre GL JS, loaded only when a reader taps "Explore map". The base map is a PMTiles archive built from Natural Earth (coastline, ocean, lakes, rivers, zooms 3–10 over the biblical world) and uploaded to Vercel Blob by the deploy workflow; the URL is a public environment variable. Places, journeys and regions are our own GeoJSON layers fetched from `content/…/entities/geo/`. MapLibre is code-split so the reader route budget (120 kB gzipped) is untouched; the atlas route gets its own size-limit entry.

Historical regions are stored with `period`, `start_year`, `end_year` so a period selector can come later; version 1 ships whatever open data passes review, and the selector is only built if at least two periods exist.

### URLs

| Route | Rendering | Content |
|---|---|---|
| `/place/{slug}` | ISR | Entity page: names in both scripts, map, verses that mention it grouped by book, related people, articles |
| `/person/{slug}` | ISR | Entity page: names, disambiguation, family, verses, places, articles |
| `/dictionary` | Prerender | Index by source with letter navigation and the language badge |
| `/dictionary/{source}/{id}` | ISR | Article with attribution and licence, links to entities |
| `/atlas` | Prerender | Map index: journeys and regions, entry to the interactive map |
| `/atlas/{journey}` | ISR | Journey page: static map, ordered stops, passages |
| `/atlas/explore` | Client-only | Interactive MapLibre map with layer toggles |
| `/api/entities/search` | Server | Entity search for the search box and reference box |

Entity pages must be ISR, not prerendered, for the same reason chapters are (ADR-1, the Vercel route cap). Tamil paths such as `/இடம்/தமஸ்கு` redirect to the English slug, following ADR-7.

### Search

One new table, `entity_search (id, type, names_norm tsvector, names_ta, names_en, weight)`, loaded by the same `load-search.sh` step from `entities.csv`, indexed with the existing `tamil_tsvector` so misspellings and Tamil letter folding work for names. The search page runs entity and verse queries together and shows matching entities as cards above the verse hits. The reference box suggestion list adds entity rows beneath book suggestions so typing "Damasc" or "தமஸ்" offers the place directly. The wasm reference parser is unchanged.

### Reader integration

The context panel (desktop) and bottom sheet (phones) gain tabs when a verse is selected: Related verses, Places, People, Dictionary. Places shows the static chapter map with the selected verse's places emphasised, then the list; each row opens the entity page or, on desktop, swaps the panel to that entity. Verse text is not decorated by default; a setting "Underline names" adds a dotted underline to aligned Tamil and English name tokens that opens the entity, off by default so the reading page stays quiet and its layout-shift budget holds. Chapter pages preload nothing extra; mentions JSON is fetched when the panel opens.

### Performance and budgets

- Reading pages: no new blocking requests. Mentions JSON and map images load on demand. CLS budget unchanged.
- Entity pages: 500 ms target like verse pages, static map image only.
- Atlas explore: MapLibre plus PMTiles headers under 250 kB gzipped before tiles; own size-limit entry; own Lighthouse URL with a relaxed performance threshold.
- Content build: the map render step must finish under five minutes in CI or it moves to a separate workflow that runs only when entity data changes.

### Licensing layout

Each article file carries `source`, `licence`, `attribution` and `url`. The site shows attribution under every article and map, and the About page gains a table of all entity sources. ShareAlike material stays in its own files and directories; the pipeline never rewrites CC BY-SA text into a combined file. Our own GeoJSON and the alignment table are released CC BY so they can be reused by others.

## 4. Phases

Effort is rough calendar time at the pace of the earlier milestones, excluding the owner's review time.

| Phase | Goal | Exit test | Effort |
|---|---|---|---|
| **A0 · Sources and licences** | Every dataset downloaded, licence verified, recorded under `data/entities/`. Sample articles for owner review. | Owner has approved the source list and the samples. | 1 week |
| **A1 · Places** | Place entities with coordinates, Tamil names, per-chapter mentions, static chapter maps, place pages, Places tab, entity search. | Acts 13 shows its places on a map in the panel; "தமஸ்கு" in the search box opens Damascus. | 2–3 weeks |
| **A2 · Dictionary** | Easton and ISBE ingested, article pages, dictionary index, Dictionary tab, articles linked from entities, blocklist in place. Smith's and Aquifer added only if approved. | Every place page with an Easton article shows it with attribution; a blocked article is unreachable. | 1–2 weeks |
| **A3 · People** | TIPNR people with disambiguation, Tamil names reviewed, person pages, People tab, name underline setting. | Selecting Acts 13:1 lists six people, each opening a page with the right disambiguation. | 2–3 weeks |
| **A4 · Interactive map** | PMTiles archive on Vercel Blob, MapLibre explore page, place and journey layers, journey pages. | Explore loads under budget on 4G; Paul's journeys draw with ordered stops. | 2 weeks |
| **A5 · Events and periods** | Theographic events and periods if licence and value justify it; period selector for regions. | Optional; decided after A4. | 2 weeks |
| **A6 · Tamil articles** | Owner-supplied Tamil translations ingested as their own source, shown by default for Tamil UI with English as fallback. | A place page in Tamil UI shows the Tamil article first. | 1 week after texts arrive |

### A0 · Sources and licences

| # | Task | Refs |
|---|---|---|
| A0.1 | Download OpenBible Geocoding, TIPNR, Easton, ISBE; record `LICENSE`, `SOURCE.md` with hashes; build fails without a licence file | §2 |
| A0.2 | Generate ten sample articles each from Smith's and Aquifer for the owner's doctrinal review; record the decision | §1 |
| A0.3 | Write `docs/design.md` §15 (entities) and the ADRs: content-build entities, ISR entity pages, PMTiles on Blob, separate-file licensing | design §12 |
| A0.4 | Add requirement IDs R-11.x (places), R-12.x (dictionary), R-13.x (people), R-14.x (maps) to `docs/requirements.md` | requirements |

### A1 · Places

| # | Task | Refs |
|---|---|---|
| A1.1 | `crates/entity-ingest`: parse OpenBible Geocoding and TIPNR places; reconcile identities; emit `entities/place/*.json` and `mentions/` | §3 |
| A1.2 | `--draft-names` co-occurrence aligner over IRVTAM and TCV; write `data/entities/names-ta.toml` draft with confidence; owner review round; build fails on `review = true` | §3 |
| A1.3 | Validation: coordinates or `unlocated`, every mention resolves, determinism diff in CI | §3 |
| A1.4 | Static map renderer in CI: Natural Earth outline, labelled places per chapter, WebP + PNG; budget check on size and time | §3 |
| A1.5 | `/place/{slug}` ISR page with names, map, verses by book, attribution; Tamil path redirects | ADR-1, ADR-7 |
| A1.6 | Context panel and bottom sheet: Places tab with map and list; mentions fetched on open | reader |
| A1.7 | `entity_search` table and loader; `/api/entities/search`; entity cards on the search page; entity rows in reference box suggestions | §3, ADR-2 |
| A1.8 | Sitemap for places; About page source table | SEO |

### A2 · Dictionary

| # | Task | Refs |
|---|---|---|
| A2.1 | Parse Easton and ISBE into `articles/{source}/{id}.json` with attribution; link articles to entities by name with a review list of ambiguous matches | §3 |
| A2.2 | `blocklist.toml` honoured by the build | §3 |
| A2.3 | `/dictionary` index and `/dictionary/{source}/{id}` pages with language badge and licence | §3 |
| A2.4 | Dictionary tab in the panel; "Read more" for ISBE length | reader |
| A2.5 | Articles searchable by title in the search box | §3 |
| A2.6 | Add Smith's and Aquifer in their own directories if approved in A0.2 | §1 |

### A3 · People

| # | Task | Refs |
|---|---|---|
| A3.1 | TIPNR people: identity, disambiguation, relations, mentions | §3 |
| A3.2 | Tamil name draft and owner review for people | §3 |
| A3.3 | `/person/{slug}` pages; People tab; related people on place pages | §3 |
| A3.4 | "Underline names" setting with pre-paint class, off by default; CLS check in CI | reader |
| A3.5 | People in search and reference box suggestions | §3 |

### A4 · Interactive map

| # | Task | Refs |
|---|---|---|
| A4.1 | Build PMTiles from Natural Earth in the deploy workflow; upload to Vercel Blob; public URL as env var; cache headers | §3 |
| A4.2 | MapLibre style: land, water, rivers, our labels; light and dark variants from the theme tokens | §3 |
| A4.3 | `/atlas/explore` client-only route, code-split; layer toggles; own size-limit and Lighthouse entries | §3 |
| A4.4 | Journeys and regions GeoJSON from available open data; `/atlas` and `/atlas/{journey}` pages with static maps and ordered stops | §3 |
| A4.5 | "Explore map" links from chapter panel, place pages and journey pages | reader |

### A5 · Events and periods (optional)

| # | Task | Refs |
|---|---|---|
| A5.1 | Verify Theographic licence; ingest events and periods into their own directory | §2 |
| A5.2 | Events on entity pages; period selector on the explore map when two or more periods exist | §3 |

### A6 · Tamil articles

| # | Task | Refs |
|---|---|---|
| A6.1 | Ingest owner-supplied Tamil articles as source `ta-owner` with its own licence; Tamil UI shows them first | §1 |
| A6.2 | Full-text search over Tamil articles with `tamil_tsvector` | §3 |

## 5. Risks

| Risk | Mitigation |
|---|---|
| Tamil name alignment is noisy for rare names and same-named people | Draft carries confidence; low-confidence rows default to `review = true`; ship places first where names are more regular |
| A source's actual file licence differs from the discussion | A0 verifies each file and records the hash; build refuses missing licences |
| Doctrinal mismatch in individual articles | Source-level gate plus per-article blocklist; owner reviews samples before a source is added |
| Map rendering slows the content build | Time budget in CI; move to a separate workflow keyed on entity data changes |
| Route count on Vercel | Entity pages are ISR; only indexes are prerendered |
| Reading performance regresses | Nothing new on the reading critical path; panel content loads on demand; existing Lighthouse and size budgets extended, not relaxed |
| Journey and region data of poor quality | Ship only reviewed files; hand-author the short list later |

## 6. Open items for the owner

1. Delivery format for Tamil translations when they arrive (per-article Markdown with the entity id is easiest).
2. Approve or reject Smith's and Aquifer after reading the A0.2 samples.
3. Choose which phases come before the outstanding M3–M5 items (settings sync, RLS tests, error tracking, custom domain verification).
