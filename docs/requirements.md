# Tamil Bible Study Web App — Requirements

**தமிழ் வேதாகம வாசிப்பு மற்றும் ஆய்வுத் தளம்**

| | |
|---|---|
| Site | https://www.tamilscripture.com |
| Version | 0.1 draft, 6 September 2026 |
| Primary language | Tamil (தமிழ்), English secondary |
| Texts | TCV, IRVTAM, one English version |
| Stack | SvelteKit · Supabase · Vercel · Rust tooling |
| Priority scheme | Must / Should / Could |

A fast, mobile-first website for reading, searching and studying the Bible in Tamil, with English alongside, cross-references, personal notes and highlights, and community reading heat.

Companion document: [design.md](design.md).

## Contents

1. [Overview and goals](#1-overview-and-goals)
2. [Bible sources](#2-bible-sources)
3. [Reading and navigation](#3-reading-and-navigation)
4. [URL scheme](#4-url-scheme)
5. [Search](#5-search)
6. [Cross-references](#6-cross-references)
7. [Display formats](#7-display-formats)
8. [Dual version display](#8-dual-version-display)
9. [Accounts, notes and highlights](#9-accounts-notes-and-highlights)
10. [Community stats](#10-community-stats)
11. [Performance](#11-performance)
12. [Other non-functional requirements](#12-other-non-functional-requirements)
13. [Tech stack and architecture](#13-tech-stack-and-architecture)
14. [Data model](#14-data-model)
15. [Delivery phases](#15-delivery-phases)
16. [Open questions and assumptions](#16-open-questions-and-assumptions)

Requirement IDs follow the numbering of the original feature list (R-1.x reading, R-2.x stats, R-3.x sources, R-5.x search, R-7.x cross-references, R-8.x formats, R-9.x dual display, R-10.x accounts).

---

## 1. Overview and goals

The site serves Tamil-speaking Bible readers, most of them on phones, who today rely on printed Bibles or English-centric apps with weak Tamil support. It should feel as quick as flipping pages and as precise as a concordance.

### Goals

- **Tamil first.** Every feature works in Tamil script: reference input, search, book names, interface labels, and URLs.
- **Instant.** Any verse opens in under half a second. Search answers within a second.
- **Shareable.** Every verse and range has a stable, human-readable link.
- **Study, not just reading.** Cross-references, parallel versions, notes and highlights.
- **Community signal.** Readers can see which verses others highlight most.

### Out of scope for version 1

- Audio Bibles, reading plans, devotionals, commentaries.
- Native mobile apps. The web app must be installable as a PWA instead.
- Social features beyond aggregate stats: no comments, sharing of notes, or groups.
- Languages other than Tamil and English. The data model must not block adding Hindi, Telugu, Malayalam or Kannada later.

### Terms

| Term | Meaning |
|---|---|
| Reference | A book, chapter and optional verse or verse range, such as `John 3:16-18` or யோவான் 3:16. |
| Version | One translation of the Bible, such as IRVTAM. Identified by a short code. |
| Paratext | Text that is not scripture: book introductions, section headings, footnotes, cross-reference markers. |
| Format | A layout choice that changes how verses and paratext are laid out. See section 7. |
| Highlight | A coloured marking a signed-in user applies to one or more verses. |
| Heatmap | A visualisation of how often each verse in a chapter or book has been highlighted across all users. |

---

## 2. Bible sources

The launch corpus is two Tamil versions plus three English versions, all downloaded as USFM from eBible.org and never edited by hand inside the app. IRVTAM is the default reading text. The user picks which English version to show.

| Code | Name | Language | Source | Licence | Role |
|---|---|---|---|---|---|
| `IRVTAM` | Indian Revised Version, Tamil (இண்டியன் ரிவைஸ்டு வெர்ஸன்) | Tamil | eBible.org id `tam2017`, © 2017, 2019 Bridge Connectivity Solutions | CC BY-SA 4.0 | **Default** reading text |
| `TCV` | Biblica® Open Indian Tamil Contemporary Version (திறந்தநிலை தமிழ் சமகால பதிப்பு) | Tamil | eBible.org id `tamtcv`, © 2005, 2020, 2022 Biblica, Inc. | CC BY-SA 4.0 | Second Tamil text, default for Tamil-vs-Tamil comparison |
| `BSB` | Berean Standard Bible | English | eBible.org id `engbsb`, BSB Publishing | Public domain | English option, default English |
| `WEB` | World English Bible (without Deuterocanon) | English | eBible.org id `engwebp` | Public domain | English option |
| `KJV` | King James (Authorized) Version, 2006 eBible edition | English | eBible.org id `eng-kjv2006` | Public domain (Crown letters patent apply in the UK) | English option |

> **Attribution.** The two Tamil texts are CC BY-SA 4.0, which requires attribution, a link to the licence, and share-alike on any adapted text. The site shows each version's notice on the `/about` page and in the footer of every reading page (R-3.5). Source files and their licence text are committed under `data/versions/{code}/`.

| ID | Requirement | Priority |
|---|---|---|
| R-3.1 | Import each version from USFM 3 into the database and static build through a repeatable pipeline. Re-running the pipeline on the same input produces identical output. | Must |
| R-3.2 | Preserve all paratext markers from USFM: book introductions (`\ip`, `\is`), section headings (`\s`, `\s1`, `\s2`), poetry lines (`\q1`, `\q2`), paragraph breaks (`\p`), footnotes (`\f`) and cross-references (`\x`). | Must |
| R-3.3 | Handle verse bridges such as `\v 17-18` and split verses such as `\v 5a` so that a reference to any verse in a bridge resolves to the bridged text. | Must |
| R-3.4 | Store a versification map so that verses can be aligned across versions when their numbering differs, for dual display and cross-references. | Should |
| R-3.5 | Display each version's copyright or licence notice, and a link to its source, on the about page and in the footer of every reading page. | Must |
| R-3.6 | Adding a new version (any Indian language) requires only adding its USFM files and a config entry. No code changes. | Should |

---

## 3. Reading and navigation

The reader is the core of the product. It must work without an account, on a slow phone, and with one thumb.

### Reference navigation

| ID | Requirement | Priority |
|---|---|---|
| R-1.1 | Provide a book, chapter and verse picker where every element is clickable. Books are grouped Old and New Testament, listed in Tamil and English names, and the picker reflects the current position. | Must |
| R-1.2 | Provide a reference box that accepts shorthand in English and Tamil and jumps directly to the passage. English examples: `Gen 1:3`, `John 3:16`, `Jn 3`, `1 Cor 13`, `1co13.4-7`, `Ps 23`. Tamil examples: ஆதி 1:3, யோவான் 3:16, யோவா 3, 1 கொரி 13, சங் 23. Separators `:`, `.`, `,` and space between chapter and verse are all accepted. Ranges use `-` or `–`. Tamil numerals (௧௨௩) are accepted as digits. Ambiguous or unknown input shows suggestions rather than an error page. | Must |
| R-1.3 | Browser Back and Forward return to previously viewed passages, restoring scroll position, version and format. Each navigation to a new passage pushes a history entry. Changing a display toggle does not. | Must |
| R-1.4 | Show breadcrumbs above the text: Bible › Testament › Book › Chapter › Verse. Each crumb is a link. Breadcrumbs are emitted as structured data for search engines. | Must |
| R-1.5 | Previous-chapter and next-chapter controls at the top and bottom of the text. On touch screens, horizontal swipe also moves between chapters. | Must |
| R-1.6 | Keyboard shortcuts on desktop: `←` `→` chapters, `/` focuses the reference or search box, `Esc` closes panels. | Could |
| R-1.7 | Tapping a verse number selects the verse and opens a small action bar: copy, share link, highlight, note, cross-references. Tapping more verse numbers extends the selection. | Must |

### Paratext toggles

| ID | Requirement | Priority |
|---|---|---|
| R-1.8 | Book introductions, section headings, footnotes and cross-reference markers each have an independent on/off toggle. Defaults: headings on, introductions on, footnotes on, cross-references on. | Must |
| R-1.9 | Toggles persist for anonymous users in local storage and for signed-in users in their profile, and sync across devices when signed in. | Should |
| R-1.10 | Reader settings include font size (5 steps), line height and a Tamil typeface choice. The default Tamil face must render conjuncts and grantha letters correctly on Android, iOS and Windows. | Must |
| R-1.11 | Light, dark and system theme. | Should |

---

## 4. URL scheme

URLs are part of the interface. A reader should be able to type or read one aloud. English slugs are canonical; Tamil paths are accepted and redirect to the canonical form. The canonical host is `www.tamilscripture.com`; the apex domain redirects to it.

| Pattern | Example | Meaning |
|---|---|---|
| `/{version}/{book}/{chapter}` | `https://www.tamilscripture.com/irvtam/john/3` | Whole chapter |
| `/{version}/{book}/{chapter}/{verse}` | `/irvtam/john/3/16` | Chapter scrolled to and highlighting one verse |
| `/{version}/{book}/{chapter}/{from}-{to}` | `/irvtam/john/3/16-18` | Verse range |
| `/{v1}+{v2}/{book}/{chapter}` | `/irvtam+bsb/john/3` | Dual version display |
| `/{book}/{chapter}` | `/john/3` | Uses the reader's default version, otherwise IRVTAM |
| `/{ref}` shorthand | `/jn3.16`, `/John%203:16` | Parsed like the reference box, then 302 to canonical |
| Tamil path | `/யோவான்/3/16` | Accepted, 301 to `/john/3/16` |
| `/search?q=` | `/search?q=அன்பு` | Search results page, shareable |
| `/heatmap/{book}` | `/heatmap/psalms` | Highlight heatmap for a book |
| `/me/history`, `/me/notes`, `/me/highlights` | | Signed-in pages |

| ID | Requirement | Priority |
|---|---|---|
| R-1.12 | Every verse and range has exactly one canonical URL. Alternate forms redirect to it, and the page carries a `rel="canonical"` tag. | Must |
| R-1.13 | Book slugs follow a published list (for example `gen`, `genesis`, `1co`, `1-corinthians`, `song-of-songs`). Common abbreviations resolve. The slug list is shared with the reference parser. | Must |
| R-1.14 | Display options (format, paratext toggles) do not appear in the URL. They come from user settings, so a shared link opens the same passage in the recipient's own preferred layout. | Must |
| R-1.15 | Shared links produce a rich preview: Open Graph title with the Tamil reference and version, and a description containing the first verse of the range. | Should |

---

## 5. Search

One search box handles references and words. It decides which the user meant, and says so. Tamil search must cope with spelling variation, sandhi and Unicode encoding differences.

| ID | Requirement | Priority |
|---|---|---|
| R-5.1 | A single search bar accepts a verse reference, a verse range or one or more words. If the input parses as a reference, the reader opens that passage directly. Otherwise a results page is shown. | Must |
| R-5.2 | Text search runs against the version currently being read, with a control to widen to all versions in the same language or all versions. | Must |
| R-5.3 | Terms wrapped in double quotes (`"` or the curly variants `“ ”`) match as an exact phrase in the stored text. Unquoted terms match all words in any order. | Must |
| R-5.4 | Unquoted search tolerates spelling variation. For Tamil this means at minimum: Unicode normalisation to NFC before indexing and querying; treating long and short vowel signs as near matches (இ / ஈ, உ / ஊ, எ / ஏ, ஒ / ஓ); treating ன / ண / ந, ல / ள / ழ and ர / ற as near matches; ignoring common case suffixes (-ஐ, -ஆல், -க்கு, -இல்) so அன்பு also finds அன்பை and அன்பினால்; accepting romanised Tamil (`anbu`) as a stretch goal. For English: case-insensitive, stemming, and trigram similarity for misspellings. | Must |
| R-5.5 | Results show the reference, the verse text with matched words emphasised, and the version. Results group by book in canonical order with a count per book, and the user can jump to a book. | Must |
| R-5.6 | An empty search box shows common searches: the most frequent queries over the last 30 days across all users, filtered to remove single-user queries and anything flagged as inappropriate. Show up to 10 in the interface language. | Must |
| R-5.7 | Typing shows autocomplete for book names in both scripts and for recent searches of the current user. | Should |
| R-5.8 | Search may be restricted to a testament, a book or a chapter range from the results page. | Should |
| R-5.9 | Search queries are logged anonymously (query, language, result count, timestamp) to power common searches and quality review. No user identifier is stored with the query. | Must |

### Reference grammar

Reference parsing is shared by the search box, the reference box and shorthand URLs. It is implemented once, unit tested against a fixture list, and compiled to WebAssembly so the browser and server behave identically.

```
reference := book [sep] chapter [vsep verse [range]]
book      := english-name | english-abbrev | tamil-name | tamil-abbrev
             (optional ordinal: "1", "2", "3", "I", "II", "III", "௧", "௨", "௩")
sep       := " " | ""
vsep      := ":" | "." | "," | " "
range     := ("-" | "–") verse
digits    := [0-9]+ | [௦-௯]+

Gen 1:3        →  GEN 1:3         யோவா 3          →  JHN 3
Jn 3           →  JHN 3           1 கொரி 13.4-7   →  1CO 13:4-7
jn3.16         →  JHN 3:16        சங் ௨௩          →  PSA 23
```

---

## 6. Cross-references

Cross-references turn the reader into a study tool. They come from an open dataset, not from the translation, so they work identically across versions.

| ID | Requirement | Priority |
|---|---|---|
| R-7.1 | Each verse shows a marker when cross-references exist. Tapping the marker (or the verse action bar) opens a panel listing the referenced passages with their text in the current version. Each entry is a link to that passage. | Must |
| R-7.2 | Cross-references can be turned off entirely from reader settings. When off, no markers render and no cross-reference data is fetched. | Must |
| R-7.3 | Source dataset: OpenBible.info cross-references (CC BY, about 340,000 links, with vote counts) merged with the `\x` markers present in the USFM of each version. Entries are ordered by vote count, and the panel shows the top 10 with an option to expand. | Must |
| R-7.4 | Following a cross-reference pushes a history entry, so Back returns to the originating verse. | Must |
| R-7.5 | Hovering a cross-reference on desktop previews the verse text in a tooltip without navigating. | Could |

---

## 7. Display formats

Three formats, switchable with one control that remembers the choice. The scripture text is identical across formats; only layout and paratext differ.

| Format | Layout | Verse numbers | Headings | Cross-references | Footnotes |
|---|---|---|---|---|---|
| **Reader** | Flowing paragraphs following USFM paragraph and poetry marks. Generous line height, one column. | Hidden, or faint on hover / tap | Optional | Off | Off |
| **Standard** | Paragraphs with superscript verse numbers, as in a printed Bible. | Superscript | On by default | Markers, panel on tap | Markers |
| **Cross-reference** | One verse per line, with its cross-references listed inline beneath or in a right-hand column on wide screens. | Leading, bold | On | Inline, always visible | Markers |

| ID | Requirement | Priority |
|---|---|---|
| R-8.1 | Reader, Standard and Cross-reference formats as defined above. The format persists per user and applies to any passage opened, including from a shared link. | Must |
| R-8.2 | Switching format does not reload the page or lose the current scroll position beyond the nearest verse. | Should |
| R-8.3 | Highlights, notes and verse selection behave identically in all formats. | Must |

---

## 8. Dual version display

Two versions side by side, aligned verse by verse. Tamil with English is the common case. Tamil with Tamil lets readers compare TCV and IRVTAM wording. On wide screens the versions sit in two columns; on phones they interleave verse by verse in one column.

| ID | Requirement | Priority |
|---|---|---|
| R-9.1 | Any two versions can be displayed together, including two Tamil versions. Verses align on the shared versification map. On screens narrower than 720 px, verses interleave (version A verse 1, version B verse 1, and so on). | Must |
| R-9.2 | Scrolling keeps the two columns in step. Tapping a verse selects it in both columns. | Must |
| R-9.3 | Dual display has its own URL form (`/irvtam+bsb/john/3`) so it is shareable. | Must |
| R-9.4 | Where one version lacks a verse (a bridge or a versification difference), the cell shows a dash and a footnote rather than shifting alignment. | Should |
| R-9.5 | Highlights and notes attach to the reference, not the version, so they appear in both columns. | Must |

---

## 9. Accounts, notes and highlights

Reading never requires an account. Signing in adds memory: what you read, what you marked, what you wrote.

### Sign-in

| ID | Requirement | Priority |
|---|---|---|
| R-10.1 | Sign in with Google and Facebook through Supabase Auth. Apple sign-in is added if the PWA is promoted on iOS. Email magic link as a fallback for users without social accounts. | Must |
| R-10.2 | Only the provider's user id, display name and email are stored. No contact import, no posting permission requested. | Must |
| R-10.3 | Anonymous highlights and notes made before sign-in (kept in local storage) are offered for import at first sign-in. | Could |
| R-10.4 | Users can export all their data as JSON and delete their account, which removes all personal rows within 24 hours. | Must |

### History

| ID | Requirement | Priority |
|---|---|---|
| R-10.5 | Every passage a signed-in user views is recorded (reference, version, timestamp). A history page lists visits newest first, grouped by day, with a filter by book. Consecutive views of the same chapter within 10 minutes collapse into one entry. | Must |
| R-10.6 | A "continue reading" shortcut on the home page returns to the most recent passage. | Should |
| R-10.7 | History can be paused and cleared by the user. | Must |

### Notes

| ID | Requirement | Priority |
|---|---|---|
| R-10.8 | From the verse action bar, a signed-in user adds a plain-text note to one verse or a selected range. Notes support Tamil and English input, up to 5,000 characters, and save automatically. | Must |
| R-10.9 | Verses with a note show a small marker. Tapping it opens the note for reading or editing. A notes page lists all notes with their reference and a search box. | Must |
| R-10.10 | Notes are private. Nothing in version 1 makes a note visible to anyone else. | Must |
| R-10.11 | Basic Markdown (bold, italics, lists, links) renders in notes. | Could |

### Highlights

| ID | Requirement | Priority |
|---|---|---|
| R-10.12 | A signed-in user highlights one or more selected verses in one of at least four colours (yellow, green, blue, pink). Highlights render behind the text in every format and both themes with readable contrast. | Must |
| R-10.13 | Tapping a highlighted verse offers change colour or remove. A highlights page lists all highlights grouped by colour and by book. | Must |
| R-10.14 | Highlights sync across devices within 5 seconds of a change while online, and work offline with later sync on the PWA. | Should |
| R-10.15 | Highlighting a word range within a verse, stored as character offsets on the specific version's text. | Could |

---

## 10. Community stats

Aggregate, anonymous, and opt-out. Readers see what the community finds worth marking, never who marked it.

| ID | Requirement | Priority |
|---|---|---|
| R-2.1 | Each verse shows how many users have highlighted it, as a small count next to the verse number or in the verse action bar. The count updates at most hourly and is hidden below a threshold of 3 to protect privacy. | Must |
| R-2.2 | A heatmap view for each book shows one cell per verse coloured by highlight count, with chapter labels. Tapping a cell opens the verse. A whole-Bible view shows one cell per chapter. Colour steps are quantiles within the book, so short books are not washed out by long ones. | Must |
| R-2.3 | An optional "heat" overlay in the reader tints the verse background by community highlight count. Off by default. | Should |
| R-2.4 | Counts are computed from distinct users, not from highlight rows, so multiple highlights by one user count once. Users can opt out of contributing to aggregates in settings. | Must |
| R-2.5 | A "most highlighted this month" list on the home page, top 10 verses. | Could |

---

## 11. Performance

Budgets are measured, not aspirational. Each is checked in CI with Lighthouse and a synthetic probe from Chennai and Mumbai, at the 75th percentile.

| Page or action | Metric | Budget | Lab profile |
|---|---|---:|---|
| Home page | Largest Contentful Paint | 300 ms | Desktop, cable, warm CDN edge in India |
| Home page | Largest Contentful Paint | 1.2 s | Mid-tier Android, 4G throttled |
| Any chapter or verse | Time to text visible from click (client navigation) | 500 ms | Mid-tier Android, 4G throttled |
| Any chapter or verse | Time to First Byte (cold URL) | 150 ms | From Indian edge |
| Word search | Results rendered from Enter | 1.0 s | Mid-tier Android, 4G throttled |
| Reference jump | Passage visible from Enter | 500 ms | Same |
| Any page | JavaScript shipped (compressed) | ≤ 120 kB | Reader route |
| Any page | Cumulative Layout Shift | < 0.05 | Including web-font swap |

> **On the 300 ms home page.** A round trip from a phone on a mobile network to any server is often 100 ms or more, so 300 ms is realistic only for a fully static, edge-cached page on a good connection. The budget above is stated for that profile, with a separate mobile budget. Both are enforced.

### How the budgets are met

- **Scripture is static content.** Chapter text is built once from USFM into JSON on the CDN. Chapter, verse and range pages are rendered from it on first request and cached at Vercel's edge until the next deploy (ISR), so every request after the first is a static hit. See design ADR-1 for why full prerendering is not possible on Vercel.
- **Prefetch neighbours.** The next and previous chapter are prefetched on hover or when idle.
- **Small, subsetted fonts.** Tamil web font subset to the characters used in the corpus, preloaded, with `font-display: swap` and size-adjusted fallback metrics to keep layout shift near zero.
- **Search index near the user.** Postgres full-text and trigram indexes in Supabase for word search, with a WebAssembly reference parser in the browser so references never touch the server.
- **Personal data loads after text.** Highlights, notes and counts stream in after the scripture text renders and never block it.
- **Aggregates are precomputed.** Highlight counts and heatmaps come from a materialised view refreshed hourly, served as static JSON per book.

---

## 12. Other non-functional requirements

### Mobile and responsive
- Layout works from 320 px to 2,560 px wide with no horizontal scrolling.
- Touch targets at least 44 × 44 px.
- Installable PWA; the last 20 visited chapters and the current book are available offline.
- Text remains readable with browser zoom to 200%.

### Accessibility
- WCAG 2.2 AA. Contrast ≥ 4.5:1 for text, including on highlight colours.
- Full keyboard operation; visible focus.
- Correct `lang` attributes (`ta`, `en`) on every text block so screen readers switch voices.
- Verse numbers hidden from screen readers in Reader format, exposed as labels elsewhere.

### Interface language
- All interface text available in Tamil and English, switchable independently of the Bible version.
- Default follows the browser language; Tamil browsers get Tamil UI.
- Numbers in UI use Western digits by default with a Tamil-numeral option.

### Search engine visibility
- Every chapter page is server-rendered HTML with title, description, canonical, breadcrumb and Open Graph tags.
- Sitemaps per version, split by testament.
- Tamil-language titles so Tamil queries rank.

### Privacy and security
- Row-level security on every personal table; users can read and write only their own rows.
- Aggregate stats never expose user ids. Threshold of 3 before any count is shown.
- No third-party analytics scripts. Vercel Analytics or a self-hosted, cookie-free counter only.
- Privacy policy and data export/delete as in R-10.4.

### Reliability and operations
- Reading works even if Supabase is down, because text is static. Only sign-in features degrade, with a clear message.
- Daily database backups with 30-day retention.
- Error tracking with source maps; uptime probe every minute.
- Preview deployments for every pull request.

---

## 13. Tech stack and architecture

SvelteKit on Vercel for the site, Supabase for everything personal, and Rust where compiled speed and correctness pay off: the text pipeline and the shared parsing and search logic. Full detail is in [design.md](design.md).

| Tier | Choice | Notes |
|---|---|---|
| Front end | SvelteKit 2 + TypeScript | Static prerendering for all scripture routes, server-side rendering for personal pages, client-side routing for instant chapter moves. Vercel adapter with edge runtime for the shorthand URL redirector. |
| Hosting | Vercel | Edge CDN with Mumbai as the primary serverless region. Preview deployments per branch. Build runs the Rust pipeline via a prebuilt binary or a GitHub Actions artifact. |
| Data and auth | Supabase (Postgres 16) | Row-level security for users, history, notes, highlights and search logs. Supabase Auth for Google, Facebook and magic link. Materialised views for aggregates. Full-text search with `pg_trgm` and a custom Tamil normalisation function. |
| Compiled core | Rust | Crates `usfm-ingest` (USFM to JSON and SQL), `bible-ref` (reference grammar, book slugs, Tamil abbreviations) and `tamil-norm` (Unicode and fuzzy normalisation). The last two compile to WebAssembly for the browser and to a native library for the pipeline and a Postgres function. |

> **Where Rust fits, honestly.** SvelteKit itself must be written in TypeScript; there is no Rust SvelteKit. Rust earns its place in three spots: the build-time text pipeline, the reference parser and Tamil normaliser shared as WebAssembly between browser and server, and optionally Vercel serverless functions written in Rust for the search endpoint if Postgres alone cannot hit the one-second budget. Start with Postgres for search and add the Rust function only if measurements demand it.

### Request flow for a verse URL

1. User opens `/irvtam/john/3/16`. Vercel edge serves the prerendered `/irvtam/john/3` HTML immediately.
2. The page hydrates, scrolls to verse 16 and marks it, reading the user's format and toggles from local storage.
3. If signed in, the client fetches highlights and notes for John 3 from Supabase with the user's session, and the visit is recorded.
4. The static JSON for John's highlight counts is fetched from the CDN and counts render next to verse numbers.
5. Cross-reference data for John 3 is fetched as static JSON only if cross-references are on.

### Repository and build

- One monorepo: `apps/web` (SvelteKit), `crates/*` (Rust), `data/` (USFM sources and licences), `supabase/` (migrations, policies, seed).
- CI runs Rust tests, the reference parser fixture suite in both native and WebAssembly builds, Svelte checks, Playwright end-to-end tests on a phone viewport, and Lighthouse budgets.
- Database changes only through versioned migrations. Row-level security policies are tested with a dedicated suite that logs in as two users.

---

## 14. Data model

Scripture is static and versioned by build. Personal data lives in Postgres and is keyed by a version-independent verse id so notes and highlights survive adding or updating translations.

| Table or file | Key fields | Notes |
|---|---|---|
| `versions` | code, language, name, licence, attribution, source_url | Static config, also emitted to the site footer. |
| `books` | usfm_id (GEN…REV), order, testament, name_en, name_ta, slugs[], abbrevs_en[], abbrevs_ta[] | Shared with the Rust parser as a generated file. |
| `verses` (static JSON per chapter) | verse_id (e.g. `JHN.3.16`), version, text, paragraph/poetry marks, headings before, footnotes[] | Built by the pipeline. Also loaded into Postgres for search. |
| `verse_search` | verse_id, version, text, text_norm, tsvector | GIN index on tsvector and trigram index on text_norm. |
| `cross_refs` (static JSON per chapter + table) | from_verse_id, to_verse_id, to_verse_end, votes, source | Merged from OpenBible.info and USFM `\x`. |
| `profiles` | user_id, display_name, ui_lang, default_version, format, toggles jsonb, share_aggregates bool | One row per auth user. |
| `history` | id, user_id, verse_id_start, verse_id_end, version, visited_at | RLS: owner only. Indexed on (user_id, visited_at). |
| `highlights` | id, user_id, verse_id_start, verse_id_end, color, created_at, updated_at | RLS: owner only. Version-independent. |
| `notes` | id, user_id, verse_id_start, verse_id_end, body, created_at, updated_at | RLS: owner only. Full-text index on body for the notes page. |
| `search_log` | id, query, lang, result_count, searched_at | No user id. Insert-only via a security-definer function. |
| `verse_highlight_counts` (materialised view) | verse_id, distinct_users | Refreshed hourly; exported to static JSON per book by a scheduled function. Rows below 3 are dropped. |
| `common_searches` (materialised view) | query, lang, count_30d | Filtered to count ≥ 5 and not in a blocklist. |

---

## 15. Delivery phases

Ship a reader first. Each phase is usable on its own and feeds real usage data into the next.

| Phase | Scope | Requirements | Exit test |
|---|---|---|---|
| **1 · Read** | Ingestion pipeline, IRVTAM, TCV, BSB, WEB and KJV, reader with picker, reference box, breadcrumbs, back/forward, canonical URLs, Standard and Reader formats, paratext toggles, PWA shell. | R-3.1–3.3, 3.5, R-1.1–1.5, 1.7–1.8, 1.10, 1.12–1.14, R-8.1, 8.3 | Every chapter loads under budget on the 4G profile. A Tamil user can reach any verse by typing its Tamil abbreviation. |
| **2 · Study** | Word search with Tamil fuzzy matching, common searches, cross-references, Cross-reference format, dual version display. | R-5.1–5.6, 5.9, R-7.1–7.4, R-8.2, R-9.1–9.5, R-3.4 | Search p75 under one second on real queries from the log. |
| **3 · Remember** | Sign-in, history, notes, highlights, cross-device sync, export and delete. | R-10.1–10.2, 10.4–10.5, 10.7–10.10, 10.12–10.14, R-1.9 | RLS test suite passes; a user's data is invisible to another user via the API. |
| **4 · Community** | Highlight counts, heatmaps, heat overlay, opt-out. | R-2.1–2.4 | Aggregates refresh hourly and never show counts under the threshold. |
| **Later** | Could items: keyboard shortcuts, romanised Tamil search, sub-verse highlights, Markdown notes, monthly top verses, anonymous import. | R-1.6, 1.11, 5.7–5.8, 7.5, 10.3, 10.6, 10.11, 10.15, 2.5, 3.6 | |

---

## 16. Open questions and assumptions

Decisions that change the build. Each names who should decide.

1. ~~**Which TCV, and under what licence?**~~ *Resolved 7 Sep 2026:* Biblica's Open Indian Tamil Contemporary Version from eBible.org (`tamtcv`), CC BY-SA 4.0.
2. ~~**Which English version?**~~ *Resolved 7 Sep 2026:* all three (BSB, WEB, KJV) are offered and the user chooses; BSB is the default English version. IRVTAM is the site default.
3. **Domain.** `www.tamilscripture.com` is the canonical host; the apex `tamilscripture.com` redirects to it. Confirm DNS is on Vercel so both the redirect and the edge CDN are handled there. *Owner.*
4. **Facebook login.** Facebook requires app review and a privacy policy URL, and adds a business verification step. Confirm it is worth the setup or whether Google plus magic link suffices for launch. *Owner.*
5. **Cross-reference dataset.** Assumed OpenBible.info under CC BY. Confirm attribution wording. *Engineering.*
6. **Tamil typeface.** Candidates are Noto Serif Tamil, Noto Sans Tamil and Mukta Malar. Pick after rendering IRVTAM on low-end Android. *Design.*
7. **Assumption: highlights are whole-verse in version 1.** Sub-verse highlighting is deferred because it must be stored per version. *Confirmed unless objected.*
8. **Assumption: notes are private in version 1.** Any sharing feature would change the privacy policy and RLS design. *Confirmed unless objected.*
9. **Assumption: the 300 ms home page budget is a desktop, warm-cache figure.** The mobile budget is 1.2 s as in section 11. *Confirmed unless objected.*
