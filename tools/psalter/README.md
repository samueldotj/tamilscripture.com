# tools/psalter

Psalter tunes for the Psalms explorer: a public-domain MIDI in, a melody-only MusicXML file and its rendered notation, note timings and audio out. The design is in [docs/feature_psalms_explorer.md](../../docs/feature_psalms_explorer.md) §8–9.

## Setup

You need Python 3.12+ and ffmpeg on `PATH`. Then:

```bash
python -m venv tools/psalter/.venv && tools/psalter/.venv/Scripts/pip install -e tools/psalter
```

## Adding a tune

1. Add a `[[tune]]` to `data/psalter/tunes.toml`. Copy `meter`, `incipit` (the Oxford Hymn Tune Index digits) and the source from the tune's CCEH or hymnary.org page, and work out `pickup` (beats before the first barline) and `line_beats` (beats in the first line, which the card shows).
2. Import the MIDI. The soprano line is taken from track 1 and checked against the incipit; a mismatch stops the import.

   ```bash
   tools/psalter/.venv/Scripts/psalter import crimond path/to/000341a.mid
   ```

3. Render it. This writes `data/psalter/rendered/{id}/`: `incipit.svg`, `full.svg`, their `*.draw.json` for the app, `events.json`, `audio.mp3` and `render.json`.

   ```bash
   tools/psalter/.venv/Scripts/psalter render crimond
   ```

4. Pair it with psalms in `data/psalter/pairings.toml`, then run `pnpm content`.

The MusicXML and the rendered files are both committed, so CI never needs Verovio or ffmpeg. `entity-ingest` checks each `render.json` against its MusicXML's SHA-256 and fails if a tune was edited without being rendered again. Rendering is deterministic: running it twice gives identical bytes.

Before deleting a tune's `review = true`, play the audio and compare the notation with a printed psalter.

## Tests

```bash
PYTHONPATH=tools/psalter/src tools/psalter/.venv/Scripts/python -m unittest discover -s tools/psalter/tests
```
