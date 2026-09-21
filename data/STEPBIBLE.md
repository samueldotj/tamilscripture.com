# STEPBible data

The concordance and the names come from STEPBible.org (Tyndale House, Cambridge), licensed CC BY 4.0: <https://github.com/STEPBible/STEPBible-Data>.

STEP asks that others be referred to that repository rather than given a copy, so none of these files are committed. `node scripts/fetch-stepbible.mjs` downloads them at pinned commits, checks each SHA-256, and writes them to ignored paths; CI caches them. The site publishes only data derived from them, with credit on every page that uses them and on `/licences`.

| File | Saved as | Commit | Used for |
|---|---|---|---|
| TAHOT (4 files) | `data/cache/stepbible/TAHOT-*.txt` | `b99716b0cddb` (18 Sep 2026) | every Hebrew word with its Strong's number |
| TAGNT (2 files) | `data/cache/stepbible/TAGNT-*.txt` | `b99716b0cddb` | every Greek word |
| TBESH, TBESG | `data/cache/stepbible/TBES?.txt` | `b99716b0cddb` | lemma, transliteration, gloss, definition |
| TIPNR | `data/entities/tipnr/TIPNR.txt` | `ae39711d7843` (8 Sep 2026) | people, place descriptions, name Strong's numbers |

To move to a newer STEP release, change the commit and hashes in `scripts/fetch-stepbible.mjs`; the build fails if a tagged verse no longer maps onto our text (docs/feature_concordance.md §8).
