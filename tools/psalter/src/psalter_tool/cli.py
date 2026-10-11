"""psalter: tunes for the Psalms explorer (tools/psalter/README.md).

  psalter import ID MIDI     MIDI → data/psalter/tunes/ID.musicxml (checked against the incipit)
  psalter render [ID ...]    MusicXML → data/psalter/rendered/ID/ (all tunes when none named)
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib
from fractions import Fraction
from pathlib import Path

import mido

from . import melody, render

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / 'data' / 'psalter'


def tunes() -> dict[str, dict]:
    with open(DATA / 'tunes.toml', 'rb') as f:
        return {t['id']: t for t in tomllib.load(f)['tune']}


def cmd_import(tune_id: str, midi_path: str) -> None:
    t = tunes()[tune_id]
    ts = next((m for m in mido.MidiFile(midi_path).tracks[0] if m.type == 'time_signature'), None)
    if ts is None or ts.denominator != 4:
        raise SystemExit(f'{midi_path}: expected a x/4 time signature')
    key = melody.Key.parse(t['key'])
    notes = melody.melody(midi_path, Fraction(t['pickup']), ts.numerator)
    melody.check_incipit(notes, key, t['incipit'])
    xml = melody.musicxml(notes, key, ts.numerator, Fraction(t['pickup']), t['bpm'], t['name'])
    out = DATA / 'tunes' / f'{tune_id}.musicxml'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml, encoding='utf-8', newline='\n')
    print(f'{tune_id}: {len(notes)} notes, incipit {t["incipit"]} matches → {out.relative_to(ROOT)}')


def cmd_render(ids: list[str]) -> None:
    all_tunes = tunes()
    for tune_id in ids or list(all_tunes):
        src = DATA / 'tunes' / f'{tune_id}.musicxml'
        beats = int(re.search(r'<beats>(\d+)</beats>', src.read_text(encoding='utf-8')).group(1))
        meta = render.render(src, DATA / 'rendered' / tune_id, all_tunes[tune_id], beats)
        print(f'{tune_id}: rendered with Verovio {meta["verovio"]}')


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog='psalter', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    i = sub.add_parser('import', help='MIDI to MusicXML')
    i.add_argument('id')
    i.add_argument('midi')
    r = sub.add_parser('render', help='notation, timings and audio')
    r.add_argument('ids', nargs='*')
    a = p.parse_args(argv)
    try:
        if a.cmd == 'import':
            cmd_import(a.id, a.midi)
        else:
            cmd_render(a.ids)
    except ValueError as e:
        sys.exit(f'psalter: {e}')


if __name__ == '__main__':
    main()
