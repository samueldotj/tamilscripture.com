"""psalter: tunes for the Psalms explorer (tools/psalter/README.md).

  psalter import ID MIDI     MIDI → data/psalter/tunes/ID.musicxml (checked against the incipit)
  psalter render [ID ...]    MusicXML → data/psalter/rendered/ID/ (all tunes when none named)
  psalter infer MIDI INCIPIT [SYLLABLES]
                             suggested key, pickup and line_beats for a new tunes.toml entry
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib
from fractions import Fraction
from pathlib import Path

import mido

from . import infer, melody, render

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / 'data' / 'psalter'


def tunes() -> dict[str, dict]:
    with open(DATA / 'tunes.toml', 'rb') as f:
        return {t['id']: t for t in tomllib.load(f)['tune']}


def time_signature(midi_path: str) -> tuple[int, int]:
    """The MIDI's time signature; none means 4/4, as the MIDI standard says."""
    ts = next((m for m in mido.MidiFile(midi_path).tracks[0] if m.type == 'time_signature'), None)
    if ts is None:
        return 4, 4
    if ts.denominator not in (2, 4):
        raise ValueError(f'{midi_path}: time signature {ts.numerator}/{ts.denominator} is not supported')
    return ts.numerator, ts.denominator


def quarters_per_bar(xml: str) -> int:
    beats = int(re.search(r'<beats>(\d+)</beats>', xml).group(1))
    beat_type = int(re.search(r'<beat-type>(\d+)</beat-type>', xml).group(1))
    return beats * 4 // beat_type


def cmd_import(tune_id: str, midi_path: str) -> None:
    t = tunes()[tune_id]
    num, den = time_signature(midi_path)
    key = melody.Key.parse(t['key'])
    notes = melody.melody(midi_path, Fraction(t['pickup']), num * 4 // den, (key, t['incipit']))
    melody.check_incipit(notes, key, t['incipit'])
    xml = melody.musicxml(notes, key, num, Fraction(t['pickup']), t['bpm'], t['name'], den)
    out = DATA / 'tunes' / f'{tune_id}.musicxml'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml, encoding='utf-8', newline='\n')
    print(f'{tune_id}: {len(notes)} notes, incipit {t["incipit"]} matches → {out.relative_to(ROOT)}')


def cmd_render(ids: list[str]) -> None:
    all_tunes = tunes()
    for tune_id in ids or list(all_tunes):
        src = DATA / 'tunes' / f'{tune_id}.musicxml'
        meta = render.render(src, DATA / 'rendered' / tune_id, all_tunes[tune_id], quarters_per_bar(src.read_text(encoding='utf-8')))
        print(f'{tune_id}: rendered with Verovio {meta["verovio"]}')


def suggest(midi_path: str, incipit: str, syllables: int = 8) -> dict:
    """Key, pickup and first line for a tune not yet in tunes.toml (review before use)."""
    mid = mido.MidiFile(midi_path)
    meta = {m.type: m for m in mid.tracks[0] if m.is_meta}
    num, den = time_signature(midi_path)
    beats = num * 4 // den
    ks = meta['key_signature'].key if 'key_signature' in meta else 'C'
    tonic = (melody.TONIC_PC[ks[0]] + (-1 if 'b' in ks[1:] else 1 if '#' in ks[1:] else 0)) % 12
    if ks.endswith('m'):  # a minor signature: use its relative major's tonic
        tonic = (tonic + 3) % 12
    pick = infer.pickup(melody.melody(midi_path, Fraction(0), beats), beats)
    notes = melody.melody(midi_path, pick, beats)
    key = infer.key_for(tonic, notes, incipit)
    notes = melody.melody(midi_path, pick, beats, (melody.Key.parse(key), incipit))
    return {'key': key, 'pickup': int(pick), 'line_beats': infer.line_beats(notes, syllables), 'time': f'{num}/{den}'}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog='psalter', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    i = sub.add_parser('import', help='MIDI to MusicXML')
    i.add_argument('id')
    i.add_argument('midi')
    r = sub.add_parser('render', help='notation, timings and audio')
    r.add_argument('ids', nargs='*')
    g = sub.add_parser('infer', help='suggest key, pickup and line_beats for a new tune')
    g.add_argument('midi')
    g.add_argument('incipit')
    g.add_argument('syllables', nargs='?', type=int, default=8)
    a = p.parse_args(argv)
    try:
        if a.cmd == 'import':
            cmd_import(a.id, a.midi)
        elif a.cmd == 'infer':
            print(suggest(a.midi, a.incipit, a.syllables))
        else:
            cmd_render(a.ids)
    except ValueError as e:
        sys.exit(f'psalter: {e}')


if __name__ == '__main__':
    main()
