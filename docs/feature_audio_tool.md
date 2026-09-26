# Feature design: audio processing tool

Status: design 25 Sep 2026. T1–T4 (ingest, upload, verify, build) built 25 Sep 2026; T5–T7 (alignment) not started. Companion to [feature_audio.md](feature_audio.md).

`tools/audio` is an offline command-line tool that the owner runs on their own machine. Its input is a zipped recording of a Bible version, one MP3 per chapter. It:

1. unpacks the zip and matches each file to a book and chapter
2. re-encodes every chapter to the site's format
3. finds where each verse starts in the audio
4. writes the results as small text files that are committed to the repository
5. uploads the MP3s to R2 and checks them

On the next deploy, `usfm-ingest` builds the committed files into the content. Nothing in this design reads or writes the database.

## 1. Decisions

| Question | Decision |
|---|---|
| Language | Python 3.12 (`tools/audio/pyproject.toml`), installed with `uv` or a plain virtualenv ([tools/audio/README.md](../tools/audio/README.md)). T1–T4 use only the standard library, plus `boto3` for upload. The aligner needs PyTorch, which rules out Rust here. This is the one exception to ADR-3 and is recorded as ADR-16. ffmpeg does the audio work, called as a process. |
| Where it runs | On the owner's machine: Windows, macOS or Linux, CPU by default, CUDA if present. Never in CI, which has neither the audio nor the R2 key. |
| What is committed | Settings and results only, in `data/audio/`: one `recording.toml`, one `chapters.tsv` and one timings file per book for each recording. That is under 1 MB per version. Audio is never committed. |
| What is not committed | The unzipped sources, the encoded MP3s, the alignment cache and the review state. They live in `.audio-work/`, which is git-ignored and can be rebuilt from the zip. |
| Settings per recording, not per version | A recording has its own narrator, licence, filename scheme and habits, such as reading the headings or announcing the chapter. They live in `data/audio/{VERSION}/{recording}/recording.toml`. `version.toml` only says which recording is live (`[audio] recording = "r1"`), so `r2` can be prepared and checked before it is switched on. |
| Text source for alignment | The built chapter JSON in `apps/web/static/content`, so `pnpm content` runs first. The aligner then sees exactly the verses, bridges and wording the reader shows. |
| Timings measured against the final MP3 | Alignment decodes the encoded 64 kbit/s file, not the source, so encoder delay and loudness changes are already in the timeline the browser plays. |
| Re-runs | Every step is idempotent and resumable. The work folder keeps a state file with each chapter's input hash and finished steps, so an interrupted overnight run carries on where it stopped, and editing one setting redoes only what depends on it. |
| Uploads | New keys only. An object that already exists with the same sha256 (kept in its metadata) is skipped. One that exists with a different hash stops the upload with an error, because a changed file needs a new recording id (feature_audio.md §1). |
| Order of publishing | Upload, verify, commit, deploy. Committed files never point at an object that isn't live yet. |

## 2. Commands

```
audio <command> --version IRVTAM [--recording r1] [options]
```

| Command | Does | Writes |
|---|---|---|
| `init` | Creates `recording.toml` from a template, asking for narrator, licence and source. It also records the sha256 of each zip. | `data/audio/…/recording.toml` |
| `ingest --zip <file> [--zip …] [--dry-run]` | Unzips the source, maps files to book and chapter, checks them against the text, and encodes the MP3s. `--dry-run` only prints the mapping. | `.audio-work/…/mp3/`, `data/audio/…/chapters.tsv` |
| `align [--book JHN] [--chapter 3] [--force]` | Finds verse starts for every encoded chapter, or the ones named. | `data/audio/…/timings/{BOOK}.tsv`, `.audio-work/…/align/` |
| `review` | Starts a local review page at `http://localhost:8765`. | Edits to the timings files |
| `upload` | Sends the MP3s to `ts-audio` and the original zips to `ts-audio-masters`. | R2 objects |
| `verify` | Checks every chapter through the public domain. | A report |
| `status` | Shows a table per book: mapped, encoded, aligned, flagged, uploaded, verified. | — |
| `run --zip <file>` | Runs `ingest`, `align` and `status` in turn, then stops for review. | as above |

**Stage 1 without timings:** `ingest` → `upload` → `verify` → commit. Alignment can follow later for the same recording, because the MP3s don't change.

## 3. Files

### Committed: `data/audio/`

