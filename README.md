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
- Reader, Standard and Cross-reference display formats.
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
| **M2 · Study** | Word search, cross-references, the Cross-reference format and dual version display. | R-5.1–5.6, 5.9, R-7.1–7.4, R-8.2, R-9.1–9.5, R-3.4 | Search p75 under one second on real queries from the log. | Shipped 7 Sep 2026; 2.14 (log review) ongoing |
| **M3 · Remember** | Sign-in with history, notes and highlights that sync across devices. | R-10.1–10.2, 10.4–10.5, 10.7–10.10, 10.12–10.14, R-1.9 | RLS test suite passes; one user's data is invisible to another through the API. | Code shipped 7 Sep 2026; blocked on owner's Supabase Auth URL setup (3.1); 3.4, 3.8, 3.9 open |
| **M4 · Community** | Highlight counts and heatmaps, anonymous and opt-out. | R-2.1–2.4 | Aggregates refresh hourly and never show counts under the threshold. | Code shipped 7 Sep 2026; 4.7 alerting open |
| **M5 · Later** | Could-priority items, scheduled by demand. | R-1.6, 1.11, 5.7–5.8, 7.5, 10.3, 10.6, 10.11, 10.15, 2.5, 3.6 | | Not started |

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
| 1.1 | `usfm-ingest`: full paratext support (introductions, headings, poetry, paragraphs, footnotes, `\x` markers) | R-3.2 | ☐ |
| 1.2 | `usfm-ingest`: verse bridges and split verses, `bridges` map in chapter JSON | R-3.3 | ☐ |
| 1.3 | Ingest IRVTAM, TCV, BSB, WEB and KJV; golden-file tests; English version selector (BSB default) | R-3.1 | ☐ |
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
| 1.14 | Verse selection (tap verse numbers) and action bar: copy text with reference and link, share via Web Share or link copy | R-1.7 | ☑ |
| 1.15 | Reader, Standard and Cross-reference formats as CSS classes on `<html>`; inline pre-paint stamp in `app.html` | R-8.1, R-8.3, ADR-6 | ☑ |
| 1.16 | Paratext toggles (introductions, headings, footnotes, cross-ref markers) persisted in local storage; default version cookie for the shorthand redirector | R-1.8, R-1.14 | ☑ |
| 1.17 | Reader settings: text size (5 steps), theme, UI language, Tamil typeface (Mukta Malar, Noto Sans, Noto Serif, system) ☑; low-end Android check ☐ | R-1.10, open question 6 | ◧ |
| 1.18 | Self-hosted subset fonts via `scripts/subset-fonts.py` (Tamil faces ~40 kB each, `unicode-range`, `font-display: optional`, preload, fallback metrics); Google Fonts removed | design §10 | ☑ |
| 1.19 | Tamil and English interface strings; default from browser language | requirements §12 | ☐ |
| 1.20 | PWA shell: web manifest with icons, service worker (shell precache, content JSON cache-first, last 20 reader pages offline) | requirements §12, design §9 | ☑ |
| 1.21 | About page with licences and attribution; footer notice on reading pages; site footer link | R-3.5 | ☑ |
| 1.22 | Sitemap index plus one sitemap per version, `robots.txt`, `rel="canonical"`, Tamil page titles | R-1.12, requirements §12 | ☑ |
| 1.23 | CI guards: Lighthouse CI (a11y ≥ 0.95 and CLS < 0.05 as errors, performance ≥ 0.9 as warning) ☑, `size-limit` (reader route ≤ 120 kB, all chunks ≤ 200 kB, wasm, font) ☑; Playwright text-visible-under-500 ms ☐ | design §10 | ◧ |
| 1.24 | Accessibility pass: `lang` attributes, focus states, 44 px targets, WCAG 2.2 AA contrast | requirements §12 | ☐ |
| 1.25 | Production deploy on `www.tamilscripture.com` ☑; Vercel Analytics ☑; Sentry ☐ (needs DSN); uptime probe ☐ | design §11 | ◧ |

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
| 3.1 | Supabase Auth: magic link ☑ and Google button ☑ in the app; Google provider credentials and Site URL / redirect URLs to be entered in the Supabase dashboard by the owner ☐; Facebook deferred (open question 4) | R-10.1, R-10.2 | ◧ |
| 3.2 | Client-side PKCE: `/auth/callback` exchanges the code in the browser; public pages never read the session on the server (ADR-9); supabase-js loads lazily only for signed-in visitors | design §7 | ☑ |
| 3.3 | Migration `20260907200000_personal`: `profiles` (auto-created on signup), `highlights`, `notes`, `history` with RLS, `record_visit`, `export_my_data`, `delete_my_account` | ADR-5, design §7 | ☑ |
| 3.4 | RLS test suite (two users through PostgREST) in CI; needs the M3 development project and a service key in secrets | design §7 | ☐ |
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
| 5.3 | Autocomplete for book names and recent searches | R-5.7 | ☐ |
| 5.4 | Restrict search to testament, book or chapter range | R-5.8 | ☐ |
| 5.5 | Romanised Tamil search input | R-5.4 stretch | ☐ |
| 5.6 | Cross-reference hover preview on desktop | R-7.5 | ☐ |
| 5.7 | Import anonymous highlights and notes at first sign-in | R-10.3 | ☐ |
| 5.8 | "Continue reading" shortcut on the home page | R-10.6 | ☐ |
| 5.9 | Markdown in notes | R-10.11 | ☐ |
| 5.10 | Sub-verse highlights stored as per-version offsets | R-10.15 | ☐ |
| 5.11 | "Most highlighted this month" list on the home page | R-2.5 | ☐ |
| 5.12 | Add a version by config only; first additional Indian language | R-3.6 | ☐ |

## Licences

- **Code** in this repository is released under the [MIT License](LICENSE).
- **Bible texts** are not part of this licence. Each version under `data/versions/` carries its own `LICENSE`, `SOURCE.md` and the publisher's `copr.htm`, and the site shows the required attribution. IRVTAM and TCV are CC BY-SA 4.0; BSB, WEB and KJV are public domain. See [docs/requirements.md](docs/requirements.md#2-bible-sources).
- **Cross-references** under `data/xrefs/` are from OpenBible.info under CC BY.

## Contributing

The project is at the planning stage. Read the two documents above, then open an issue to discuss a change before sending a pull request. Requirement IDs (for example `R-5.4`) and decision records (`ADR-2`) are the shared vocabulary for discussions.
