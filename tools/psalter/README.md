# tools/psalter

Psalter tunes for the Psalms explorer: a public-domain MIDI in, a melody-only MusicXML file and its rendered notation, note timings and audio out. The design is in [docs/feature_psalms_explorer.md](../../docs/feature_psalms_explorer.md) §8–9.

## Setup

You need Python 3.12+ and ffmpeg on `PATH`. Then:

```bash
python -m venv tools/psalter/.venv && tools/psalter/.venv/Scripts/pip install -e tools/psalter
```

The organ audio needs FluidSynth and the FluidR3_GM SoundFont, unpacked into `tools/psalter/.cache/` (git-ignored), or named by the `FLUIDSYNTH` and `SOUNDFONT` environment variables:

- FluidSynth: the Windows release from [github.com/FluidSynth/fluidsynth](https://github.com/FluidSynth/fluidsynth/releases) (v2.6.1 was used), unzipped to `.cache/fluidsynth/`.
- FluidR3_GM (MIT, Frank Wen): `FluidR3_GM.sf2` from Debian's `fluid-soundfont-gm` package (3.1-6 was used), at `.cache/FluidR3_GM.sf2`.

## Adding a tune

1. Add a `[[tune]]` to `data/psalter/tunes.toml`. Copy `meter`, `incipit` (the Oxford Hymn Tune Index digits) and the source from the tune's CCEH or hymnary.org page. For `key`, `pickup` (quarter notes before the first barline) and `line_beats` (quarter notes in the first line, which the card shows), ask `psalter infer`, then check the bar lines in the render:

   ```bash
   tools/psalter/.venv/Scripts/psalter infer path/to/000341a.mid "53425 42171"
   ```

2. Import the MIDI. The soprano line is taken from track 1 (where the alto crosses above it within the incipit, the chord's note that matches the incipit is taken) and checked against the incipit; a mismatch stops the import. Time signatures in quarters and halves (4/4, 3/2, 2/2) are supported.

   ```bash
   tools/psalter/.venv/Scripts/psalter import crimond path/to/000341a.mid
   ```

3. Render it. This writes `data/psalter/rendered/{id}/`: `incipit.svg`, `full.svg`, their `*.draw.json` for the app, `events.json` (note and line timings), `audio.mp3` (one stanza on organ, from the four-part MIDI that `import` keeps in `data/psalter/sources/`) and `render.json`.

   ```bash
   tools/psalter/.venv/Scripts/psalter render crimond
   ```

4. Pair it with versions of psalms in `data/psalter/pairings.toml` (keys as in `data/psalter/scottish-1650/`), then run `pnpm content`. The build rejects a tune whose metre does not fit the version.

The MusicXML, the source MIDI and the rendered files are all committed, so CI never needs Verovio, FluidSynth or ffmpeg. `entity-ingest` checks each `render.json` against the SHA-256 of its MusicXML and MIDI and fails if a tune was edited without being rendered again. Rendering is deterministic: running it twice gives identical bytes.

Before deleting a tune's `review = true`, play the audio and compare the notation with a printed psalter.

## Tests

```bash
PYTHONPATH=tools/psalter/src tools/psalter/.venv/Scripts/python -m unittest discover -s tools/psalter/tests
```
