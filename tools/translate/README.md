# tools/translate

Tamil drafts of the dictionary articles (Easton, Smith's, Aquifer), with Reformed terminology fixed by a glossary drawn from the IRV. It reads the built English articles and writes draft files into `data/entities/drafts/ta/` and `drafts/ta-sa/` (Aquifer, ShareAlike). The design is in [docs/feature_dictionary_translation.md](../../docs/feature_dictionary_translation.md).

## Setup

You need Python 3.12+ and a built site content folder (`pnpm content`). Then either:

```bash
uv sync --project tools/translate
```

or, without uv, a virtualenv:

```bash
python -m venv tools/translate/.venv && tools/translate/.venv/Scripts/pip install -e tools/translate
```

`show`, `verses` and `check` make no API calls. `run`, `repair` and `batch` call the Claude API with the credentials in your environment: `ANTHROPIC_API_KEY`, or a profile from `ant auth login`. Never put a key in a file in this repository.

## Commands

```bash
translate show eastons/justification             # the request that would be sent
translate show eastons/justification --system    # … with the system prompt
translate run eastons/justification aquifer/abagtha --model claude-sonnet-5
translate run --ids-file pilot.txt               # the pilot set
translate repair                                 # retry articles flagged in the last run
translate check --source eastons                 # re-check committed drafts
translate batch submit --source eastons --limit 500 --dry-run
translate batch submit --source eastons --limit 500
translate batch status
translate batch collect msgbatch_…
```

Articles that already have a draft for the current English text and prompt version are skipped; `--force` redoes them.

## Reviewing names and terms

`translate verses` shows the English and IRV verses for a word side by side, marks the English word, and lists the Tamil words those verses share (rare elsewhere in the IRV) as candidates. For a name, candidates whose consonants sound like the English name rank first, and the verse either side is shown too: Tamil often moves a clause across the verse boundary, so the IRV names Esther's chamberlains in 1:11 where the English has them in 1:10.

```bash
translate verses Abagtha                         # a person or place name, as on its page
translate verses Abagtha --tcv                   # with the TCV verse too
translate verses G1344                           # a Strong's number (BSB tags)
translate verses justification --english BSB     # any English word
translate verses Aaron --html                    # a page in .translate-work/ to open in a browser
translate verses Abagtha --accept அபக்தா          # set the reviewed Tamil name in names-ta.toml
translate verses Abana --accept ஆப்னா --forms ஆப்னா,ஆப்னாவும்
```

`--accept` writes the label, collects the forms from the name's IRV and TCV verses (words that start like the label), and removes `review = true`. Run `pnpm content` afterwards: the build checks every form against the text.

### Accepting the clear cases automatically

```bash
translate auto-accept-names --dry-run      # list what would change
translate auto-accept-names                # accept them
translate auto-accept-names --revert       # undo the logged auto-accepts
translate auto-accept-names --sounds 0.96 --unique-above 0.9   # the one suggestion above 0.96, none other above 0.9
translate auto-accept-names --ai            # Claude's answer where it sounds above 0.9 (after ai-names)
```

Accepts suggestion 1 for an unreviewed name when it sounds like the English name (consonant match above `--sounds`, default 0.9, and the same kind of first letter) and the drafted entry was fairly sure (confidence above `--confidence`, default 0.7). Compound and descriptive names (Hamath-zobah, Valley of Rephaim), names with one consonant (Evi) and vocative forms (கோராசீனே) are left for review.

With `--unique-above`, confidence is ignored: a suggestion is accepted when it is the only one that sounds above that value and it sounds above `--sounds`. Stricter checks then apply to every candidate: the vowels must roughly agree too (and closely for names of two consonants, so Esek is not ஈசாக், Isaac); a name ending in a vowel may not get a label ending in a bare consonant (Rhoda is not ரோத்) except a woman's name in ாள்; a Greek name in -us must end in ு; and when two names would get the same Tamil name, or a reviewed name already has it (Jabal and Jubal, யாபால்), neither is accepted unless one matches clearly better. The file is backed up to `.translate-work/` first and every change is logged in `.translate-work/auto-accepted.jsonl`; the review then shows only what is left.

### Sending doubtful names back to review

An entry without `review = true` only means the aligner was confident, not that a person checked it. `translate flag-names` marks for review every such single-word name whose Tamil does not sound like the English name (below 0.5, `--below` to change; `--dry-run` to list), for example Moza பெற்றான் ("begat"). Auto-accepted names are left alone. Changes are logged in `.translate-work/flagged-names.jsonl`. Some flagged names are correct translations (James யாக்கோபு, South தென்திசை): press `c` to keep them.

### Asking Claude about the rest

```bash
translate ai-names                               # plan: how many names and requests; no API call
translate ai-names show --names "City of David"  # the request for those names; no API call
translate ai-names submit                        # all of them as a batch (half price)
translate batch status                           # until it says ended (usually within an hour)
translate ai-names collect msgbatch_…            # check the answers and write them
translate review-names --web --ai                # review what Claude could not settle
translate review-names --web --ai-accepted       # spot-check what it settled
translate ai-names run --limit 20                # or: ask about 20 names now, one request per group
```

Names go in groups of up to ten, in text order, so names in the same verses (Esther's seven chamberlains) share a request and each verse is sent once; with the batch discount this costs a small fraction of asking name by name. For each name Claude gets who or what it is, the aligner's guess, and the English and IRV verses (with the verse either side for rare names), and gives the IRV's own spelling, or the IRV's phrase for a name it translates (City of David, தாவீதின் நகரம்).

Every form Claude reports is checked against the IRV and TCV verses. An answer is accepted only when Claude found the name in the IRV, is sure, and every form it gave is in the text; otherwise it becomes the entry's draft, still marked for review. In the review, Claude's answer is suggestion 1 (tagged Claude, so Enter accepts it), with its note and the reason it was not accepted. A name reviewed on the page while the batch ran is left as reviewed. Answers are logged in `.translate-work/ai-names.jsonl`; names already asked are skipped next time (`--again` or `--names` asks again). Needs `ANTHROPIC_API_KEY` in the environment.

### Reviewing all the names

`translate review-names` goes through every unreviewed name in `names-ta.toml`, most verses first. For each it shows who or what the name is, a few English and IRV verses (with the verse either side for rare names), and up to five suggested Tamil names, then asks:

| Key | Does |
|---|---|
| Enter | accept suggestion 1 |
| 1–5 | accept that suggestion |
| a Tamil word | accept what you typed (or `e` to be asked for the name and forms) |
| c | keep the current name, marked reviewed |
| r | reject: the current Tamil is wrong and none of the suggestions is right; it is hidden on the site and left out of later sessions |
| s | skip for now |
| m / t | more verses / show the TCV too |
| u | undo the last answer |
| q | quit |

Every answer is written to the file at once, so you can stop and resume; the next session starts with what is left. `--below 0.6` shows only names whose confidence is under 0.6 (the aligner's own score, shown beside each name); `--order alpha --start Jabez` walks A–Z from a name; `--include-rejected` brings rejected names back; `--all` re-checks reviewed names too. Run `pnpm content` after a session.

```bash
translate review-names --web                      # in the browser (recommended on Windows)
translate review-names                            # in the terminal
translate review-names --web --below 0.6           # only the least certain names
translate review-names --order alpha --start Jabez
```

`--web` serves the same review at http://127.0.0.1:8765/ and opens it: Tamil renders properly there, which Windows consoles do not manage. The keys are the same (Enter, 1–5, `c`, `r`, `s`, `u`, `m`, `t`), `/` jumps to the box for typing a name, and the page shows every answer's saved forms. Stop the server with Ctrl+C in the terminal; it prints the session's totals. It listens on this computer only.

## Theological glossary

`data/entities/glossary-theology-ta.toml` fixes the Tamil for about 280 theological terms (the seed list is `tools/translate/seed/terms.toml`; edit it to add or drop terms). Only entries you approve reach the translator.

```bash
translate ai-terms                               # plan: how many terms and requests; no API call
translate ai-terms show --terms justification    # the request for those terms; no API call
translate ai-terms submit                        # all of them as a batch (half price, about $5)
translate batch status                           # until it says ended
translate ai-terms collect msgbatch_…            # write Claude's proposals, all marked for review
translate review-terms --web                     # approve, correct or reject each term
translate ai-terms run --terms "Trinity"         # ask again about one term
```

A batch is half price but waits in a queue: usually under an hour, at most 24. `translate batch status` shows how long each has been running; `translate batch cancel msgbatch_…` stops one (requests already finished stay done and billed; collect it to keep them). Direct runs (`run`, for articles, `ai-names` and `ai-terms`) cost the full price but send 6 requests at a time (`--workers N` to change), so they finish in minutes.

For each term the tool finds the Strong's numbers the BSB tags on its English words, picks up to six verses across the Bible (with the verse before and after, since the IRV often moves a clause), and counts how the dictionaries use it. Claude proposes the IRV's word (or, for terms like Trinity and sacrament with no single Bible word, the Tamil of Reformed teaching), its forms, and renderings to avoid; forms it reports for an IRV word must be in those verses. Capitalised terms are separate entries: the LORD (YHWH, யெகோவா in the IRV) is not the Lord.

On the review page every field is editable; Enter approves as shown, Ctrl+Enter approves from inside a field, `r` rejects, `s` skips, `u` undoes.

## Pilot

About 60 articles (`tools/translate/seed/pilot.txt`: doctrinal articles, well-known people and places, and a seeded random spread of short, medium and long ones) translated by two models, compared blind, then one model's drafts adopted.

```bash
translate pilot run --model claude-opus-5        # into .translate-work/pilot/claude-opus-5/
translate pilot run --model claude-sonnet-5      # into .translate-work/pilot/claude-sonnet-5/
translate pilot                                  # drafts, problems left, tokens and cost per model
translate review-pilot --web                     # compare A and B blind, article by article
translate pilot adopt --model claude-sonnet-5    # copy the chosen drafts into data/entities/drafts/
```

Each run sends 6 articles at a time (`--workers`), writes its drafts, report and saved replies in its own folder, and skips articles already done (`--force` redoes them). On the comparison page each article shows the English beside version A and version B with the checks' remaining problems; which model is A is fixed per article and revealed only on the results page. Keys: `a` A better, `b` B better, `g` both good, `w` both need work, ←/→ to move; a note is saved with each rating. `pilot` estimates the cost of all 13,147 articles from the pilot's own tokens.

The glossary goes with each article: only the approved terms its text uses (a typical article: a few thousand characters), not all 278. Renderings to avoid are checked in their inflected forms too, leaving out those that are part of the term's own Tamil or another approved term's.

## What it writes

- **Drafts:** `data/entities/drafts/ta/{source}/{slug}.json`, or `drafts/ta-sa/aquifer/{slug}.json` for Aquifer. A draft is written unless the build would reject it (missing paragraphs, no Tamil, markup).
- **Work folder:** `.translate-work/`, git-ignored.
  - `report.jsonl`: every article with its remaining problems (glossary, names, verse references, length, untranslated English).
  - `flagged/`: raw replies of flagged articles, for `repair`.
  - `usage.jsonl`: token counts per request, cache reads included.
  - `batches.jsonl` and `{batch id}.json`: submitted batches.

## Glossaries

- **Terms:** `data/entities/glossary-theology-ta.toml`. Only entries without `review = true` are given to the model and checked.
- **Names:** `data/entities/names-ta.toml`, one entry per English name for every Tamil version; only entries without `review = true` are used.

## Tests

```bash
python -m unittest discover -s tools/translate/tests
```
