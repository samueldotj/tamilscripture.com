# Roadmap: places, dictionary, people and maps

Status: proposal for prioritisation, 12 Sep 2026. Nothing here is built.

This document turns the data-source discussion (`bible_project_maps_data_summary.md`) into a plan that fits the site as it stands: scripture is static content built by the Rust pipeline and served from the CDN; Postgres holds only search and personal data; every reading page has a performance budget guarded in CI. The new features follow the same rule. Entities, articles and map layers are content build outputs. The database gains one search table. The reader gains tabs in the context panel it already has.

## 1. Decisions taken

| Question | Decision |
|---|---|
| Tamil descriptions | Articles are drafted in Tamil by an AI process run outside this repository from the English public-domain articles, committed as drafts, and corrected by the community (§5). English is shown only where no Tamil draft exists. |
| Tamil name alignment | Drafted inside the pipeline from verse co-occurrence (§3); a model may only choose between corpus candidates, never invent a form. Corrected by the community (§5). |
| Review | Crowdsourced. Signed-in readers suggest paragraph-level corrections; reviewers accept or reject; moderators also manage roles. Readers see nothing until acceptance. |
| Publishing corrections | Export only. A scheduled job every 12 hours exports accepted corrections from the database into the repository, which rebuilds the site. Moderators can trigger the export immediately. The site never reads entity content from Postgres. |
| Contribution licence | Suggesting a correction licenses it CC BY, stated on the form and the account page. |
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

