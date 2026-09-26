# Feature design: Tamil translation of the dictionaries

Produces the Tamil drafts that [feature_dictionary.md](feature_dictionary.md) §5 expects, for Easton, Smith's and the Aquifer Open Bible Dictionary, with Reformed terminology fixed by a glossary drawn from the IRV. Status: design approved 25 Sep 2026; tasks 1–3 done 26 Sep 2026.

## 1. Decisions

| Question | Decision |
|---|---|
| Where the tool lives | `tools/translate/`, a Python command-line package like `tools/audio/`. It reads the build output and writes draft files; the build never calls it. This replaces "runs outside the project" in feature_dictionary.md §5. |
| Provider | Claude through the Anthropic SDK, behind a small provider layer so another provider can be tried in the pilot. |
| Model | Decided after the pilot (§5): Opus 5 and Sonnet 5 are compared on the same articles. |
| Terminology | A theological glossary, `data/entities/glossary-theology-ta.toml`, drawn from how the IRV renders each term, reviewed by the owner. Names come from the reviewed entries of `names-ta.toml`. |
| Scripture quoted in articles | Given the IRV text of each cited verse so quotations use IRV wording rather than a new translation. |
| Doctrine | Translation is faithful. It fixes terminology, never rewrites what an article says. Articles the owner disagrees with go in `data/entities/blocklist.toml`. |
| Licence folders | Drafts of public-domain sources go to `drafts/ta/` (CC BY); drafts of Aquifer go to `drafts/ta-sa/` (CC BY-SA). The build loads both and rejects a draft in the wrong folder. |
| Bulk runs | Message Batches API (half price) with the fixed part of the prompt cached. Direct requests for the pilot and prompt tuning. |

## 2. Scale

| Source | Articles | English words | Drafts |
|---|---|---|---|
| Easton | 3,962 | 418k | `drafts/ta/eastons/` |
| Smith's | 4,488 | 289k | `drafts/ta/smiths/` |
| Aquifer | 4,697 | 1,188k | `drafts/ta-sa/aquifer/` |

About 2.5M English tokens in. Tamil takes several times as many tokens as English, so output is estimated at 10–15M tokens; the pilot measures the real ratio. Rough batch cost: Opus 5 $200–300, Sonnet 5 $80–120.

## 3. Glossary

`data/entities/glossary-theology-ta.toml`, licence CC BY 4.0 (tamilscripture.com contributors):

```toml
["justification"]
ta = "…"                 # the form used in running text
forms = ["…", "…"]       # inflected forms that count as using the term
strongs = ["G1345", "G1347"]
source = "irv"           # irv: taken from IRV verses; curated: owner's choice
avoid = ["…"]            # renderings a draft must not use
note = "…"
verses = ["ROM.4.25", "ROM.5.18"]
review = true            # removed by the owner after checking
```

Built in four steps:

- **G1 seed list.** Reformed doctrinal vocabulary (Westminster Confession and catechism headings), frequent theological words in the three dictionaries, and their Strong's numbers. Kept in `tools/translate/seed/terms.toml`.
- **G2 IRV evidence.** For each term, the verses where its Strong's numbers occur in the BSB (read from the `strong="…"` tags in the USFM), paired with the IRV text of the same verses. The model names the Tamil word the IRV uses and its forms; every form must occur in those IRV verses or the entry is flagged.
- **G3 curated terms.** Terms not in the Bible text (Trinity, sacrament, the doctrines of grace and similar): the model proposes a rendering with its reasons, `source = "curated"`.
- **G4 owner review.** Only entries without `review = true` are given to the translator.

The same G2 step repairs `names-ta.toml`. Since 26 Sep 2026 it holds one entry per English name, used for every Tamil version (the IRV's name; the other versions' inflections of it are among the forms). 1,900 of its 2,815 entries are unreviewed, and names that occur in one or two verses were often matched to an ordinary word. One cause: Tamil puts the verb last and often moves a clause across the verse boundary, so the IRV names Esther's seven chamberlains in 1:11 where the English, and TIPNR, have them in 1:10. The build now checks forms against the name's verses and the verse either side.

`translate verses NAME` is the review tool: the English and IRV verses side by side (with the verse either side for rare names), the Tamil words the verses share ranked by how rare they are and how closely their consonants match the English name, and `--accept LABEL` to write the reviewed entry. It also takes a Strong's number or any English word, for the term glossary.

## 4. Translation

One request per article; long Aquifer articles are split into groups of paragraphs, each sent with the paragraphs before it as context.

- **System prompt (cached, identical for every request):** the style guide (formal written Tamil in the IRV's register, faithful not paraphrased, no added commentary, keep verse references as `புத்தகம் 3:16` using the Tamil book names) and the core glossary.
- **Per-article context:** glossary and reviewed name entries whose English terms occur in the article, the IRV text of every verse the article cites, and the article's Tamil title if a sibling article (`also_in`) already has one.
- **Output:** JSON `{title, paragraphs: [{id, text}]}` through structured output, so paragraph ids cannot drift.

Checks before a draft is written; a failure gets one repair request listing the problems, then the article is flagged:

- same paragraph ids and count, Tamil script, no markup (the build's own rules);
- no English sentence left untranslated;
- every chapter:verse number in the English paragraph is in the Tamil one;
- Tamil length within bounds of the English;
- glossary: where an English term occurs, one of its Tamil forms occurs and no `avoid` form does;
- names: reviewed Tamil names are used.

A draft records `generator.prompt_version`; articles whose draft has the current `source_hash` and prompt version are skipped, so runs can be repeated.

## 5. Pilot

About 60 articles: doctrinal (Justification, Election, Covenant, Atonement, Grace), people, places, short Easton and Smith's entries, long Aquifer entries. Translated with Opus 5 and Sonnet 5, reviewed by the owner for terminology, accuracy and natural Tamil. The model and `prompt_version = 1` are fixed afterwards.

## 6. Tasks

| # | Task | Status |
|---|---|---|
| 1 | entity-ingest loads `drafts/ta-sa/`; a draft in the wrong licence folder is rejected | done |
| 2 | Strong's index from the BSB USFM and IRV verse lookup (in the tool; the reader JSON is unchanged) | done |
| 3 | `tools/translate` core: data loading, API client with caching and structured output, checks, draft writer | done; not yet run against the API |
| 3a | `names-ta.toml` one entry per English name; `translate verses` review tool | done |
| 4 | Glossary G1–G2; the same step over unreviewed names | names done (2,781 of 2,815 reviewed); terms: seed list of 278, `ai-terms` and `review-terms` built |
| 5 | Glossary G3 and owner review | waiting for `ai-terms submit` and the owner's review |
| 6 | Translation command and pilot | |
| 7 | Batch runs: Easton, Smith's, Aquifer | |
