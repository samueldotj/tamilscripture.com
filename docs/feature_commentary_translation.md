# Feature design: Tamil translation of the Bible commentaries

Tamil drafts of the public-domain commentaries imported in the
[bible-commentaries](https://github.com/samueldotj/bible-commentaries) repository: Geneva notes, Matthew Henry,
Calvin, Poole, Trapp, and the Early Church Fathers. The tool is `tools/translate` (`translate commentary …`),
the same one that made the dictionary drafts ([feature_dictionary_translation.md](feature_dictionary_translation.md)).
The page design is not part of this document. Status: tool built 27 Sep 2026; pilot next.

## 1. Decisions

| Question | Decision |
|---|---|
| Where the data lives | The English and the drafts live in the bible-commentaries repository, next to this one (`TRANSLATE_COMMENTARIES` overrides the path). About 175 MB of English JSON, and more in Tamil, would slow this repository and its deploys. The site will read published chapter files from R2. |
| Unit of translation | One unit: a comment on a verse or range, a chapter's introduction, or a book's. A unit over 2,500 words is sent in parts, as long articles are; a footnote stays in the part of the paragraph that marks it. |
| What is reused | The API client, Message Batches, the theological glossary, the reviewed names, the IRV verse lookup, the repair turn, and the building blocks of the checks. The dictionary code is unchanged; `client.params` takes the output schema as an argument. |
| Scripture | The IRV text of the verses a unit explains (up to 60) and of other verses it cites (up to 40) goes with every request. Quotations of the verse use IRV wording, unless the commentator's point rests on his own Bible's wording. |
| Anchors | The old-English words a note explains (Poole's and Calvin's lemmas, Trapp's "Ver. 1. words]", Geneva's marked words) are translated as the IRV's words for that phrase. |
| References | Written with the Tamil book name and chapter:verse in Arabic numerals, whatever the English form ("Mal. ii. 7" → மல்கியா 2:7), from the verse ids the import attached to each paragraph. |
| Latin, Greek, Hebrew | Kept as written, with a Tamil rendering in brackets where the English gives none. To be confirmed in the pilot. `[Hebrew]` markers (Poole) stay. |
| Footnotes | Translated: Calvin's editors' notes (owner, 27 Sep 2026) and Trapp's sources. Markers `{a}`, `{55}` stay in place. |
| Licence folders | `ta/` for the public-domain commentaries (CC BY, as the dictionary drafts). `ta-ecf/` for the Early Church Fathers, which SermonIndex allows to be copied, shared and distributed for personal and ministry purposes. |
| Doctrine | Faithful translation, as for the dictionary: terminology is fixed by the glossary, and nothing the commentator says is softened or corrected. |

## 2. Scale

English words, including anchors, from `translate commentary status`:

| Commentary | Units | English words |
|---|---|---|
| Geneva | 14,583 | 0.46M |
| Matthew Henry | 5,484 | 6.47M |
| Calvin | 13,724 | 7.10M |
| Poole | 27,136 | 3.42M |
| Trapp | 27,595 | 3.47M |
| Early Church Fathers | not yet imported | 13.4M |

The dictionary run cost about $100 per million English words on Claude Sonnet 5 as batches. At that rate the
five imported commentaries cost about $2,100, and the Early Church Fathers about $1,340. The pilot measures
the real rate.

## 3. Drafts

`ta/{source}/{BOOK}/{chapter}.json` (`intro.json` for a book's introduction), one per chapter, beside the English:

```json
{
 "source": "henry", "book": "JHN", "chapter": 3, "lang": "ta",
 "units": [
  {"id": "henry/JHN.3.1-21", "source_hash": "3b0c9a1e",
   "generator": {"name": "claude", "model": "claude-sonnet-5", "prompt_version": "c1", "generated_at": "2026-09-28"},
   "title": "…",
   "paragraphs": [{"id": "henry/JHN.3.1-21#p1-9f19f8ba", "text": "…", "anchor": "…"}]}
 ]
}
```

A unit is skipped when its draft has the current `source_hash` and `prompt_version`.

## 4. Checks

A failing part gets one repair turn:

- same paragraph ids; Tamil script, no markup, at most 4,000 characters (the dictionary's rules);
- an anchor in Tamil wherever the English paragraph has one;
- no English sentence left untranslated. A run of Latin words is not English: at least two common English
  words must occur in it;
- every chapter:verse number in the English is in the Tamil, and every reference in `refs` is there
  (chapter:verse, or the verse alone for a verse of the unit's own chapter);
- footnote markers and `[Hebrew]` markers kept;
- Tamil length 0.6–3.5 times the English (not checked for footnotes, where Latin is kept and rendered);
- glossary terms and reviewed names, as for the dictionary; a form also counts without its last letter
  when that is a consonant or a vowel sign, which the case endings replace (ஜெபம் matches ஜெபத்தில்,
  ஜெபித்து; தேசம் matches தேசங்கள்).

The repair turn sends back only the flagged paragraphs: their English with the glossary, names and verses
they need, the earlier Tamil of those paragraphs, and the problems. The answer holds those paragraphs,
which replace theirs in the first answer. When the problem is not in a paragraph (no answer, paragraph
ids wrong), the whole part goes back with the first answer, as the dictionary does.

## 5. Commands

```
translate commentary status                       units and current drafts per commentary
translate commentary show henry/JHN.3.1-21        print the requests; no API call (--system for the system prompt)
translate commentary run --source trapp --every 500 --limit 8    translate now, direct
```

Work files are in `.translate-work/commentary/` (report, flagged replies).

## 6. Tasks

| # | Task | Status |
|---|---|---|
| 1 | Import the English (bible-commentaries `tools/import_*.py`) | done for five; Early Church Fathers next |
| 2 | `translate commentary`: loading, prompt, checks, drafts, direct runs | done; not yet run against the API |
| 3 | Pilot: about 40 units across the commentaries, Sonnet 5 and Opus 5.5 compared blind | |
| 4 | Batch runs: `commentary` in `full-run` or its own batch command | |
| 5 | Publish to R2 and the page (owner's design) | |
