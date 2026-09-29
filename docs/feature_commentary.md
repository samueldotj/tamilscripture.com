# Feature design: Bible commentaries in the reader

Commentary beside the verses (redesign section 15), from six commentaries in the
[bible-commentaries](https://github.com/samueldotj/bible-commentaries) repository: Matthew Henry, Calvin,
the Geneva notes, Poole, Trapp and the Early Church Fathers. English first; Tamil drafts follow
([feature_commentary_translation.md](feature_commentary_translation.md)) and show where they exist. Status:
built 27 Sep 2026, waiting for the CDN.

## 1. Decisions

| Question | Decision |
|---|---|
| Layout | 15B focus pane on wide screens (≥1180px), as a விளக்கவுரை tab in the context panel. 15C inline cards under the verses on phones and tablets. 15A parallel columns was not taken. |
| Setting | `commentary` (off by default) and `commentarySource` (default `henry`) in the reader settings, from a card in வாசிப்பு அமைப்பு and a chip in the reader toolbar. |
| Where the text comes from | Static JSON on the CDN (R2), published from the bible-commentaries repository (`tools/publish.py`). Never part of a site build or deploy. `PUBLIC_COMMENTARY_BASE` overrides the base URL. |
| Versions | `{base}/latest.json` names the current version (5-minute cache). Files under `{base}/{version}/` never change (one-year cache), so new text needs no deploy. |
| Loading | After paint, only while the setting is on: the index (24 kB) and the chosen commentary's chapter (for example Henry on John 3 is 107 kB, about 35 kB gzipped). The focus pane also fetches the other commentaries' chapters for its "Also in" previews. The views are a lazy chunk. |
| English and Tamil | Tamil where a current draft exists and the site is in Tamil. Otherwise the English, labelled ஆங்கில மூலம் · தமிழாக்கம் விரைவில் (English original, translation coming). |
| Credit and licence | Each comment shows the commentary, its year, the attribution and the licence. The Early Church Fathers are used under SermonIndex's terms (free for personal and ministry purposes). |
| Offline | The service worker caches same-origin requests only, so commentary is not available offline. |

## 2. Files

- `lib/commentary/load.ts`: types, CDN loaders, and unit/verse helpers.
- `lib/commentary/CommentaryText.svelte`: a unit's paragraphs. Anchors are bold; verse numbers and note labels are shown; footnotes; for the Fathers, the author before each quotation and the work after it; references are links.
- `lib/commentary/CommentaryPane.svelte` (15B), `CommentaryInline.svelte` (15C), `CommentaryFoot.svelte` (provenance strip), `views.ts` (the lazy chunk).
- `lib/reader/ChapterPage.svelte`: loading, placing inline comments after the paragraph that ends their verses, the toolbar chip, and the panel tab. `Chapter.svelte` takes an `after` snippet; `ContextPanel.svelte` has a `commentary` tab; `SettingsPanel.svelte` has the commentary card.

## 3. The verse page: commentary for search engines

The single-verse page (`/irvtam/john/3.16`) is the explanation of the verse. Its title is "யோவான் 3:16 விளக்கம் – Explanation of John 3:16" (Tamil first: the Tamil searches are the ones a Tamil commentary can win), and its h1 says the same. The description is the verse and the start of the first comment, in Tamil where there is a draft. Every commentary's comment is rendered with the page, so search engines index it:

- A commentary with a unit per verse (Geneva, Calvin, Poole, Trapp, the Fathers) shows those units whole, with a verse label on range pages (`3.16-18`).
- Henry writes on sections (John 3:1–21 in one unit). The page shows only the paragraphs on the verse: those citing it ("v. 16") and the ones after them, up to the next paragraph citing another verse, at most 14. A link opens the whole section in the reader. Twenty-one pages carrying the same 10,000 words would be duplicate content.
- Tamil is shown where a draft exists, otherwise English. A verse without commentary keeps the old title.

The commentary is fetched in `+page.server.ts` (`lib/commentary/verse.ts`). A fetch in the universal load would inline each fetched chapter (all of the Fathers on John 3) into the HTML. On the server, `load.ts` reads `latest.json` again after five minutes and keeps no chapters in memory.

The reader's verse URLs (`/irvtam/john/3/16`) name the verse page as their canonical, and only the verse pages are in `sitemap-verses.xml`. Links point at it: the reader's verse numbers are links to it (a plain click still selects the verse), scripture references in commentaries, the dictionary, people, Strong's and notes go to it, and each verse page links the verse before and after, across chapters and books. The reader's cross-reference lists still open the reader. ISR pages never expire, so a verse page already rendered keeps the commentary it was rendered with until the next deploy.

## 4. Local development

```bash
python ../bible-commentaries/tools/publish.py build   # dist/commentary/{version}/
python ../bible-commentaries/tools/serve.py           # http://localhost:8790, with CORS
# apps/web/.env.local: PUBLIC_COMMENTARY_BASE=http://localhost:8790/commentary
```

`.claude/launch.json` has `commentary-cdn` (the server above) and `web-5182`.

## 5. Before it goes live

- Upload (`publish.py upload`) to the R2 bucket, and set `PUBLIC_COMMENTARY_BASE` (or the default in `load.ts`) to its public URL.
- A CORS rule on the bucket allowing GET from https://www.tamilscripture.com. Audio does not need one (`<audio>` does not use CORS); `fetch` does.
- Known limit: inline comments follow the paragraph that ends their verses, so in a chapter with long paragraphs, verse-by-verse commentaries (Geneva, Poole, Trapp) stack several cards after one paragraph.

## 6. To do

- Structured data on the verse page: an `Article` (or `CreativeWork`) whose `about` is the verse, naming each commentator as author of their part, beside the BreadcrumbList it has now.