```
data/audio/
├─ audio.toml                     base = "https://stream.tamilaudiobible.com"
└─ IRVTAM/
   └─ r1/
      ├─ recording.toml
      ├─ chapters.tsv
      └─ timings/
         ├─ GEN.tsv
         └─ …
```

`recording.toml`:

```toml
version     = "IRVTAM"
recording   = "r1"
fileset     = ["TAMDPIO1DA", "TAMDPIN1DA"]   # the publisher's ids, when there are any
narrator    = "…"
publisher   = "davar-partners-international"   # the rights holder's id
licence     = "…"
attribution = "…"
source_url  = "…"
sources     = [{ name = "IRV-TAMDPIO1DA.zip", sha256 = "…" },
               { name = "IRV-TAMDPIN1DA.zip", sha256 = "…" }]

drama       = false            # several voices with music and effects under them (FCBH "2DA")

# How source files are named: a preset, or a regex with named groups
[source]
preset = "fcbh"               # "fcbh", "dbp" or "custom"
# pattern  = '(?P<book>\d{2})_(?P<chapter>\d{3})\.mp3$'   # only for "custom"
# book_key = "number"         # "number" (1–66), "usfm" (JHN) or "name" with [source.names]

[encode]                      # fixed for the site; kept here so a re-encode is visible in git
bitrate_kbps = 64
sample_rate  = 44100
loudness     = -16.0          # LUFS, EBU R128

[align]                       # written by `audio align --probe`, then used by every run (§5)
reads_text     = "IRVTAM"     # the text the recording matched best
text_score     = 0.96         # its mean word score over the probe chapters
reads_headings = false        # mid-chapter headings spoken aloud?
model          = "torchaudio MMS_FA"
torch          = "2.11.0+cu128"
```

`chapters.tsv`, one row per encoded chapter:

```
book	chapter	ms	bytes	sha256
JHN	3	312480	2499840	9f2c…
```

`timings/{BOOK}.tsv`, one row per verse present in the text:

```
chapter	verse	start_ms	end_ms	score	flag
3	1	3940	15610	0.82
3	2	15880	27180	0.79
3	17	160020	171900	0.74	bridge
```

`flag` is empty, `low` (failed a check), `edited` (changed in review; the tool never overwrites these rows unless run with `--force`) or `bridge` (the first verse of a bridge such as `\v 17-18`, whose other verses get no row).

### Not committed: `.audio-work/`

```
.audio-work/IRVTAM/r1/
├─ source/            unzipped originals, as found
├─ mp3/JHN/JHN_003.mp3  final encodes: exactly what is uploaded
├─ wav16k/JHN_003.flac  16 kHz mono decode of the final MP3, input to the aligner
├─ align/JHN_003.json   word-level spans and scores, for the review page
├─ state.json         per chapter: input hash, finished steps, upload and verify results
└─ report.md          the latest ingest and align summary
```

## 4. Ingest

1. **Unzip** each zip into `source/`. A version usually arrives as two zips, OT (`…O1DA`) and NT (`…N1DA`), both passed with `--zip`. It skips `__MACOSX/`, hidden files and anything that isn't audio, and lists what it skipped. A `copyright.pdf`, if present, is kept beside `recording.toml` in the work folder and named in `init`'s licence prompt. Nested folders and one zip per book are both fine.
2. **Map** every audio file through `[source] pattern` to `(book, chapter)`. The `--dry-run` table shows file → book, chapter, plus four lists:
   - unmatched files
   - duplicates
   - chapter 0 or introduction files, which are ignored
   - chapters that exist in the text but have no file

   Two presets cover every file on hand today (§14), and `custom` takes a regex for anything else:

   | Preset | Example | How the book is read |
   |---|---|---|
   | `fcbh` | `A19__150_Psalms______EN1WEBO2DA.mp3`, `Tamil_tam_DPI_NT_Non-Drama/B01___01_Matthew_____TAMDPIN1DA.mp3` | `A` = Old Testament and `B` = New, then the book's number *within that testament* (`A01` Genesis … `A39` Malachi, `B01` Matthew … `B27` Revelation). The chapter is padded with underscores, not zeros (`___01`, `__150`). The name is padded to a fixed width, and a name that fills it runs straight into the id (`A21___01_EcclesiastesEN1WEBO2DA.mp3`), so the id is read as the last ten upper-case characters. The English name and the trailing id are checked for consistency but not relied on. Any folder prefix is ignored. |
   | `dbp` | `ENGBERO1DA_A19_PSA_150.mp3` | The USFM code (`PSA`) directly. The `A19` is checked against it. |

   The numbering *within* a testament is the easiest thing to get wrong: `B01` is Matthew, book 40, not Genesis. The text check in the next step catches any mistake, because the chapter counts stop matching.
