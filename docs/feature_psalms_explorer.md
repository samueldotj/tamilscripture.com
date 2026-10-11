# Feature design: Psalms explorer

Status: built 10 Oct 2026 without tunes (§10 steps 2–4): the website's `/psalms` and the app's Study → Psalms. Tunes (steps 6–7) are not built yet. Comes from Claude Design handoff "Tamil Scripture Psalms Explorer" (`Psalms Explorer v2.dc.html` for desktop web, `Psalms Mobile Screen.dc.html` for mobile web and the app). The Android app (`tamilscripture.app`) builds the same feature from the same data (§7).

A reader explores the 150 psalms by theme, genre and author. A grid shows every psalm as a numbered tile with a coloured bar for its theme. Filters narrow the grid. Tapping a number opens a card with the psalm's title, theme, genres and author, a short summary, a key verse in Tamil and English, and, where one is set, a psalter tune shown as notation that can be played. From the card the reader opens the full psalm in the reader or shares the key verse.

## 1. Decisions

| Question | Decision |
|---|---|
| What the facets are | **Theme**: exactly one per psalm, one of eight, coloured (the grid's bar). **Genre**: any number per psalm, from the 15 types of Sean Finnegan's "All 150 Psalms Categorized" (restitutio.org, 2024), followed in the same panel by four fixed **collections** (Songs of Ascents, the seven penitential psalms, Egyptian Hallel, Final Hallel). **Author**: the names in the Hebrew superscriptions, with "Anonymous" for the rest. The Psalter's five books (I–V) were tried as a fourth facet and removed on 10 Oct 2026. |
| How filters combine | Any value within a facet (OR), every facet that has a selection (AND), as in the design. When a filter excludes the open psalm, the card moves to the first psalm that matches. |
| Where the data lives | Hand-edited TOML in `data/psalms/` (§2), like `data/entities/names-ta.toml`: reviewed in git, `review = true` marking lines not yet checked. The restitutio page was imported once by `scripts/import-restitutio-psalms.py`; after that the TOML, not the page, is the source of truth. |
| How it is built | `entity-ingest` gains `psalms.rs`. It validates the TOML and writes `content/{build}/entities/psalms/…` (§4). The text of the key verse is not copied: the page reads it from the reader's own versions. |
| How the app gets it | A new study pack `study.psalms` (prefixes `psalms/` and `psalter/`), built by `pack-build` like `study.people`. When the pack is not installed, `ContentSource` fetches the same files online. |
| URL | `/psalms`, a static route that SvelteKit matches before `[book=book]`. State is in the query: `/psalms?p=23&theme=lament&genre=trust,petition&author=david`. The reader's `/psalms/23` is unchanged. |
| Tunes in this milestone | Scottish Psalter tunes only (§9). The design's Ein feste Burg, Ellacombe and "Miserere" are replaced by Scottish tunes for Psalms 46, 8 and 51. Tamil metrical psalms and *keerthanai* are the next milestone (§11). |
| Music | MusicXML is the stored format. Notation (SVG), a note timing map and the audio are rendered at build time, so neither the browser nor the phone parses MusicXML or synthesises sound (§8). |
| Psalms without a tune | The tune block is hidden. The design's generated "Keerthanai n" melody was only a placeholder and is not built. |
| Language | Labels follow the interface language: the primary language first, the other as the subtitle, as on the plans pages. |

## 2. Data

Three files in `data/psalms/`, all UTF-8 with LF line endings.

### `taxonomy.toml`: the vocabulary

| Table | Fields | Notes |
|---|---|---|
| `[[theme]]` | `id`, `order`, `en`, `ta`, `color` | Eight themes with the design's colours: praise, lament, thanks, trust, wisdom, royal, zion, repent. |
| `[[genre]]` | `id`, `order`, `mood`, `en`, `ta`, `about_en`, `about_ta`, `review` | The 15 restitutio types. `mood` is Brueggemann's orientation, disorientation or reorientation, as the source groups them (Zion is `mixed`). Descriptions are our own wording. |
| `[[collection]]` | `id`, `order`, `en`, `ta`, `psalms`, `basis`, `review` | Fixed groups with their psalms listed here, since membership never varies. |
| `[[author]]` | `id`, `order`, `en`, `ta` | Seven names; Tamil is the IRV spelling from `names-ta.toml`. |

Ids are permanent because they appear in URLs: rename the labels, never the id.

### `psalms.toml`: one line per psalm

```toml
[psalms]
1 = { theme = "wisdom", genres = ["torah", "wisdom"], authors = [], review = true }  # Torah, wisdom
2 = { theme = "royal", genres = ["royal", "prophecy"], authors = [], nt = { authors = ["david"], ref = "Acts 4:25" }, review = true }  # royal, prophecy
101 = { theme = "wisdom", genres = ["wisdom"], maybe = ["royal"], authors = ["david"], review = true }  # wisdom, royal?
```

| Field | Meaning |
|---|---|
| `theme` | One theme id. |
| `genres` | Genre ids; the Genre filter matches any of them. |
| `maybe` | Types the source marked "?". They are not shown and not filtered on. The reviewer moves each one into `genres` or deletes it. |
| `authors` | Author ids from the superscription; `[]` is anonymous. Psalm 88 has two (Sons of Korah, Heman). |
| `nt` | Authors the New Testament names for an untitled psalm (2 and 95), with the reference. The card shows "David (Acts 4:25)"; the Author filter does not count it. |
| `review` | Delete once the line has been checked. |
| trailing comment | The source's original wording, kept for the review. |

One line per psalm keeps the review readable: the whole Psalter fits on three screens, and a change shows as a one-line diff.

### `notes.toml`: titles, summaries and key verses

```toml
[23]
title_ta = "கர்த்தர் என் மேய்ப்பர்"
title_en = "The Lord is my shepherd"
key = "23:1"
tags = ["Shepherd"]
summary_ta = "…"
summary_en = "…"
review = true
```

It is seeded with the design's ten psalms (1, 8, 23, 46, 51, 91, 100, 121, 130, 150). A psalm with no entry is titled after its theme ("புலம்பல் சங்கீதம் · A psalm of lament", as in the design), takes verse 1 as its key verse, and has no summary. The other 140 are drafted later with `tools/translate`, the same draft-and-review flow the dictionary uses (§10, step 5). `tags` are English only for now. They become `{ en, ta }` pairs when the Tamil is written.

### Import and review

`scripts/import-restitutio-psalms.py` read both of the page's tables, the 15 types and the by-psalm list, cross-checked them, and wrote `psalms.toml`. It refuses to overwrite the file without `--force`, so a re-run cannot lose reviewed edits. The two tables disagree in two places, and the by-psalm table was kept:

- Psalm 48 is "praise, Zion" by psalm, but the praise list does not include 48.
- Psalm 144 is "royal, petition" by psalm, but "144?" in the royal list.

Authors come from the superscriptions, not from the source. The draft theme was derived from the genres: a psalm with one genre takes that genre's theme, and a psalm with several takes the most specific one. The order is repentance, royal, Zion, Torah/wisdom, thanksgiving, lament (petition, complaint, imprecatory), historical, trust, prophecy, then praise (praise, enthronement, creation). Historical and prophecy map to "Wisdom & Torah". Every line is marked `review = true`, so check the theme carefully wherever a psalm has more than one genre. The draft gives lament 45, praise 29, wisdom 23, thanksgiving 15, trust 14, Zion 11, royal 8 and repentance 5. The design's own sample lists were illustrative and are not used.

### Validation (build fails on)

- a psalm outside 1–150, or one missing
- an unknown theme, genre, collection or author id
- a theme count of zero (every theme must have at least one psalm, or its tile is a dead button)
- a `key` that is not a verse or range inside that psalm (checked against IRVTAM's verse count)
- a tune pairing whose metre does not match the metrical version (§9)

The build prints how many lines still have `review = true`, as `entity-ingest` does for names.

## 3. Why theme and genre are separate

Restitutio's types are many-to-many: 33 psalms have two or three (29 without the uncertain "?" ones). A coloured grid needs one colour per tile, so each psalm also gets a single theme. Eight themes are few enough to tell apart by colour and to show as tiles. Fifteen genres are not, so they go in the side panel. Genre is the finer, overlapping label ("which psalms ask for rescue?"); theme is the coarse, exclusive one ("what kind of psalm is this?").

## 4. Build output

`entity-ingest` writes under `content/{build}/entities/`:

```text
psalms/index.json        everything the grid and filters need (~18 KB, ~4 KB gzip)
psalms/{n}.json          one per psalm: the card
psalter/{tune}/…         per tune: incipit.svg, full.svg, events.json, audio.mp3 (§8)
```

```jsonc
// psalms/index.json
{
  "themes":      [{ "id": "praise", "en": "Praise", "ta": "துதி", "color": "#EDA100" }],
  "genres":      [{ "id": "trust", "en": "Trust", "ta": "…", "mood": "disorientation" }],
  "collections": [{ "id": "ascents", "en": "Songs of Ascents", "ta": "…", "psalms": [120, …] }],
  "authors":     [{ "id": "david", "en": "David", "ta": "தாவீது" }],
  "psalms": [
    // n, theme, genres, authors, title_ta, title_en, key, tune (or null)
    [23, "praise", ["praise"], ["david"], "கர்த்தர் என் மேய்ப்பர்", "The Lord is my shepherd", "23:1", "crimond"]
  ]
}
// psalms/23.json
{ "n": 23, "summary_ta": "…", "summary_en": "…", "tags": ["Shepherd"],
  "nt": null, "tunes": [{ "id": "crimond", "name": "Crimond", "meter": "C.M.", "key": "G major" }] }
```

Each psalm is a positional array in the index to keep it small. The array's order is documented in a comment and in `lib/psalms/types.ts` and the app's model. Lists are sorted by `order`, so clients never sort.

## 5. Screens

Values (sizes, colours, spacing) are in the design files. This section records behaviour.

**Desktop web** (`Psalms Explorer v2`): a kicker ("Psalms · 150 songs"), a Tamil heading and an English intro. Below that is a two-column layout. The left column is a sticky side panel listing the genres, followed by the collections, as two-line toggle buttons, with "Clear selection" when any filter is set. The right column holds, in order:

1. Author chips in one wrapping row.
2. The eight theme tiles: Tamil name, English name and count, with the colour bar at the foot. Unselected tiles dim when any theme is selected.
3. The grid of numbered tiles (min 3.1 rem, compact 2.4 rem) with the theme colour as a 4 px bottom border. A heading names the active filters ("Psalms of trust", "David · Lament"), a caption gives "*n* of 150", and a legend of theme colours follows.
4. The psalm card in two halves. The left half has the number, the Tamil and English titles, the theme chip, tag chips, the author chip and both summaries. The right half, on a tinted background, has the key verse (Tamil highlighted, English below), the psalter tune, "More on {theme}" (up to eight related numbers) and the actions: Read (`/{version}/psalms/{n}`) and Share.

Tiles move when filters change. Moved tiles slide (FLIP, 320 ms) and newly shown ones scale in (280 ms). Both animations are disabled under `prefers-reduced-motion`. Below 52 rem the layout is one column and the panel is no longer sticky.

**Mobile web** (`Psalms Mobile Screen`, mode `web`): the site header, then the themes, the grid and the card inline below the grid. A Filters button with a red count badge opens a bottom sheet holding Genre and Author. Its footer button reads "Show *n* psalms".

**App** (`Psalms Mobile Screen`, mode `app`): the native shell, with a Filters icon in the title bar (same badge) and the same filter sheet. Tapping a number opens the card as a modal bottom sheet rather than inline.

**Selection state**: the open psalm and the filters are in the URL on the web (replace-state, so Back leaves the page) and in saved state in the app. Neither is stored in the account.

## 6. Website

| Part | Where |
|---|---|
| Route | `apps/web/src/routes/psalms/+page.ts` loads `psalms/index.json` (prerendered; `/psalms` is in the sitemap). `+page.svelte` lays out the panels. |
| Pure logic | `lib/psalms/filter.ts`: `matcher`, `toggled`, `toQuery`/`fromQuery`. No Svelte. The web app has no unit-test runner, so the same rules are tested in the app (`PsalmsTest`, against a copy of the built `index.json`). |
| Components | `routes/psalms/+page.svelte` (panels as snippets shared by the side panel and the phone's filter `<dialog>`, the grid with `animate:flip` and `in:scale`) and `lib/psalms/PsalmCard.svelte`. `TuneBlock.svelte` comes with step 6. |
| Key verse | The card fetches the chapter JSON the reader already uses, for the reader's Tamil and English versions, and slices out the key verse. These files are cached and usually warm. |
| Share | Links to the key verse's single-verse page (`/irvtam/psalms/23.1`), which holds the share image sheet. In the app it opens the reader with the key verse selected, where Share is in the action bar. |
| Colours | The design's hex values map to theme tokens (`--accent`, `--surface-2`, …), so the page follows the dark theme. The eight theme colours get dark-theme variants checked for contrast against `--surface`. |
| Links | Footer: "சங்கீதங்கள் / Psalms explorer". The reader's breadcrumb on a Psalms chapter ends with "Explore the Psalms", linking to `/psalms?p={n}`. |
| Budget | The page's JS chunk is kept under 25 KB gzip. The tune player is loaded only when a psalm with a tune is opened. |

## 7. App

| Part | Where |
|---|---|
| Module | `:feature:study`, `PsalmsScreen.kt` (`PsalmsScreen` loads; `PsalmsExplorer` and `PsalmCardView` draw, so screenshot tests pass fixtures). The Study hub's Psalm explorer card opens it; `/psalms` deep links open it. Models and the filter are in `:core:model` `Psalms.kt`. |
| Data | `PsalmsRepository` reads `entities/psalms/index.json` and `{n}.json` through `ContentSource` (pack, then cache, then network). Models use kotlinx.serialization, mirroring `types.ts`. |
| Logic | `PsalmSelection.matcher` mirrors `filter.ts`. |
| Compact width | Design 1b: title bar with Filters button and badge, theme tiles, grid (`LazyVerticalGrid`, adaptive 44 dp minimum), and the card in a `ModalBottomSheet`. The filter sheet is a second bottom sheet. |
| Medium and expanded | From 840 dp: filters in a 260 dp pane, the grid, and the card in a 400 dp pane, side by side. |
| Tune | `TuneBlock` renders the incipit SVG with AndroidSVG (Apache 2.0) into a `Picture`. It draws the highlight from `events.json` boxes on a Compose `Canvas` overlay and plays `audio.mp3` with a screen-scoped Media3 `ExoPlayer`. Audio focus pauses the Bible audio. |
| Pack | `pack-build` gains `StudyPack { id: "study.psalms", prefixes: &["psalms/", "psalter/"], … }`. It is listed in Downloads under Study. |
| Tests | `PsalmsScreenshotTest` (compact and wide, light and dark, Tamil and English) and `PsalmsTest` (parsing and filters). |

## 8. MusicXML: storing, showing and playing tunes

### Storage

```text
data/psalter/
  tunes.toml                 one [[tune]] per tune: id, name, meter ("C.M." or "8.6.8.6"),
                             key, composer, year, source, licence, file
  tunes/{id}.musicxml        uncompressed MusicXML 4.0, melody only, no lyrics or credits,
                             so diffs are readable
  scottish-1650/psalm-023.toml   metrical text (§9)
  pairings.toml              psalm (and version) → ranked tune ids
```

### Build (once per tune, cached by file hash)

1. **Validate** against the MusicXML 4.0 XSD, then **normalise** with music21: one part, explicit key and time signatures, consistent divisions, and a check that the phrase lengths match the declared metre.
2. **Engrave** with Verovio (Python package; LGPL-3.0 applies only to the build tool, not to our output). This writes `incipit.svg` (the first phrase, matching the design's one-line staff) and `full.svg` (the whole tune at a fixed 600 px width, with `breaks: encoded`). The SVG is post-processed so black becomes `currentColor` (it follows the theme) and every note has a stable `id`.
3. **Time** with Verovio's `renderToTimemap`, plus each notehead's position in the SVG. The result is `events.json`: `[{ id, on_ms, off_ms, midi, x, y }]`.
4. **Render audio** with Verovio's MIDI export and FluidSynth using a small permissively licensed SoundFont (organ or piano), encoded to MP3 at 64 kbps mono (~30 KB a verse).

### Playback

Both platforms play the pre-rendered MP3 with their existing audio stack (`<audio>` on the web, Media3 in the app). They highlight the note whose `on_ms ≤ currentTime < off_ms`: the web toggles a class on the note's SVG id, and the app draws a circle at `(x, y)`. The design's progress bar and "0:12 / 0:31" time come straight from the audio element. This replaces the prototype's Web Audio oscillator: it sounds better, looks the same, and leaves no synthesiser code to keep in step on two platforms.

"Show full tune" (below the incipit) expands `full.svg`, with the highlight following along. Later options: play all stanzas (repeat with a stanza counter), tempo (re-render at two tempos rather than time-stretching), and lyrics under the notes (§9).

### Alternatives considered

| Option | Why not |
|---|---|
| OpenSheetMusicDisplay / VexFlow in the browser | ~300 KB of JS for a 30 KB SVG. Nothing equivalent exists for Compose, so the app would need a WebView. |
| Verovio WASM in the browser | ~2 MB. Same Compose problem. |
| Web Audio or MIDI synthesis on the client | Two synthesisers to keep identical. Android has no system MIDI synth for in-app playback. |

## 9. Importing the Scottish Psalter

*The Psalms of David in Metre* (Church of Scotland, 1650) gives every psalm in English metre, mostly common metre (8.6.8.6). Some psalms have a second version ("another of the same"). Its tunes come from the 1615 and 1635 Scottish psalters and later Scottish use. The 1650 text and these melodies are public domain. Modern engravings and harmonisations may not be, so we encode the melodies ourselves or take them only from sources whose licence is stated.

**Steps**

1. **Text.** Choose a transcription of the 1650 text (candidates: Wikisource, CCEL). Record the source and its licence in `data/psalter/scottish-1650/SOURCE.md`, and import with `scripts/import-scottish-psalter.py` into one TOML per psalm: `versions = [{ meter = "C.M.", stanzas = [["line", "line", "line", "line"], …] }]`. Check that every stanza's syllable count matches its metre and list exceptions for review.
2. **Tune list.** Start from the common tunes of the 1635 psalter and the standard proper tunes (for example Old Hundredth L.M., Old 124th 10.10.10.10.10, Dundee, French, Crimond, St Paul, Martyrdom, Coleshill). About 30–40 tunes cover every psalm, because any common-metre tune fits any common-metre version.
3. **Melodies to MusicXML.** For each tune, in order of preference:
   - a public-domain machine-readable source: ABC from the Open Hymnal Project or hymn-tune collections, converted with `abc2xml`
   - a Mutopia LilyPond file under a free licence, converted with `ly musicxml` and checked by hand
   - entering it ourselves in MuseScore 4 from a public-domain facsimile, then exporting `.musicxml`

   Each tune is then validated and normalised as in §8.1. `tunes.toml` records the source, licence and who checked it.
4. **Pairings.** `pairings.toml` lists traditional associations first (23 → Crimond, 100 → Old Hundredth, 121 → French, 124 → Old 124th, …), then any tune of the right metre. The build rejects a pairing whose metre does not match the version's.
5. **Lyrics under the notes (later).** Hyphenate stanza 1 (English hyphenation, then hand fixes in an overrides file) and attach the syllables to the notes in the build's in-memory MusicXML before engraving. The stored MusicXML stays melody-only.
6. **Showing the text.** The card shows the tune. "Sing this psalm" opens the metrical stanzas next to `full.svg`, with Play.

**Tamil.** The Scottish Psalter is English. Tamil metrical psalms and *keerthanai* are the next milestone (§11). They use the same files and pipeline: a `data/psalter/{collection}/` directory, tunes in `tunes.toml`, and pairings.

## 10. Plan

| Step | Work | Depends on |
|---|---|---|
| 1 | **Review `data/psalms/psalms.toml` and `taxonomy.toml`** (themes, genres, Tamil labels), delete `review = true` as lines are checked | — |
| 2 | `entity-ingest` `psalms.rs`: validation and `psalms/index.json`, `{n}.json`; fixtures; CI determinism | 1 (can start on the draft) |
| 3 | Website `/psalms`: panels, grid, card, filter sheet, URL state, links | 2 |
| 4 | App `:feature:study` Psalms explorer and `study.psalms` pack | 2 |
| 5 | Titles, summaries and key verses for all 150 (`notes.toml`), drafted then reviewed | — |
| 6 | MusicXML pipeline (§8) with six Scottish Psalter tunes for the design's psalms: Old Hundredth (100), Crimond (23), Dundee (121), and the traditional Scottish pairings for 46, 8 and 51 in place of the design's hymn tunes, each confirmed from a printed source (such as the tune index of *The Scottish Psalter 1929*) before it is encoded; tune block on both platforms | 3, 4 |
| 7 | Scottish Psalter text and tunes (§9) | 6 |

Steps 3 and 4 ship without tunes; the tune block appears when step 6 lands.

## 11. Next milestone: Tamil metrical psalms and keerthanai

Not in this milestone. To be designed next:

- Find Tamil metrical psalm translations and *keerthanai* settings of psalms, and confirm their licences (who holds the rights, and whether the text and the music are free to use).
- Decide on notation. Keerthanai are usually sung to Carnatic ragas and talas and are not always written in staff notation. Choose between transcribing to MusicXML (same pipeline as §8), sargam notation shown as text, or recorded audio only.
- Store them alongside the Scottish Psalter: `data/psalter/{collection}/`, tunes in `tunes.toml` and pairings in `pairings.toml`, so the card can offer both an English and a Tamil setting.

## 12. Open questions

- Should the Genre panel show `mood` (orientation, disorientation, reorientation) as group headings?
- Tamil labels for the genres are drafts (`review = true`). The IRV prefers "வேதம்" to "திருச்சட்டம்" for Torah, so the design's "ஞானம் · திருச்சட்டம்" became "வேதப் பிரமாணப் பாடல்கள்" for the Torah genre. Please confirm.

## 13. Sources and licences

- Genres: Sean Finnegan, "All 150 Psalms Categorized", restitutio.org, 18 Feb 2024. Only the psalm-to-type assignments are used, with the type names. Descriptions are our own. Credited on `/licences` and in the page's footnote.
- Authors: the Hebrew superscriptions.
- Collections: the Psalter's superscriptions and Jewish and Christian liturgical tradition.
- Summaries and titles: tamilscripture.com contributors, CC BY 4.0.
- Tunes and the 1650 metrical text: public domain. Each encoding's source and licence is in `tunes.toml` and `SOURCE.md`.
