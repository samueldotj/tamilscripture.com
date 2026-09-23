# tamilscripture.com

**Tamil Bible Online** — a fast, mobile-first website for reading, searching and studying the Bible in Tamil, with English alongside, cross-references, personal notes and highlights, and community reading heat.

Live site (planned): **https://www.tamilscripture.com**

> Status: **live at https://www.tamilscripture.com** (first deploy 7 Sep 2026). All 1,189 chapters of IRVTAM, TCV, BSB, WEB and KJV are readable; the search table is loaded. M0 nearly complete; M1 features (picker, reference box, formats, PWA) in progress.

## Getting started

Prerequisites: Node 22+, pnpm, stable Rust (with the `wasm32-unknown-unknown` target for later milestones).

```bash
pnpm install
pnpm content:fixture   # parse the three-book fixture into apps/web/static/content
pnpm dev               # http://localhost:5173
```

`pnpm content` builds the full corpus (all five versions, about 6 seconds). `pnpm test` runs the Rust tests; `pnpm check` and `pnpm build` cover the web app.

For features that talk to Supabase, copy `apps/web/.env.example` to `apps/web/.env` and fill in the anon key from the Supabase dashboard.

## Deploying

Every push to `main` runs [deploy.yml](.github/workflows/deploy.yml): build content, apply migrations with `supabase db push`, load the search table, then build the site and upload it prebuilt to Vercel. The workflow needs these repository secrets, entered once by the owner:

| Secret | Where to get it |
|---|---|
| `SUPABASE_ACCESS_TOKEN` | Supabase account → Access Tokens |
| `SUPABASE_DB_PASSWORD` | Set when the project was created; resettable under Project Settings → Database |
| `SUPABASE_DB_URL` | Project Settings → Database → Connection string, **Session pooler** (port 5432; GitHub runners have no IPv6 for the direct host) |
| `VERCEL_TOKEN` | Vercel account → Tokens |
| `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` | From `.vercel/project.json` after running `vercel link` once locally, or the project settings page |

The Vercel project should have its Git integration's production deploys disabled (or an "Ignored Build Step" that always skips), since GitHub Actions performs the deploy.

## Documents

| Document | What it covers |
|---|---|
| [docs/requirements.md](docs/requirements.md) | Product requirements: reading, navigation, URLs, search, cross-references, display formats, dual versions, accounts, notes, highlights, community stats, performance budgets, delivery phases, open questions |
| [docs/design.md](docs/design.md) | Software architecture: system context, content pipeline, SvelteKit rendering modes, search design, auth and row-level security, aggregates, offline, performance mechanisms, decision records, repository layout |

## What it will do