`data/entities/names-ta.toml` maps each **name string** (not each entity: the thirty people called Zechariah share one Tamil form, and TIPNR's verse lists tell them apart) to its Tamil surface forms per version. `entity-ingest` has a `--draft-names` mode that proposes forms by co-occurrence: for each name, collect the verses it appears in, tokenise the Tamil text of those verses, apply the existing `tamil-norm` folding and suffix stripping, and rank tokens that recur across the name's verses and rarely elsewhere. Candidates are therefore always words present in the text. A model is used only to break ties between candidates, never to transliterate. Each row carries a confidence; low-confidence rows are shown with a "draft" badge until a reviewer accepts them (§5). Build rule: every accepted form must occur in at least one of that name's verses in that version, or the build fails. Expect roughly 2,500 distinct names, places first.

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
| **A1b · Community review** | Roles, suggestion and review tables with RLS, suggestion form on names and paragraphs, review queue at `/mod`, 12-hour export workflow with manual trigger. | A reviewer accepts a suggested Tamil name; after "Publish now" the corrected name is on the site and searchable. | 2 weeks |
| **A2 · Dictionary** | Easton and ISBE ingested, article pages, dictionary index, Dictionary tab, articles linked from entities, blocklist in place. Smith's and Aquifer added only if approved. | Every place page with an Easton article shows it with attribution; a blocked article is unreachable. | 1–2 weeks |
| **A3 · People** | TIPNR people with disambiguation, Tamil names reviewed, person pages, People tab, name underline setting. | Selecting Acts 13:1 lists six people, each opening a page with the right disambiguation. | 2–3 weeks |
| **A4 · Interactive map** | PMTiles archive on Vercel Blob, MapLibre explore page, place and journey layers, journey pages. | Explore loads under budget on 4G; Paul's journeys draw with ordered stops. | 2 weeks |
| **A5 · Events and periods** | Theographic events and periods if licence and value justify it; period selector for regions. | Optional; decided after A4. | 2 weeks |
| **A6 · Tamil draft articles** | Externally produced Tamil drafts (§5) ingested from `data/entities/drafts/ta/`, validated, shown first in Tamil UI with English as fallback; suggestions enabled on every paragraph. | A place page in Tamil UI shows the Tamil article first; a stale draft falls back per paragraph. | 1 week after drafts arrive |

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

### A1b · Community review

| # | Task | Refs |
|---|---|---|
| A1b.1 | Migration: `profiles.role`, `entity_suggestions`, `entity_accepted`, `moderation_log`; RLS; `set_role`, `accept_suggestion`, `reject_suggestion` functions; rate limits | §5 |
| A1b.2 | RLS test suite covering reader, reviewer and moderator (closes M3 task 3.4) | design §5 |
| A1b.3 | Suggestion control on every Tamil name and article paragraph for signed-in users; CC BY consent line; `/me/contributions` | §5 |
| A1b.4 | `/mod` queue: open suggestions with current text, English source and an editable field pre-filled with the suggestion; accept publishes the edited text; reject with reason; per-entity grouping; direct-correction form for reviewers on any name or paragraph | §5 |
| A1b.5 | `/mod/roles` for moderators: appoint and remove reviewers | §5 |
| A1b.6 | Export workflow: every 12 hours and on dispatch, read accepted rows with the service key, write `data/entities/overrides/`, commit if changed; deploy follows | §5 |
| A1b.7 | "Publish now" in `/mod`: server route verifies the moderator's session and dispatches the export workflow through a fine-grained GitHub token | §5 |
| A1b.8 | Build applies overrides over drafts; badges for draft, community-corrected and owner-authored text | §3, §5 |

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
| A6.1 | Ingest `data/entities/drafts/ta/` with the validation rules in §5; per-paragraph fallback to English when stale | §5 |
| A6.2 | Full-text search over Tamil articles with `tamil_tsvector` | §3 |
| A6.3 | Glossary check: report draft paragraphs whose names differ from accepted Tamil forms | §5 |

## 5. Community review of Tamil content

The site keeps its rule that scripture and reference content are static. The database is a moderation workspace only: readers write suggestions into it, reviewers accept them there, and a scheduled export writes the accepted text back into the repository, which rebuilds and deploys. No page reads entity content from Postgres.

### Roles

| Role | Can |
|---|---|
| reader (default, signed in) | Suggest a correction to a Tamil name or an article paragraph; see own suggestions and their status under `/me/contributions` |
| reviewer | Everything above; open the `/mod` queue; accept a suggestion as written, **edit its text and accept the edited version**, or reject it with a reason; make a direct correction to any Tamil name or paragraph without a prior suggestion |
| moderator | Everything above; appoint and remove reviewers; trigger "Publish now" |

Editing before acceptance is the normal case, not the exception: the queue opens every suggestion in an editable field pre-filled with the suggested text, next to the current text and the English source. What is saved is the reviewer's final text. The suggestion keeps the reader's original wording, so the record shows what was proposed, what was published, and who changed it; the reader is still credited as the contributor under `/me/contributions`. A direct correction by a reviewer is stored as a suggestion authored and accepted by the same person in one step, so it appears in the same history and export.

The owner sets moderators directly in the database. Moderators cannot create other moderators. Role changes go through a `set_role(target_user, role)` function that checks the caller is a moderator and the target role is `reader` or `reviewer`, so the rule is enforced in Postgres, not in the UI.

### Tables

```sql
-- role on the existing profiles table
alter table profiles add column role text not null default 'reader'
  check (role in ('reader', 'reviewer', 'moderator'));

-- one row per suggestion; a paragraph is addressed by its stable id (§ below)
create table entity_suggestions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users,
  target text not null,                 -- 'name:IRVTAM:Damascus' or 'article:eastons/damascus#p3-4f2a9c1b'
  current_text text not null,           -- what the user saw, so a stale suggestion is detectable
  suggested_text text not null,
  reason text,
  status text not null default 'open' check (status in ('open', 'accepted', 'rejected')),
  created_at timestamptz not null default now(),
  decided_by uuid references auth.users,
  decided_at timestamptz,
  decision_note text,
  final_text text                       -- what the reviewer published; equals suggested_text when accepted unchanged
);

-- current accepted text per target; replaced on each acceptance, history in the log
create table entity_accepted (
  target text primary key,
  text text not null,
  suggestion_id uuid references entity_suggestions,
  accepted_by uuid not null references auth.users,
  accepted_at timestamptz not null default now(),
  exported_at timestamptz                 -- set by the export job
);

create table moderation_log (
  id bigserial primary key,
  actor uuid not null,
  action text not null,                 -- accept, reject, set_role, publish
  target text,
  detail jsonb,
  at timestamptz not null default now()
);
```

Policies: readers insert suggestions for themselves and select their own; reviewers and moderators select all suggestions and call `accept_suggestion(id, final_text)`, `reject_suggestion(id, note)` and `correct_directly(target, text)`, which are `security definer` functions that write `entity_suggestions.final_text`, `entity_accepted` and the log; nobody updates rows directly; anon has no access. `accept_suggestion` requires `final_text`, so the edited text is what gets published whether or not it differs from the reader's wording, and the log records both. A suggestion whose `current_text` no longer matches the live text is shown to the reviewer as stale. Limits: twenty open suggestions per user, and a suggested text must contain Tamil letters unless the target is a transliterated foreign word, checked in the insert function.

### Export

`.github/workflows/export-overrides.yml` runs every 12 hours (`0 */12 * * *`), on `workflow_dispatch` (the Run workflow button in GitHub), and on `repository_dispatch` from the site. It queries `entity_accepted` with the Supabase service key held as a GitHub secret, writes one file per entity under `data/entities/overrides/`, marks the rows `exported_at`, and commits as a bot if anything changed. The commit triggers the normal deploy, so the published site changes about ten minutes after an export.

```toml
# data/entities/overrides/place/damascus.toml
[names.IRVTAM]
forms = ["தமஸ்கு"]
accepted_at = 2026-10-03T14:12:00Z

[[paragraphs]]
id = "eastons/damascus#p3-4f2a9c1b"
text = "…"
accepted_at = 2026-10-03T14:20:00Z
```

Override files are the third input to the build, applied over drafts. They are CC BY, like the alignment table and our GeoJSON.

"Publish now" in `/mod` calls a server route on the site that verifies the caller's Supabase session and moderator role, then sends a `repository_dispatch` to GitHub using a fine-grained personal access token scoped to this repository's Actions, stored as a Vercel environment variable. The action is logged.

### Paragraph identity

Paragraph-level suggestions need ids that survive rebuilds. The build assigns each English article paragraph the id `{source}/{article}#p{n}-{hash8}`, where `hash8` is the first eight hex digits of the SHA-256 of the English paragraph text. A Tamil draft paragraph carries the same id as the English paragraph it translates, and an accepted correction is keyed by it. If the English source is re-segmented the hash changes and the correction detaches deliberately, which the build reports as an orphaned override for a reviewer to reattach.

### Tamil draft articles produced outside this repository

The AI translation runs outside the project. The build first emits the English source articles in a segmented form; the external process reads those and writes Tamil drafts back into `data/entities/drafts/ta/`. Both shapes are fixed here so the two sides can be developed independently.

Input the build provides, one file per English article:

```jsonc
// content/{build}/entities/articles/eastons/damascus.json
{
  "source": "eastons",
  "id": "eastons/damascus",
  "title": "Damascus",
  "lang": "en",
  "licence": "PD",
  "entities": ["place/damascus"],
  "paragraphs": [
    { "id": "eastons/damascus#p1-9c0e2a77", "text": "The most ancient of Oriental cities; the capital of Syria …" },
    { "id": "eastons/damascus#p2-1b6f03d4", "text": "…" }
  ]
}
```

plus `content/{build}/entities/articles/index.json` listing every article id, title, source hash and paragraph count, so the external process can find what is new or changed since its last run.

Output the external process must produce, one file per article, committed to the repository:

```jsonc
// data/entities/drafts/ta/eastons/damascus.json
{
  "id": "eastons/damascus",
  "lang": "ta",
  "source_hash": "sha256:…",                       // of the English article file it translated
  "generator": { "name": "claude", "model": "…", "prompt_version": "1", "generated_at": "2026-09-20" },
  "title": "தமஸ்கு",
  "paragraphs": [
    { "id": "eastons/damascus#p1-9c0e2a77", "text": "கிழக்கு நகரங்களில் மிகப் பழமையானது; சீரியாவின் தலைநகரம் …" },
    { "id": "eastons/damascus#p2-1b6f03d4", "text": "…" }
  ]
}
```

Rules the build enforces on drafts: same paragraph ids and count as the source, `source_hash` matches the current English file (otherwise the draft is flagged stale and the English paragraph is shown for the changed ones), Tamil script present, no HTML. Name occurrences inside a draft should use the accepted Tamil forms from `names-ta.toml`; the external process can read that file to build its glossary, and the build reports paragraphs whose entity names do not match the accepted forms so reviewers can fix them first. Drafts are released CC BY as translations of public-domain text; a draft of a CC BY-SA source (if Aquifer is ever approved) is stored under `drafts/ta-sa/` and keeps the ShareAlike licence.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Tamil name alignment is noisy for rare names and same-named people | Draft carries confidence; low-confidence rows default to `review = true`; ship places first where names are more regular |
| A source's actual file licence differs from the discussion | A0 verifies each file and records the hash; build refuses missing licences |
| Doctrinal mismatch in individual articles | Source-level gate plus per-article blocklist; owner reviews samples before a source is added |
| Map rendering slows the content build | Time budget in CI; move to a separate workflow keyed on entity data changes |
| Route count on Vercel | Entity pages are ISR; only indexes are prerendered |
| Reading performance regresses | Nothing new on the reading critical path; panel content loads on demand; existing Lighthouse and size budgets extended, not relaxed |
| Journey and region data of poor quality | Ship only reviewed files; hand-author the short list later |

## 7. Open items for the owner

1. Approve or reject Smith's and Aquifer after reading the A0.2 samples.
2. Choose which phases come before the outstanding M3–M5 items (settings sync, error tracking, custom domain verification). The RLS test suite (3.4) is now part of A1b.
3. Create the fine-grained GitHub token for "Publish now" and the Supabase service key secret for the export job when A1b starts; both are entered by the owner, never handled in chat.