3. **Check against the text.** Every mapped chapter must exist in the version's chapter JSON. A book that is entirely missing, as in an NT-only recording, is allowed and reported. A book with only some of its chapters stops the run unless `--allow-gaps` is given, since it usually means a bad pattern.
4. **Encode** in parallel, one process per CPU core:
   - Measure: `ffmpeg -i in -af loudnorm=I=-16:TP=-3:LRA=11:print_format=json -f null -`
   - Encode: `ffmpeg -i in -af loudnorm=…measured values…:linear=true -ac 1 -ar 44100 -c:a libmp3lame -b:a 64k -write_xing 1 -id3v2_version 3 -map_metadata -1 -metadata title="யோவான் 3" -metadata artist="{narrator}" -metadata album="{version name}" -metadata track=3 -metadata comment="{attribution}" out.mp3`
   - Leading and trailing silence is kept. Trimming would save nothing that matters, and alignment doesn't need it.
5. **Measure the result** with `ffprobe`: duration in ms, byte size, sha256. Write `chapters.tsv` sorted by canonical book order, then chapter.
6. **Decode for alignment:** `ffmpeg -i out.mp3 -ac 1 -ar 16000 wav16k/…flac`.

## 5. Align

### What the spike established (25 Sep 2026)

A throwaway script ran MMS forced alignment on the owner's RTX 5090 (PyTorch 2.11, CUDA 12.8) against the encoded MP3s and the built chapter JSON:

| Audio | Text | Words | Mean word score | Verses under 0.45 | GPU time for the chapter |
|---|---|---|---|---|---|
| BSB John 3 (5:12) | BSB | 732 | **0.972** | 0 of 36 | 1.5 s emissions + 0.8 s alignment |
| IRV John 3 (6:03) | IRV | 453 | **0.962** | 0 of 36 | 1.1 s + 0.9 s |
| IRV Genesis 1 (5:43) | IRV | 437 | **0.964** | 0 of 31 | 1.2 s + 1.2 s |
| "TCV" Genesis 1 | TCV | 458 | 0.599 | 2 of 31 | — |
| "TCV" Genesis 1 | IRV | 437 | **0.960** | 0 of 31 | — |
| "TCV" Genesis 2, Psalm 23, Matthew 5 | TCV | — | 0.56–0.60 | — | — |
| the same three | IRV | — | **0.93–0.96** | — | — |

What follows from it:

- **Accuracy is high enough to ship without a person checking every verse.** Matched text scores 0.93–0.97, with no verse under the flag threshold.
- **A wrong text is obvious.** A mismatched text scores about 0.6, a gap no borderline chapter comes near. The chapter-level mismatch test is therefore a mean word score under **0.80**, not a count of flagged verses.
- **The "TCV" recording reads the IRV text** throughout the OT and NT (§14), whatever its tags say. The mismatch test found it on the first chapter tried.
- **Headings can be detected rather than configured.** Forcing BSB's section heading into the transcript gave its words a score of 0.002: the narrator skips it. IRV John 3's heading scored 0.29. `reads_headings` therefore becomes a measured value (below), not a guess in `recording.toml`.
- **Every file opens with 4–8 s before verse 1** (the chapter announcement). Wildcards at both ends absorb it without any setting, so `intro` and `outro` are dropped from `recording.toml`.
- **Speed is not a concern on this GPU.** About 200–300× real time plus a one-off 5–30 s model load, so a whole version of about 90 hours of audio aligns in roughly 20–30 minutes. A CPU run would take hours, as estimated before.

### Model and licence