- Read the Bible in Tamil (IRVTAM, TCV) with an English version (BSB, WEB or KJV) side by side.
- Jump to any passage by typing `John 3:16`, `Jn 3`, `யோவான் 3:16` or `யோவா 3`.
- Search words with Tamil-aware fuzzy matching; exact phrases in quotes.
- Every verse and range has a stable, human-readable link, e.g. `https://www.tamilscripture.com/irvtam/john/3/16`.
- Cross-references, section headings and introductions, each switchable on or off.
- Reader, Standard and Study Bible display formats (Study Bible: one verse per line with the chapter's places, persons and map).
- Sign in with Google or Facebook to keep history, notes and colour highlights.
- See which verses the community highlights most, as counts and heatmaps.

## Planned stack

| Layer | Choice |
|---|---|
| Web app | SvelteKit 2, TypeScript, PWA |
| Hosting | Vercel (edge CDN, ISR, serverless in Mumbai) |
| Data and auth | Supabase (Postgres 16, Auth, row-level security) |
| Text pipeline and parsers | Rust workspace, compiled to native and WebAssembly |
| Bible sources | USFM from eBible.org (IRVTAM, TCV: CC BY-SA 4.0; BSB, WEB, KJV: public domain), OpenBible.info cross-references (CC BY) |

## Planned repository layout

```
apps/web/        SvelteKit application
crates/          Rust: usfm-ingest, bible-ref, tamil-norm, wasm wrapper
packages/        npm package built from the wasm crate
data/            USFM sources, licences, books.toml, test fixtures
supabase/        migrations, policies, seed
scripts/         content build, font subsetting, search load, ISR warm-up
docs/            requirements, design, decision records
```

See [docs/design.md](docs/design.md#14-repository-layout) for the full tree and conventions.

## Milestones

Milestones follow the delivery phases in [docs/requirements.md](docs/requirements.md#15-delivery-phases). Each milestone is usable on its own. Requirement IDs (`R-x.y`) and decision records (`ADR-n`) link tasks back to the documents.

| Milestone | Goal | Requirements | Exit test | Status |
|---|---|---|---|---|
| **M0 · Foundations** | Repository, pipeline and deploy path exist end to end. | R-3.1, R-3.5 | A chapter is visible on the production URL, built by CI from USFM. | Done except 0.11, 0.12 spikes and books.toml review |
| **M1 · Read** | Anyone can read IRVTAM, TCV and an English version of their choice on a phone, fast, at a shareable URL. | R-3.1–3.3, 3.5, R-1.1–1.5, 1.7–1.8, 1.10, 1.12–1.14, R-8.1, 8.3 | Every chapter loads under budget on the 4G profile. A Tamil user can reach any verse by typing its Tamil abbreviation. | Shipped 7 Sep 2026 except 1.17 font choice, 1.18 self-hosted subset, 1.19 i18n module, 1.23 CI guards, 1.24 a11y pass, 1.25 Sentry |
| **M2 · Study** | Word search, cross-references, the Study Bible format (then called Cross-reference) and dual version display. | R-5.1–5.6, 5.9, R-7.1–7.4, R-8.2, R-9.1–9.5, R-3.4 | Search p75 under one second on real queries from the log. | Shipped 7 Sep 2026; 2.14 (log review) ongoing |
| **M3 · Remember** | Sign-in with history, notes and highlights that sync across devices. | R-10.1–10.2, 10.4–10.5, 10.7–10.10, 10.12–10.14, R-1.9 | RLS test suite passes; one user's data is invisible to another through the API. | Code shipped 7 Sep 2026; blocked on owner's Supabase Auth URL setup (3.1); 3.4, 3.8, 3.9 open |
| **M4 · Community** | Highlight counts and heatmaps, anonymous and opt-out. | R-2.1–2.4 | Aggregates refresh hourly and never show counts under the threshold. | Code shipped 7 Sep 2026; 4.7 alerting open |
| **M5 · Later** | Could-priority items, scheduled by demand. | R-1.6, 1.11, 5.7–5.8, 7.5, 10.3, 10.6, 10.11, 10.15, 2.5, 3.6 | | Not started |
| **M6 · Places and maps** | Every verse knows its places: Tamil and English place names, verse links, a static map in the reader, place and journey pages, and an interactive atlas. Design in [docs/feature_maps.md](docs/feature_maps.md). | R-11.1–11.8, R-14.1–14.6 | Acts 13 shows its places on a map in the panel; "தமஸ்கு" in the search box opens Damascus; Explore loads under budget on 4G. | Built 12 Sep 2026 on branch `m6-places-maps`; regions and the period selector (6.16) deferred |
| **M7 · Dictionary, people and community review** | Reformed dictionary articles and people linked to verses, Tamil drafts from outside the repository, and crowdsourced paragraph-level review with roles and export-only publishing. Design in [docs/feature_dictionary.md](docs/feature_dictionary.md). | R-12.1–12.7, R-13.1–13.6, R-15.1–15.7 | A reviewer edits and accepts a suggested Tamil paragraph; after "Publish now" the text is on the site with its badge; the RLS suite passes for every role. | Built 13 Sep 2026 on `m7-dictionary-people`; Smith's and Aquifer approved 13 Sep 2026; the scheduled export ran for the first time 18 Sep 2026, so `SUPABASE_SERVICE_KEY` works; owner items open (first moderator, Tamil drafts, `GITHUB_DISPATCH_TOKEN` for "Publish now"); ISBE deferred |
| **M8 · Site analytics** | First-party, cookie-free visit counts for moderators: page views, visitors, unique views, signed-in users, verse clicks, country and city, device and resolution, in `/mod/traffic`. Design in [docs/feature_analytics.md](docs/feature_analytics.md). | R-16.1–16.7 | A moderator opens Traffic and sees yesterday's views by page and country; no stored row identifies a reader. | A1–A6 built 18 Sep 2026 |
| **M9 · Concordance** | Every Hebrew and Greek word with its Strong's number: a concordance page per number with all its verses, loaded as you scroll; the original words of any verse in the reader; search by number, word, transliteration or meaning; Tamil meanings through the review queue. Design in [docs/feature_concordance.md](docs/feature_concordance.md). | — | Tapping ἠγάπησεν in John 3:16 opens G0025 with all 110 verses; "agape", "G26" and "அன்பு" find G0026. | C1–C5 built 20 Sep 2026; Tamil gloss drafts open |
| **M10 · Verse presentations** | Slides of verse references with Markdown notes for sermons and Bible studies: an editor, a presenter in its own tab with keyboard control and full screen, and a permanent shareable link. Verses are stored as references, so the translation can be changed at any time. Design in [docs/feature_presentation.md](docs/feature_presentation.md). | R-17.1–17.7 | A sermon of eight slides opens from its link on another device; Space steps through it full screen; switching to TCV shows the same verses in TCV. | P1–P5 built 21–22 Sep 2026 |

### M0 · Foundations

| # | Task | Refs | Done |
|---|---|---|---|
| 0.1 | Set up the monorepo: pnpm workspace, Cargo workspace, `rust-toolchain.toml`, root scripts, `.gitignore` for `target/` and `static/content` | design §14 | ☑ |
| 0.2 | Decide the USFM parsing approach: own marker-level parser in `usfm-ingest` over the eBible dialect | design §14 | ☑ |
| 0.3 | Download IRVTAM, TCV, BSB, WEB, KJV from eBible.org and OpenBible cross-references; record `LICENSE` + `SOURCE.md` for each | R-3.5, open questions 1–2 | ☑ |
| 0.4 | Create `data/books.toml` with English and Tamil names, slugs and abbreviations for all 66 books (drafted from the USFM headers by `scripts/draft-books-toml.py`; reviewed by owner 7 Sep 2026) | R-1.13 | ☑ |
| 0.5 | Create the three-book fixture version under `data/fixtures/` (Ruth, Jonah, Philemon in IRVTAM and BSB) | design §14 | ☑ |
| 0.6 | `usfm-ingest` v0: parse all five versions with strict validation, emit chapter JSON, intro JSON, cross-ref JSON, `manifest.json` and search CSV; determinism check in CI | R-3.1 | ☑ |
| 0.7 | Scaffold the SvelteKit app with `adapter-vercel`; chapter pages rendered from JSON via ISR (see ADR-1 for why not prerender) with breadcrumbs, prev/next, footnotes and attribution | ADR-1 | ☑ |
| 0.8 | One hosted Supabase project in Mumbai (`zytgmnqmrvgspjdokajp`); first migration (`pg_trgm`, `tamil_norm` placeholder, `verse_search`) written; applied by the deploy workflow once secrets exist. Second project deferred to M3. | design §11 | ◧ |
| 0.9 | GitHub Actions: `ci.yml` (fmt, clippy, cargo test, full-corpus strict build, determinism diff, svelte-check, web build) ☑; `preview.yml` (Vercel preview against the development project) ☐ | design §11 | ◧ |
| 0.10 | Point `www.tamilscripture.com` at Vercel; redirect apex to www | ADR-7 | ☑ |
| 0.11 | Spike: `bible-ref` compiled to WebAssembly running on the Vercel edge runtime; measure bundle size and cold start. *Outcome:* the wasm is 31 kB gzipped and the redirector runs in the Node runtime (bom1) via `read()` from `$app/server`; edge deferred because it adds nothing measurable for a redirect | design §13 risks | ☑ |
| 0.12 | Spike: PGroonga versus `pg_trgm` on the fixture corpus for Tamil fuzzy search | design §6, ADR-2 | ☐ |

### M1 · Read

| # | Task | Refs | Done |
|---|---|---|---|
| 1.1 | `usfm-ingest`: full paratext support (introductions, headings, poetry, paragraphs, footnotes, `\x` markers) | R-3.2 | ☑ |
| 1.2 | `usfm-ingest`: verse bridges and split verses, `bridges` map in chapter JSON | R-3.3 | ☑ |
| 1.3 | All five versions ingested (IRVTAM, TCV, BSB, WEB, KJV) ☑; English version selector, BSB default ☑; unit tests in `usfm.rs` and the CI determinism diff cover the parser, dedicated golden-file fixtures ☐ | R-3.1 | ◧ |
| 1.4 | `bible-ref` crate: grammar, English and Tamil book matching, Tamil numerals, canonical URL builder; fixture suite (190 cases, grow to 500) | R-1.2, R-1.13 | ☑ |
| 1.5 | `packages/bible-wasm`: wasm-pack build (31 kB gzipped), lazy loader in `src/lib/ref` | ADR-3 | ☑ |
| 1.6 | Chapter route rendered from JSON via ISR; `Chapter`, `Verse` components | R-1.1, ADR-1 | ☑ |
| 1.7 | Verse and range routes with ISR, selected-verse highlight, per-verse title, description, Open Graph tags | R-1.12, R-1.15, ADR-1 | ☑ |
| 1.8 | Shorthand (`/jn3.16`) and Tamil-path (`/யோவான்/3/16`) redirectors; Node runtime rather than edge (see 0.11) | R-1.12, ADR-7 | ☑ |
| 1.9 | Book page with chapter grid and translation introduction; in-reader version/book/chapter picker reflecting the current position | R-1.1 | ☑ |
| 1.10 | Reference box in the header wired to `bible-wasm`, with book suggestions and a not-recognised hint | R-1.2 | ☑ |
| 1.11 | History handling: SvelteKit client navigation per passage (one history entry each), settings changes never navigate, scroll restored on back | R-1.3 | ☑ |
| 1.12 | Breadcrumbs with JSON-LD `BreadcrumbList` | R-1.4 | ☑ |
| 1.13 | Previous and next chapter controls, swipe on touch, ← → keys, hover prefetch | R-1.5 | ☑ |
| 1.14 | Verse selection (tap verse numbers, or drag across the text / long-press on phones) and action bar: copy text with reference and link, share via Web Share or link copy; ‡ and ✎ marks stay out of copied text | R-1.7 | ☑ |
| 1.15 | Reader, Standard and Cross-reference formats as CSS classes on `<html>`; inline pre-paint stamp in `app.html` | R-8.1, R-8.3, ADR-6 | ☑ |
| 1.16 | Paratext toggles (introductions, headings, footnotes, cross-ref markers) persisted in local storage; default version cookie for the shorthand redirector | R-1.8, R-1.14 | ☑ |
| 1.17 | Reader settings: text size (5 steps), theme, UI language, Tamil typeface (Mukta Malar, Noto Sans, Noto Serif, system) ☑; low-end Android check ☐ | R-1.10, open question 6 | ◧ |
| 1.18 | Self-hosted subset fonts via `scripts/subset-fonts.py` (Tamil faces ~40 kB each, `unicode-range`, `font-display: optional`, preload, fallback metrics); Google Fonts removed | design §10 | ☑ |
| 1.19 | Tamil and English interface strings throughout, switchable in the header and the phone menu ☑; first visit always starts in Tamil rather than following the browser language ☐ | requirements §12 | ◧ |
| 1.20 | PWA shell: web manifest with icons, service worker (shell precache, content JSON cache-first, last 20 reader pages offline) | requirements §12, design §9 | ☑ |
| 1.21 | About page (purpose, who is behind the site, privacy) and a separate `/licences` page with sources and attribution; footer notice on reading pages; site footer links | R-3.5 | ☑ |
| 1.22 | Sitemap index plus one sitemap per version and one for entities, plain-text `/sitemap.txt` with all 23,932 URLs, `robots.txt`, `rel="canonical"`, Tamil page titles ☑; since 22 Sep 2026 one canonical page per passage (the Tamil version's, ADR-15) with `hreflang`, bilingual titles, the verse as description and shown first on verse pages, sitemaps of the canonical version only ☑; a default Open Graph image, WebSite/Person/Place JSON-LD, book pages canonical to Tamil, a custom error page ☑ | R-1.12, requirements §12 | ☑ |
| 1.23 | CI guards: Lighthouse CI (a11y ≥ 0.95 and CLS < 0.05 as errors, performance ≥ 0.9 as warning) ☑, `size-limit` (wasm, font) and `scripts/size-check.mjs` (reader route ≤ 120 kB counting every chunk a chapter page loads up front, since 23 Sep 2026; all chunks ≤ 260 kB summed over every page; map engine; /mod) ☑; Playwright text-visible-under-500 ms ☐ | design §10 | ◧ |
| 1.24 | Accessibility pass: `lang` attributes, focus states, 44 px targets, WCAG 2.2 AA contrast | requirements §12 | ☐ |
| 1.25 | Production deploy on `www.tamilscripture.com` ☑; Vercel Analytics ☑; Sentry ☐ (needs DSN); uptime probe ☐ | design §11 | ◧ |
| 1.26 | Phone header, design 10A: the three header rows become one 56px auto-hiding bar (back, chapter pill, search); book/chapter/version menu with language, sign-in and settings in its footer; reader thumb bar with floating text size and a progress hairline while reading | design 10A, R-1.10 | ☑ |
| 1.27 | Single-verse page `/irvtam/john/3.16` (and `3.16-18`; `3_16` redirects): the passage alone in large type, Tamil and English, with a link to the whole chapter; offered from the action bar's Share menu as "Large text"; listed in `/sitemap-verses.xml` | R-1.16 | ☑ |

### M2 · Study

| # | Task | Refs | Done |
|---|---|---|---|
| 2.1 | `tamil-norm` crate: near-letter folding, suffix stripping; SQL generator with explicit Tamil code points; CI diff keeps the SQL current (a live parity test needs the M3 dev project) | R-5.4 | ☑ |
| 2.2 | Migrations: `verse_search` generated columns from our own Tamil tokeniser (`tamil_tsvector`), GIN and trigram indexes | design §6 | ☑ |
| 2.3 | `usfm-ingest` emits `search/{VERSION}.csv`; `scripts/load-search.sh` upserts per version in the deploy workflow | design §3 | ☑ |
| 2.4 | `search_verses()`: exact phrase (trigram-prefiltered), full text with Tamil prefix matching, word-similarity fallback, ranking, paging, blank-query guard | R-5.3, R-5.4 | ☑ |
| 2.5 | `/api/search` with 60 s CDN cache; client-side match marking | R-5.5 | ☑ |
| 2.6 | Header box classifies reference vs words in the browser; `/search` page grouped by book with scope (version, language, all) and paging | R-5.1, R-5.2, R-5.5 | ☑ |
| 2.7 | `search_log` + `log_search()`, `common_searches` view refreshed nightly by pg_cron, `/api/common-searches`, empty-state chips | R-5.6, R-5.9 | ☑ |
| 2.8 | `usfm-ingest` emits OpenBible cross-references per chapter (USFM `\x` markers are kept as verse notes) | R-7.3 | ☑ |
| 2.9 | Cross-reference markers (‡), panel with target text in the current version, links push history; toggle off stops the fetch | R-7.1, R-7.2, R-7.4 | ☑ |
| 2.10 | Cross-reference display format: one verse per line with inline reference list | R-8.1 | ☑ |
| 2.11 | Format switch is a class change, so scroll position is kept | R-8.2 | ☑ |
| 2.12 | Versification: pipeline validates chapter counts across versions (all 66 books agree); dual view aligns rows by verse number and shows a dash for a verse missing on one side | R-3.4, R-9.4 | ☑ |
| 2.13 | Dual version route (`/irvtam+bsb/...`) with ISR; verse-aligned rows side by side, stacked per verse on phones; shared selection; compare control in the picker | R-9.1–9.5 | ☑ |
| 2.14 | Weekly search-log review during the first month; tune folding tables | design §13 risks | ☐ |

### M3 · Remember

| # | Task | Refs | Done |
|---|---|---|---|
| 3.1 | Supabase Auth: magic link ☑, Google button ☑, Google provider credentials and redirect URLs entered by the owner ☑ (18 Sep 2026); Google app-name and logo verification with Google still to be submitted ☐; Facebook deferred (open question 4) | R-10.1, R-10.2 | ◧ |
| 3.2 | Client-side PKCE: `/auth/callback` exchanges the code in the browser; public pages never read the session on the server (ADR-9); supabase-js loads lazily only for signed-in visitors | design §7 | ☑ |
| 3.3 | Migration `20260907200000_personal`: `profiles` (auto-created on signup), `highlights`, `notes`, `history` with RLS, `record_visit`, `export_my_data`, `delete_my_account` | ADR-5, design §7 | ☑ |
| 3.4 | RLS test suite in CI: pgTAP against the local Supabase stack (`supabase/tests/`), no secrets needed; covers personal tables indirectly through the community-review suite (7.8) | design §7 | ☑ |
| 3.5 | Highlights: four colours in the action bar, contiguous runs stored as rows, remove or recolour, rendered in every format and both themes, `/me/highlights` grouped by book with colour filter | R-10.12, R-10.13 | ☑ |
| 3.6 | Notes: bottom sheet with autosave and delete, ✎ markers on verses, `/me/notes` with full-text search | R-10.8, R-10.9, R-10.10 | ☑ |
| 3.7 | History: `record_visit` collapses repeats within 10 minutes, `/me/history` grouped by day with book filter, pause and clear | R-10.5, R-10.7 | ☑ |
| 3.8 | Settings sync to `profiles.settings` for signed-in users | R-1.9 | ☐ |
| 3.9 | Offline outbox in IndexedDB with idempotent upserts; cross-device sync within 5 s | R-10.14, design §9 | ☐ |
| 3.10 | `/me/account`: export as JSON (copyable), delete account with typed confirmation, opt-out of aggregates | R-10.4, R-2.4 | ☑ |
| 3.11 | Privacy text on the About page ☑; graceful degradation message when Supabase is unreachable ☐ | requirements §12 | ◧ |

### M4 · Community

| # | Task | Refs | Done |
|---|---|---|---|
| 4.1 | `share_aggregates` flag on `profiles` with a toggle on the Account page | R-2.4 | ☑ |
| 4.2 | `verse_highlight_counts` materialised view: distinct users, join on opt-in, `having count ≥ 3`; hourly `pg_cron` concurrent refresh | R-2.1, R-2.4, ADR-8 | ☑ |
| 4.3 | `/api/heat/{book}.json` and `/api/heat/all.json` with one-hour CDN cache | design §8 | ☑ |
| 4.4 | Counts shown in the verse-number tooltip and in the action bar for the selection (no inline text, so no layout shift) | R-2.1 | ☑ |
| 4.5 | `/heatmap` (one cell per chapter) and `/heatmap/{book}` (one cell per verse) with quantile buckets; tap opens the passage | R-2.2 | ☑ |
| 4.6 | Heat overlay in the reader as a settings toggle, off by default | R-2.3 | ☑ |
| 4.7 | Alert if view refresh exceeds 30 s; document the trigger-table upgrade path | design §13 risks | ☐ |

### M5 · Later

| # | Task | Refs | Done |
|---|---|---|---|
| 5.1 | Keyboard shortcuts (← → chapters, / focuses the reference box, Esc clears) | R-1.6 | ☑ |
| 5.2 | Light, dark and system theme | R-1.11 | ☑ |
| 5.3 | Autocomplete for book names in both scripts (header box, since 1.10) and recent searches: the last 8 searches and references kept in this browser, the latest six on focusing the empty box, matches while typing, a Clear button | R-5.7 | ☑ |
| 5.4 | Restrict search to testament, book or chapter range: "Within" picker and chapter fields on `/search` (`in=ot\|nt\|{book}`, `ch=3-5`), "Search only here" on each book of the results; `search_verses` takes book and chapter bounds (pgTAP `search_filters`) | R-5.8 | ☑ |
| 5.5 | Romanised Tamil search input: with a Tamil primary version, a query in Latin letters that finds nothing as typed ("anbu") is searched as Tamil (அன்பு) with a "search as typed" link; one that does ("god") keeps its results and offers the Tamil reading (`lib/search/romanised.ts`) | R-5.4 stretch | ☑ |
| 5.6 | Verse preview on hover: resting the mouse on any verse link for half a second shows the verse underneath it (cross-references, entity pages, dictionary articles) | R-7.5 | ☑ |
| 5.7 | Import anonymous highlights and notes at first sign-in | R-10.3 | ☐ |
| 5.8 | "Continue reading" shortcut on the home page: the passage last opened in this browser (any reader), else the newest history entry of a signed-in reader | R-10.6 | ☑ |
| 5.9 | Markdown in notes (bold, italics, lists, links, verse references) on `/me/notes`, with a Preview in the note sheet; the in-house parser used by presentations | R-10.11 | ☑ |
| 5.10 | Sub-verse highlights stored as per-version offsets | R-10.15 | ☐ |
| 5.11 | "Most highlighted this month" list on the home page: the top ten verses from `verse_highlight_month` (last 30 days, opted-in readers, three or more, refreshed hourly; pgTAP `highlights_this_month`), with their text in the reader's version; hidden until a verse qualifies | R-2.5 | ☑ |
| 5.12 | Add a version by config only; first additional Indian language | R-3.6 | ☐ |

### M6 · Places and maps

Design: [docs/feature_maps.md](docs/feature_maps.md). Rough effort: five to six weeks excluding review time.

| # | Task | Refs | Done |
|---|---|---|---|
| 6.1 | Download OpenBible Geocoding and TIPNR; record `LICENSE`, `SOURCE.md` with hashes under `data/entities/`; build fails without a licence file | maps §2 | ☑ |
| 6.2 | Requirement IDs R-11.x (places) and R-14.x (maps) in `docs/requirements.md`; design ADRs: content-build entities, ISR entity pages, PMTiles on Vercel Blob | maps §1 | ☑ |
| 6.3 | `crates/entity-ingest`: parse OpenBible Geocoding and TIPNR places, reconcile identities, emit `entities/place/*.json` and per-chapter `mentions/` | maps §3 | ☑ |
| 6.4 | `--draft-names` co-occurrence aligner over IRVTAM and TCV writing `data/entities/names-ta.toml` with confidence; model only breaks ties; build fails on forms absent from the text | maps §3 | ☑ |
| 6.5 | Validation: coordinates or `unlocated`, every mention resolves, determinism diff in CI | maps §3 | ☑ |
| 6.6 | Static map renderer in the content build: Natural Earth outline, labelled places per chapter, place and journey, as theme-aware inline SVG with labels in both scripts (SVG replaces the planned WebP; see feature_maps.md) | maps §4 | ☑ |
| 6.7 | `/place/{slug}` ISR page: names, map, verses by book, attribution; Tamil path redirects | maps §5, ADR-1, ADR-7 | ☑ |
| 6.8 | Places in the reader: shown only in the Study Bible format behind the Places and Maps toggles (owner decision 13 Sep 2026; the Reader and Standard formats stay text and related verses only) | R-8.4, R-11.4 | ☑ |
| 6.9 | `entity_search` table and loader; `/api/entities/search`; entity cards on the search page; entity rows in reference box suggestions | maps §3, ADR-2 | ☑ |
| 6.10 | Sitemap for places; About page source table | maps §3 | ☑ |
| 6.11 | Base map: Natural Earth land, lakes and rivers clipped to the biblical world (`scripts/build-basemap.py`), served as static GeoJSON; PMTiles deferred (design ADR-11) | maps §4 | ☑ |
| 6.12 | MapLibre style: land, water, rivers, our labels; light and dark from the theme tokens | maps §4 | ☑ |
| 6.13 | `/atlas/explore` client-only route, code-split, layer toggles; own size-limit and Lighthouse entries | maps §4, §7 | ☑ |
| 6.14 | Journeys: 31 hand-authored with Tamil names (patriarchs, Exodus, conquest, judges, kings, prophets, exile and return, life of Jesus, Acts); 30 drawn on UBS Project MARBLE routes (CC BY-SA 4.0) instead of straight legs, 13 Sep 2026; `/atlas` and `/atlas/{journey}` pages with static maps and ordered stops ☑; regions deferred (no open data at usable quality) | maps §4, §5 | ◧ |
| 6.15 | "Explore map" links from the panel, place pages and journey pages | maps §6 | ☑ |
| 6.16 | Period selector on the explore map once two or more region periods exist | maps §4 | ☐ |

### M7 · Dictionary, people and community review

Design: [docs/feature_dictionary.md](docs/feature_dictionary.md). Rough effort: six to eight weeks excluding review time; Tamil drafts arrive from outside the repository.

| # | Task | Refs | Done |
|---|---|---|---|
| 7.1 | Dictionary sources with licence files: Easton (NEUU dataset) ☑, Smith's (NEUU dataset) ☑, Aquifer Open Bible Dictionary (CC BY-SA, own directory) ☑; Smith's and Aquifer approved by the owner 13 Sep 2026; ISBE deferred (scans only) | dictionary §2 | ☑ |
| 7.2 | Requirement IDs R-12.x (dictionary), R-13.x (people), R-15.x (community review) in `docs/requirements.md`; design ADRs: static drafts plus exported overrides, moderation in Postgres | dictionary §1, ADR-13, ADR-14 | ☑ |
| 7.3 | Parse Easton, Smith's and Aquifer into `articles/{source}/{id}.json` with stable paragraph ids and attribution; link to entities by ACAI hints or title; `blocklist.toml` honoured; `articles/index.json` (13,147 articles) | dictionary §3 | ☑ |
| 7.4 | Ingest `data/entities/drafts/ta/` with the validation rules; per-paragraph fallback to English when stale; glossary check against accepted names (`community.rs`; drafts themselves await the owner) | dictionary §5 | ☑ |
| 7.5 | `/dictionary` index and `/dictionary/{source}/{id}` pages with language badge and licence; articles searchable by title (the Dictionary tab in the reader was withdrawn, R-12.6) | dictionary §7, §8 | ☑ |
| 7.6 | TIPNR people: identity, disambiguation, relations, mentions; Tamil name drafts; `/person/{slug}` pages; people in search and reference box (the People tab was withdrawn, R-13.4) | dictionary §4 | ☑ |
| 7.7 | Migration: `profiles.role`, `entity_suggestions`, `entity_accepted`, `moderation_log`; RLS; `set_role`, `accept_suggestion`, `reject_suggestion`, `correct_directly`; rate limits | dictionary §6 | ☑ |
| 7.8 | RLS test suite covering anon, reader, reviewer and moderator: `supabase/tests/community_review.test.sql` (pgTAP), CI job `rls` (closes 3.4) | dictionary §6 | ☑ |
| 7.9 | Suggestion control on every Tamil name and article paragraph for signed-in users; CC BY consent line; `/me/contributions` | dictionary §6, §7 | ☑ |
| 7.10 | `/mod` queue: current text, English source and an editable field pre-filled with the suggestion; accept publishes the edited text; reject with reason; per-entity grouping; stale flag; direct-correction form; `/mod/history` | dictionary §6 | ☑ |
| 7.11 | `/mod/roles` for moderators (appoint by email, remove) | dictionary §6 | ☑ |
| 7.12 | Export workflow every 12 hours and on dispatch: read accepted rows with the service key, write `data/entities/overrides/`, commit if changed, start the deploy (`export-overrides.yml`, `scripts/export-overrides.mjs`); needs the `SUPABASE_SERVICE_KEY` secret from the owner | dictionary §6 | ◧ |
| 7.13 | "Publish now": `/api/mod/publish` verifies the moderator session and dispatches the export workflow through a fine-grained GitHub token; needs `GITHUB_DISPATCH_TOKEN` on Vercel from the owner | dictionary §6 | ◧ |
| 7.14 | Build applies overrides over drafts; provenance badges for draft, community-corrected and owner-authored text | dictionary §6 | ☑ |
| 7.15 | "Dictionary words" setting (design 7A), off by default, pre-paint class: people and places named in the text carry a dotted underline in Tamil and English versions; a tap opens the name's card (original form, Strong's number, verse count, description, article and full-entry links) under a new அகராதி tab in the context panel, or as a half-sheet on phones. The chapter mentions carry the Tamil forms that occur in each chapter | dictionary §4, design 7A | ☑ |
| 7.18 | Concordance for name words: every Strong's number shown on the site (name cards, study panel, person pages) links to `/strongs/{number}`, listing every verse the word occurs in, grouped by book, with the text in the reader's version, 50 verses at a time. Built from TIPNR's per-form verse lists (4,994 numbers); `/api/verses` serves the text | design 7A | ☑ (superseded by M9) |
| 7.16 | Full-text search over Tamil articles with `tamil_tsvector` (after the first Tamil drafts exist) | dictionary §8 | ☐ |
| 7.17 | Optional: Theographic events and periods in their own directory if licence and value justify it; events on entity pages | dictionary §2 | ☐ |

### M8 · Site analytics

Design: [docs/feature_analytics.md](docs/feature_analytics.md).

| # | Task | Refs | Done |
|---|---|---|---|
| 8.1 | A1: migration `20260918000000_site_analytics.sql` (`analytics_salt`, `analytics_events`, `track()`, salt and 90-day retention jobs) | R-16.1–16.4 | ☑ |
| 8.2 | A1: `/api/t` collector with bot filter, Vercel geo headers and user-agent parsing; page-view beacon after each navigation and a verse-click event; GPC/DNT opt-out; About page privacy text | R-16.1–16.3, R-16.7 | ☑ |
| 8.3 | A2: `analytics_report(from, to)` (staff only) and `/mod/traffic` with range switch, tiles, daily chart and ranked tables | R-16.4, R-16.5 | ☑ |
| 8.4 | A2: pgTAP suite `site_analytics.test.sql` (anon records, only staff read, nothing identifying stored) | R-16.2, R-16.4 | ☑ |
| 8.5 | A3: daily rollups kept two years; report reads rollups beyond 90 days | R-16.6 | ☑ |
| 8.6 | A4: reading insight — books and chapters read, reading heatmap by book, most-tapped verses per book, search terms, atlas and dictionary usage | feature_analytics §6 | ☑ |
| 8.7 | A5: live "now" panel, CSV export, week-over-week deltas | feature_analytics §6 | ☑ |
| 8.8 | A6: edge rate limit, spike note, bot list review, collector load test | feature_analytics §5 | ☑ |

### M9 · Concordance

Design: [docs/feature_concordance.md](docs/feature_concordance.md). Sources: STEPBible TAHOT, TAGNT, TBESH, TBESG (CC BY 4.0), fetched at build time and never committed.

| # | Task | Refs | Done |
|---|---|---|---|
| 9.1 | C1: `scripts/fetch-stepbible.mjs` (pinned commits, SHA-256, CI cache); TIPNR moved to the same fetch and untracked; `stepbible.rs` parses every tagged word, maps NRSV numbering onto ours and fails on an unmapped verse; one file per Strong's number (17,125) and the original words of every chapter | concordance §5, §8 | ☑ |
| 9.2 | C2: `/strongs/{n}` with lemma, transliteration, meaning, definition, names, book strip, every verse with its original form; text 50 verses at a time as you scroll; words in over 1,000 verses open on one book; `?b=` keeps a book | concordance §6–7 | ☑ |
| 9.3 | C3: மூலம் tab (desktop) and sheet (phones) listing the selected verses' Hebrew or Greek words with Strong's links; its own chunk, loaded on first use with the chapter's words | concordance §6 | ☑ |
| 9.4 | C4: Hebrew & Greek filter in `/dictionary`; search by number, word, transliteration or meaning on the server; results in `/search`; a number typed in the header box opens its page | concordance §7 | ☑ |
| 9.5 | C5: Tamil meaning per number, from `drafts/lexicon-ta.toml` or an accepted `gloss:` correction (export writes `overrides/lexicon.toml`), shown with its badge and a suggest control; searchable | concordance §10 | ☑ |
| 9.6 | Tamil gloss drafts for the lexicon (owner) | concordance §12 | ☐ |

### M10 · Verse presentations

Design: [docs/feature_presentation.md](docs/feature_presentation.md), from design 11A.

| # | Task | Refs | Done |
|---|---|---|---|
| 10.1 | P1: `presentations` table with `check_slides()` (references only, bounded), owner-only RLS, `presentation_by_slug()` for shared links without the owner's id, export includes presentations; pgTAP `presentations.test.sql` | presentation §2 | ☑ |
| 10.2 | P2: `/me/presentations` list; `/present/{slug}/edit` with slide rail (drag to reorder), 16:9 preview, Markdown notes (toolbar, Write / Split / Preview), verses with a version each, picker by reference, chapter, word, cross-references, recent and highlights; autosave; share with visibility | presentation §4 | ☑ |
| 10.3 | P3: `/present/{slug}` server-rendered for link previews, keys (Space, arrows, F, N, ?, Esc), full screen, controls fade after 3 s, version switch (`?v=`), text shrinks to fit, follow-along channel between editor and presenter tabs | presentation §4 | ☑ |
| 10.4 | Markdown renderer `src/lib/md` building elements from a tree (no HTML strings); verse references in notes link with the hover preview | presentation §1 | ☑ |
| 10.5 | P4: one-line header on every slide; a slide without verses is a title page with centred Markdown; references and verse numbers on a slide link to the reader; closing slide with thumbs up / down (`presentation_vote()`, owner cannot edit the counters, private takes none) and share; pgTAP extended to 25 checks | presentation §4 | ☑ |
| 10.6 | P5: statistics for the owner at `/present/{slug}/stats` (views, visitors, votes, last opened, 30-day chart, countries, devices) from the existing analytics through `presentation_stats()`; a line of numbers on the list; site JavaScript budget raised to 260 kB | presentation §4 | ☑ |
| 10.7 | "Add to presentation" from the reader's verse action bar; dual-version slides; printed handout | presentation §6 | ☐ |

## Licences

- **Code** in this repository is released under the [MIT License](LICENSE).
- **Bible texts** are not part of this licence. Each version under `data/versions/` carries its own `LICENSE`, `SOURCE.md` and the publisher's `copr.htm`, and the site shows the required attribution. IRVTAM and TCV are CC BY-SA 4.0; BSB, WEB and KJV are public domain. See [docs/requirements.md](docs/requirements.md#2-bible-sources).
- **Cross-references** under `data/xrefs/` are from OpenBible.info under CC BY.

## Contributing

The project is at the planning stage. Read the two documents above, then open an issue to discuss a change before sending a pull request. Requirement IDs (for example `R-5.4`) and decision records (`ADR-2`) are the shared vocabulary for discussions.
