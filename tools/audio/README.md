# tools/audio

Offline audio Bible tool: zipped chapter MP3s in, site-format MP3s in R2 and committed `data/audio/` files out. The design is in [docs/feature_audio_tool.md](../../docs/feature_audio_tool.md).

## Setup

You need Python 3.12+ and ffmpeg on `PATH` (`winget install Gyan.FFmpeg`). Then either:

```bash
uv sync --project tools/audio
```

or, without uv, a virtualenv:

```bash
python -m venv tools/audio/.venv && tools/audio/.venv/Scripts/pip install -e tools/audio
```

`init`, `ingest`, `verify` and `status` use only the standard library, so they also run without installing anything:

```bash
PYTHONPATH=tools/audio/src python -m audio_tool status --version BSB
```

`upload` needs `boto3` and an R2 API token. Put the token in `.env.audio` at the repository root. That file is git-ignored by `.env*`; never commit it or paste it anywhere:

```
R2_ACCOUNT_ID=…
R2_ACCESS_KEY_ID=…
R2_SECRET_ACCESS_KEY=…
```

## A version, end to end

```bash
audio init   --version BSB --preset dbp --zip audio_bibles/ENGBERO1DA.zip --zip audio_bibles/ENGBERN1DA.zip --licence "…" --attribution "…"
audio ingest --version BSB --zip audio_bibles/ENGBERO1DA.zip --zip audio_bibles/ENGBERN1DA.zip --dry-run
audio ingest --version BSB
audio upload --version BSB --dry-run
audio upload --version BSB
audio verify --version BSB
audio status --version BSB
```

The first `ingest` remembers the zips, so re-runs don't need `--zip`. Everything resumes after an interruption, and a re-run redoes only chapters whose source or encode settings changed.

To go live, commit `data/audio/BSB/r1/`, add this to `data/versions/bsb/version.toml` and push:

```toml
[audio]
recording = "r1"
```

The deploy's `pnpm content` builds the audio into the chapter JSON.

## Verse timings (`align`, stage 2)

`align` needs PyTorch and a GPU (it runs on a CPU too, many times slower). Install the extra into the venv, CUDA build first:

```bash
tools/audio/.venv/Scripts/pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
```

```bash
tools/audio/.venv/Scripts/pip install -e "tools/audio[align]"
```

It reads the chapter text from the built content, so run `pnpm content` first. Then:

```bash
audio align --version BSB --probe
audio align --version BSB
audio status --version BSB
```

`--probe` aligns 14 sample chapters against every text in the version's language. It records in `recording.toml` which text the recording reads and whether its narrator reads section headings. A full run probes first if that hasn't been done. It stops if the recording reads another version's text; pass `--accept` to override. `--book` and `--chapter` narrow a run, and `--force` redoes chapters already aligned. Results go to `data/audio/{VERSION}/{recording}/timings/{BOOK}.tsv`, with a report in `.audio-work/{VERSION}/{recording}/report-align.md`.

## Tests

```bash
python -m unittest discover -s tools/audio/tests
```
