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

## Tests

```bash
python -m unittest discover -s tools/audio/tests
```