| Option | Licence | Status |
|---|---|---|
| **`torchaudio.pipelines.MMS_FA`** (MMS 300M, 1,130 languages, uroman input, star token) | Weights **CC BY-NC 4.0**; torchaudio BSD | Chosen. torchaudio had planned to remove `forced_align` in 2.9, then kept it after 2.10 ([pytorch/audio#3902](https://github.com/pytorch/audio/issues/3902)); 2.11 ships it |
| `ctc-forced-aligner` (the same MMS weights, with windowing built in) | BSD code; the default model is CC BY-NC 4.0 too | A fallback wrapper; no licence advantage |
| Per-language wav2vec2 CTC models fine-tuned on Tamil or English (for example the XLSR-53 fine-tunes on Hugging Face) | Several are Apache-2.0 or MIT | The fallback if the non-commercial licence is unacceptable. Weaker on Tamil, native-script vocabularies, no star token, so the ends need trimming by silence detection instead |

**The weights' non-commercial licence is accepted** (owner, 25 Sep 2026): the site is non-commercial. The model runs offline, and only its output (verse start times) is published.

### Probe: what a recording does (`audio align --probe`)

Before a full run, align about 12 chapters spread across the canon (Genesis 1, Psalm 23, Isaiah 53, Matthew 5, John 3, Romans 8, Revelation 21, and so on) three ways, and write the answers into `recording.toml` under `[align]`:

1. **Which text it reads.** Score against every same-language version's text. The best mean must be at least 0.85, belong to this version, and beat the runner-up by 0.2. Otherwise the probe stops and names the text it matched ("this recording reads IRVTAM").
2. **Whether headings are read.** Align with mid-chapter section headings in the transcript (`s` and `ms` headings after verse 1; the one before verse 1 sits against the announcement and is ambiguous). If their words score a mean of at least 0.6, set `reads_headings = true`; otherwise false.
3. **How long the openings are**, for the report only: the median time to the first word of verse 1.

### Per chapter

1. **Transcript** from the built chapter JSON: verse segments in order, each word tagged with its verse. Headings go in only if the probe found them read, and never `r`, `mr` or `sr` references. Footnotes are never included; they aren't in the segment text.
2. **Normalise** each word so it matches what is spoken:

   | Step | Tamil | English |
   |---|---|---|
   | Unicode | NFC; drop U+200C/U+200D (IRV has them) | NFC |
   | Marks | drop `¶ [ ] ( )`, quotes, dashes, `/` | the same (KJV has `¶` and `[ ]`); split hyphenated words |
   | Numbers | the Tamil number speller (below): 484 IRV and 377 TCV verses contain digits | `num2words` on 512 BSB verses; WEB and KJV spell numbers out |
   | Romanise | `uroman` (the `uroman` Python package, `lcode="tam"`) | `uroman`, which leaves Latin letters as they are |
   | Filter | keep only characters in the MMS vocabulary, lower case; a word left empty is dropped, but its verse keeps its other words | the same |

3. **Tamil number speller** (`tools/audio/src/audio_tool/tamil_numbers.py`): cardinals to 10⁷ in the combining forms narrators use (`1,400` → ஆயிரத்து நானூறு, `144,000` → இலட்சத்து நாற்பத்து நான்காயிரம்), with commas and full stops as separators. A digit run followed by a case suffix (`12-ல்`, `3ஆம்`) is spelled and the suffix attached. Where the spoken form differs anyway, the word's low score lands in that verse alone and the verse boundaries either side still hold, because the words round it align.
4. **Wildcards** at both ends, always: one star word before the transcript and one after.
5. **Emissions** in 30 s windows with 2 s of context either side, the context frames trimmed off, concatenated. This is what the spike did; Psalm 119, at 17 minutes, fits in memory. It runs in fp16 on CUDA.
6. **Align** with `torchaudio.functional.forced_align` through the bundle's aligner, and group token spans into words.
7. **Verse starts:** `max((a + b) / 2, b − 300 ms)`, where *a* is the end of the previous verse's last word (for verse 1, 600 ms before its first word) and *b* is the start of this verse's first word. `end_ms` is the next verse's start; for the last verse, its last word's end plus 300 ms, capped at the file length.
8. **Score** each verse by the frame-weighted mean of its tokens' probabilities.
9. **Check and flag:**
   - A verse is flagged `low` if its score is under 0.45, or if its rate (romanised characters per second) is outside 0.4–2.5× the chapter median (0.33–3× for `drama`). The spike found none.
   - The chapter is marked **mismatch** if its mean word score is under 0.80. It then gets no rows, and the reader falls back to playing from the chapter start.
   - Starts must increase; a failure here is a bug, so the run stops.
10. **Write** `timings/{BOOK}.tsv`, keeping rows flagged `edited`, and `align/{BOOK}_{ccc}.json` with every word's span and score, for the review page.

### Dependencies

An optional extra in `pyproject.toml`: `pip install -e "tools/audio[align]"`, with `torch` and `torchaudio` from the CUDA 12.8 index (the RTX 5090 needs it), plus `uroman` and `num2words`. The extra keeps T1–T4 installable without PyTorch. The model (1.2 GB) is cached under `~/.cache/torch/hub`.

### Report

`report.md` and `status` show, per book:

- chapters aligned
- verses flagged
- chapters marked mismatch
- the 20 lowest-scoring verses, with links into the review page

## 6. Review page

`audio review` serves one HTML page and a small JSON API from Python's standard library. It plays the local MP3s from `.audio-work`, so nothing needs to be uploaded yet.

- **Queue:** flagged verses first, then mismatch chapters, then a random sample of 20 unflagged chapters for spot checks. The sample is part of each version's exit test.
- **Verse view:**
  - the verse text, with the previous verse's last words and the next verse's first words
  - a waveform strip of the region, drawn from the 16 kHz audio, with the start marked
  - play from the start, and play the 2 seconds before and after the start
  - nudge by ±100 ms and ±500 ms, or click the waveform to set the start
  - **Accept** (clears the flag) or **Save** (flag becomes `edited`)
- **Chapter view:** scrub the whole chapter with every verse start marked, click a marker to hear it, drag it to move it.
- **Keys:** Space plays, ←/→ nudges 100 ms, Shift+←/→ nudges 500 ms, Enter accepts, J/K moves to the next or previous verse.

Saving rewrites that book's TSV. Nothing reaches the site until the file is committed.

## 7. Upload and verify

`upload` uses `boto3` against R2's S3 endpoint. It reads the key from `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` in the environment or in `.env.audio` at the repository root (git-ignored by `.env*`), never from committed files.

- **MP3 objects:** key `{VERSION}/{recording}/{BOOK}/{BOOK}_{ccc}.mp3` in `ts-audio`, with:
  - `Content-Type: audio/mpeg`
  - `Cache-Control: public, max-age=31536000, immutable`
  - metadata `sha256`
- **Before each MP3:** a HEAD request. Same hash → skip. Different hash → stop. Missing → upload.
- **Masters:** each source zip goes as-is to `ts-audio-masters/{VERSION}/{recording}/source/{name}`.
- **Speed:** 8 uploads at a time, with retries. About 2.3 GB takes as long as your upload bandwidth allows, typically 20–60 minutes. It can be re-run safely.

`verify` checks every row of `chapters.tsv` through `https://stream.tamilaudiobible.com`:

- a HEAD request returns 200 with the expected `Content-Length`, `Content-Type`, `Accept-Ranges: bytes` and cache header
- for one chapter in 50, a range request for the middle 1 kB returns 206 with the right `Content-Range`

Every row must pass before committing.

## 8. Build integration (`usfm-ingest`)

- **New argument:** `--audio data/audio`, added to the `content` scripts in `package.json`.
- **Build id:** for each version whose `version.toml` has `[audio] recording`, `audio.toml`, `recording.toml`, `chapters.tsv` and every timings file are added to the build-id hash (`hash::Fnv64`, alongside the USFM files).
- **Chapter JSON:** when the chapter has a row in `chapters.tsv`, add `"audio": { "src": "{base}/{VERSION}/{recording}/{BOOK}/{BOOK}_{ccc}.mp3", "ms": 312480 }`. That is about 100 bytes, enough for the Listen button and its duration.
- **`{ch}.audio.json`:** when the chapter has timings, write this file beside the chapter JSON, holding `{ "verses": [[1, 3940], [2, 15880], …] }`. The reader fetches it only on Play or "Play from here", so page loads carry no timings at all. Rows flagged `low`, and chapters marked mismatch, are left out, and the reader falls back to playing from the chapter start.
- **Version metadata:** narrator, licence and attribution go into the version's entry in `manifest.json`, for the player's info sheet and `/about`.
- **Validation** (the build fails with the file and line on any of these):
  - a timings row for a verse the text lacks
  - starts that don't increase
  - a start beyond `ms`
  - a `chapters.tsv` row for a chapter the text lacks
  - an unknown `recording` in `version.toml`
- **CI coverage:** the fixture version gets a fixture recording with a hand-written `chapters.tsv` and timings, so CI tests all of this without any audio.

## 9. Tests

| Where | What |
|---|---|
| `tools/audio/tests` (pytest) | filename presets and custom patterns; mapping edge cases (duplicates, chapter 0, gaps); Tamil and English normalisation, including the number speller; the boundary rule on synthetic word spans; the checks; TSV round-trip that keeps `edited` rows |
| `tools/audio/tests`, marked `slow` | an end-to-end run on Psalm 117 from the first cleared recording (two verses, under a minute). It asserts both verse starts land within 250 ms of hand-marked values |
| `crates/usfm-ingest` | `audio` and `.audio.json` output for the fixture recording, the validation errors, and that the build id changes when a timings file changes |

## 10. Setup on the owner's machine

```bash
winget install Gyan.FFmpeg astral-sh.uv
```

```bash
uv sync --project tools/audio
```

Or without uv: `python -m venv tools/audio/.venv`, then `pip install -e tools/audio` inside it. The README has both.

The first `align` downloads the MMS model (about 1.2 GB) into the Torch cache. On an NVIDIA machine, `uv sync --extra cuda` installs the CUDA build of PyTorch.

## 11. A version, end to end

```bash
pnpm content
```

```bash
audio init --version IRVTAM --preset fcbh --zip audio_bibles/IRV-TAMDPIO1DA.zip --zip audio_bibles/IRV-TAMDPIN1DA.zip --publisher davar-partners-international --licence "CC BY-SA 4.0" --attribution "…"
```

```bash
audio ingest --version IRVTAM --recording r1 --zip audio_bibles/IRV-TAMDPIO1DA.zip --zip audio_bibles/IRV-TAMDPIN1DA.zip --dry-run
```

```bash
audio run --version IRVTAM --recording r1 --zip audio_bibles/IRV-TAMDPIO1DA.zip --zip audio_bibles/IRV-TAMDPIN1DA.zip
```

```bash
audio review --version IRVTAM --recording r1
```

```bash
audio upload --version IRVTAM --recording r1
```

```bash
audio verify --version IRVTAM --recording r1
```

Then set `[audio] recording = "r1"` in `data/versions/irvtam/version.toml`, commit `data/audio/IRVTAM/r1/` and the version file, and push. The deploy builds the audio into the content.

## 12. Roadmap

| Step | What | Depends on |
|---|---|---|
| **T1 · Skeleton** | `pyproject`, CLI, `init`, `status`, state file, `.audio-work` in `.gitignore`, ADR-16 in design.md. **Built 25 Sep 2026** | — |
| **T2 · Ingest** | unzip, presets and patterns, mapping checks, two-pass encode, `chapters.tsv`. **Built 25 Sep 2026**; `run` (ingest + align) waits for T5 | T1, a sample zip |
| **T3 · Upload and verify** | boto3 upload with hash checks, masters, verify. **Built 25 Sep 2026**, not yet run against R2 | T2, R2 key |
| **T4 · Build** | `usfm-ingest --audio`, `audio` in chapter JSON and the manifest, build id, validation, fixture recording (`data/fixtures/audio`). **Built 25 Sep 2026** | T2 |
| **T5 · Align** | `[align]` extra; probe (text match, headings); normaliser and Tamil number speller; windowed emissions; forced alignment; boundary rule; checks; timings TSV; report. Spike done 25 Sep 2026 (§5) | T2 |
| **T6 · Review** | local review page | T5 |
| **T7 · Verse files** | `.audio.json` output and fallback rules | T4, T5 |

T1–T4 are all stage 1 needs. T5–T7 are stage 2.

## 13. Risks

| Risk | Check |
|---|---|
| A source's filenames don't fit any preset | `--dry-run` shows the mapping before anything is encoded, and a custom regex covers any scheme |
| One file holds two chapters, or a chapter is split across files | The mapping check reports duplicates and gaps. Splitting and joining files is out of scope; the owner fixes the source, or the chapter is left without audio |
| The narrator adds words that aren't in the text, such as "the Gospel according to John" or a chapter summary | The wildcards absorb speech at either end. Speech in the middle lowers the scores and is flagged |
| The Tamil text has words MMS rarely heard, such as Sanskrit-derived names | Romanisation keeps them pronounceable, alignment is forced rather than recognised, and a low score only flags the verse |
| PyTorch or torchaudio changes the aligner | Versions are locked in `uv.lock` and recorded in `recording.toml`. The slow test catches drift |
| The MMS weights are licensed CC BY-NC 4.0 | Accepted by the owner on 25 Sep 2026: the site is non-commercial. If that ever changes, the fallback is permissively licensed per-language wav2vec2 models (§5), at some cost in accuracy |
| A recording reads a different text from its label (found: "TCV" reads IRV) | The probe compares every same-language text before any timing is written, and refuses to go on unless the recording's own version wins clearly |
| The R2 key leaks | It lives only in the environment or `.env.audio`. It can reach only the two buckets and can be revoked in the dashboard without touching the site |

## 14. Sources on hand (25 Sep 2026)

Ten zips in `audio_bibles/` (git-ignored, about 12 GB): an OT and an NT zip for each of the site's five versions. Every pair holds 929 + 260 = 1,189 files, one per chapter, so every version is complete. The ids are Faith Comes By Hearing / Digital Bible Platform fileset codes, where `1DA` means one narrator and `2DA` drama.

| Version | Zips | Preset | Kind | Licence file in the zip |
|---|---|---|---|---|
| BSB | `ENGBERO1DA`, `ENGBERN1DA` | `dbp` | Narrated | "℗ Public Domain" |
| WEB | `EN1WEBO2DA`, `EN1WEBN2DA` | `fcbh` | **Drama** | Text public domain; "Audio: ℗ Winfred Henson" |
| KJV | `ENGKJVO1DA`, `ENGKJVN1DA` | `fcbh` | Narrated | Text public domain; "Audio: ℗ 1997 & 2000 Hosanna" (Faith Comes By Hearing) |
| IRVTAM | `IRV-TAMDPIO1DA`, `IRV-TAMDPIN1DA` | `fcbh` | Narrated | none |
| ~~TCV~~ | `TCV-TAMDIPO1DA`, `TCV-TAMDIPN1DA` | `fcbh` | Narrated | none; **reads the IRV text, removed** (below) |

What this means for publishing (feature_audio.md §9: nothing is uploaded until its licence permits rehosting):

- **BSB** is marked public domain and can go first. It is also the best first test of the tool.
- **WEB** and **KJV** are copyrighted recordings of public-domain texts. Rehosting needs written permission from the rights holders (Winfred Henson; Hosanna / Faith Comes By Hearing).
- **IRVTAM** and **TCV** came with no licence file. The owner supplied their credits on 25 Sep 2026 (below). The fileset codes (`TAMDPI`, `TAMDIP`) don't name the text edition, so `align` must also confirm that each recording follows that edition. A mismatch shows up as chapters marked mismatch.

Credits supplied by the owner on 25 Sep 2026, now in each `recording.toml`:

| Version | Licence | Attribution | Publisher id |
|---|---|---|---|
| BSB | Public domain | Berean Standard Bible audio, ℗ public domain (from the zip) | — |
| IRVTAM | CC BY-SA 4.0 | Indian Revised Version (IRV) Tamil, CC-BY-SA-4.0, Bridge Connectivity Solutions, 2019 (Text), Tamil Indian Revised Audio Version, CC-BY-SA-4.0, Davar Partners International, 2021 (Audio) | `davar-partners-international` |
| KJV | ℗ 1997 Hosanna | Text: public domain. Audio: ℗ 1997 Hosanna | `hosanna` |
| WEB | ℗ Winfred Henson | Text: public domain. Audio: ℗ Winfred Henson | `winfred-henson` |

All ten zips map completely (1,189 chapters each) with the `fcbh` or `dbp` preset.

**The "TCV" recording is not TCV** (found by the T5 spike, 25 Sep 2026). Its ID3 tags carry the *Biblica Open Indian Tamil Contemporary Version, Audio Edition, ℗ 2024 Biblica and Davar Partners* notice. Yet aligned against the TCV text it scores 0.56–0.60 in Genesis 1 and 2, Psalm 23 and Matthew 5, and against the IRV text 0.93–0.96. Its files are not copies of the IRV recording: every hash differs and chapters run about 1 s longer, so it is most likely the same narration remastered and issued under the TCV name. **Owner's decision, 25 Sep 2026: TCV audio removed.** `data/audio/TCV/` and its encodes were deleted, and TCV has no audio until a recording of the TCV text is found. The owner may want to tell Davar Partners or Faith Comes By Hearing about the mislabelled fileset (`TAMDIP`).
- The tool can run `ingest` and `align` on any of them locally meanwhile. Only `upload` waits for the licence.
