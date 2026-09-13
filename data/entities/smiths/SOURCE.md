# Smith's Bible Dictionary (1863)

| | |
|---|---|
| Author | William Smith (1813–1893), edited; the one-volume "Smith's Bible Dictionary" (Anglican, but approved by the owner for inclusion on 13 Sep 2026 after the sample review) |
| Text | Public domain (published 1863) |
| Dataset | https://github.com/neuu-org/bible-dictionary-dataset, `data/02_sources/smith/*.json`, parsed by NEUU from the CCEL ThML edition (`smith_bibledict.xml`); dataset licence CC BY 4.0 (LICENSE-dataset) |
| Files | 26 files under `src/` (`_index.json`, `a.json` … `z.json`, no `x.json` upstream); `_index.json` reports 4,561 entries and 26,561 scripture references |
| Hash | `src/a.json` sha256 188581289a95c888…, `src/z.json` 6cc1f0c09d83edb3… |
| Downloaded | 2026-09-13 |
| Attribution shown | Smith's Bible Dictionary (1863), public domain; dataset by NEUU, CC BY 4.0 |
| Notes | Same JSON shape as Easton's (`name`, `slug`, `definitions[].text`, `scripture_refs`); the build splits entries into reviewable paragraphs with stable ids under `smiths/{slug}`. Very short cross-reference entries ("See Alpha") are kept: they link the reader to the main article. |
