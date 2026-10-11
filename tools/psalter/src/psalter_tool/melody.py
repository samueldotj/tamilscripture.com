"""The melody of a hymn-tune MIDI, as notes on a beat grid, and its MusicXML.

CCEH MIDIs put the treble staff (soprano and alto) in track 1. The soprano is
the top note of each chord; a lower note that starts while the soprano above it
still sounds is the alto moving and is skipped. The files articulate (a quarter
sounds for 0.83 of a beat), so a note lasts until the next melody note, and the
last note fills its bar (the bar the pickup left short).
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

import mido

STEPS = ['C', 'C', 'D', 'D', 'E', 'F', 'F', 'G', 'G', 'A', 'A', 'B']
SHARP = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]
FLAT_STEPS = ['C', 'D', 'D', 'E', 'E', 'F', 'G', 'G', 'A', 'A', 'B', 'B']
FLAT = [0, -1, 0, -1, 0, 0, -1, 0, -1, 0, -1, 0]
TONIC_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]
FIFTHS_MAJOR = {0: 0, 7: 1, 2: 2, 9: 3, 4: 4, 11: 5, 5: -1, 10: -2, 3: -3, 8: -4, 1: -5}


@dataclass(frozen=True)
class Note:
    onset: Fraction  # beats from the start
    dur: Fraction  # beats
    midi: int


@dataclass(frozen=True)
class Key:
    tonic: int  # pitch class
    minor: bool

    @staticmethod
    def parse(text: str) -> 'Key':
        """'G major', 'E-flat major', 'A minor'."""
        name, mode = text.split()
        pc = TONIC_PC[name[0]] + (-1 if '-flat' in name else 1 if '-sharp' in name else 0)
        return Key(pc % 12, mode == 'minor')

    @property
    def fifths(self) -> int:
        return FIFTHS_MAJOR[(self.tonic + 3) % 12 if self.minor else self.tonic]

    def degree(self, midi: int) -> int:
        """Scale degree 1..7 of a pitch (an altered note counts as the degree below)."""
        rel = (midi - self.tonic) % 12
        scale = MINOR if self.minor else MAJOR
        if rel in scale:
            return scale.index(rel) + 1
        if self.minor and rel == 11:  # raised leading note
            return 7
        return max(i for i, s in enumerate(scale) if s < rel) + 1

    def spell(self, midi: int) -> tuple[str, int, int]:
        """(step, alter, octave) in this key's spelling: flats in flat keys."""
        pc, octave = midi % 12, midi // 12 - 1
        if self.fifths < 0:
            return FLAT_STEPS[pc], FLAT[pc], octave
        return STEPS[pc], SHARP[pc], octave


def melody(path: str, pickup: Fraction, beats_per_bar: int, guide: tuple['Key', str] | None = None) -> list[Note]:
    """`beats_per_bar` counts quarter notes. With `guide` (key, incipit), a chord whose top
    note contradicts the incipit gives the note that matches it: the alto crossing above."""
    mid = mido.MidiFile(path)
    tpb = mid.ticks_per_beat
    t, on, raw = 0, {}, []
    for msg in mid.tracks[1]:
        t += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            on[msg.note] = t
        elif msg.type in ('note_off', 'note_on') and msg.note in on:
            raw.append((on.pop(msg.note), t, msg.note))
    chords: dict[int, list[tuple[int, int]]] = {}
    for a, b, n in raw:
        chords.setdefault(a, []).append((n, b))
    want = guide[1].replace(' ', '') if guide else ''
    top: list[tuple[int, int, int]] = []  # onset, end, pitch
    for onset in sorted(chords):
        pitch, end = max(chords[onset])
        if top and top[-1][1] > onset and top[-1][2] > pitch:
            continue  # an inner voice moving under a held melody note
        i = len(top)
        if guide and i < len(want) and want[i] != '_' and guide[0].degree(pitch) != int(want[i]):
            match = [(n, e) for n, e in chords[onset] if guide[0].degree(n) == int(want[i])]
            if match:
                pitch, end = max(match)
        top.append((onset, end, pitch))
    beats = [Fraction(a, tpb) for a, _, _ in top]
    notes = []
    for i, (a, _, pitch) in enumerate(top):
        if i + 1 < len(top):
            dur = beats[i + 1] - beats[i]
        else:
            # The last bar is short by the pickup: the last note fills it.
            into = (beats[i] - pickup) % beats_per_bar
            dur = beats_per_bar - pickup - into if pickup else beats_per_bar - into
        notes.append(Note(beats[i], dur, pitch))
    return notes


def incipit_digits(notes: list[Note], key: Key, n: int) -> str:
    return ''.join(str(key.degree(x.midi)) for x in notes[:n])


def check_incipit(notes: list[Note], key: Key, incipit: str) -> None:
    """The melody's opening against the Oxford Hymn Tune Index digits; '_' matches anything."""
    want = incipit.replace(' ', '').rstrip('_')
    got = incipit_digits(notes, key, len(want))
    if len(got) < len(want) or any(w != '_' and w != g for w, g in zip(want, got)):
        raise ValueError(f'melody opens {got}, the incipit is {want}')


# ---- MusicXML ------------------------------------------------------------------------

DIV = 4  # divisions per quarter note
TYPES = {16: ('whole', 0), 12: ('half', 1), 8: ('half', 0), 6: ('quarter', 1), 4: ('quarter', 0),
         3: ('eighth', 1), 2: ('eighth', 0), 1: ('16th', 0)}


def _pieces(d: int) -> list[int]:
    """A duration in divisions as notatable values, longest first."""
    out = []
    for v in sorted(TYPES, reverse=True):
        while d >= v:
            out.append(v)
            d -= v
    return out


def _beams(notes: list[Note]) -> dict[Fraction, list[tuple[int, str]]]:
    """Beams for notes shorter than a beat that share a beat: (level, begin/continue/end/backward hook)."""
    groups: dict[int, list[Note]] = {}
    for n in notes:
        beat = int(n.onset)
        if n.dur < 1 and n.onset + n.dur <= beat + 1:
            groups.setdefault(beat, []).append(n)
    out: dict[Fraction, list[tuple[int, str]]] = {}
    for group in groups.values():
        if len(group) < 2:
            continue
        for i, n in enumerate(group):
            level1 = 'begin' if i == 0 else 'end' if i == len(group) - 1 else 'continue'
            out[n.onset] = [(1, level1)]
            if n.dur <= Fraction(1, 4):
                out[n.onset].append((2, 'backward hook' if i else 'forward hook'))
    return out


def musicxml(notes: list[Note], key: Key, beats_per_bar: int, pickup: Fraction, bpm: int, title: str, beat_type: int = 4) -> str:
    """`beats_per_bar` and `beat_type` are the time signature (3 and 2 for 3/2)."""
    bar = beats_per_bar * DIV * 4 // beat_type
    pick = int(pickup * DIV)
    # Bar boundaries in divisions.
    end = int((notes[-1].onset + notes[-1].dur) * DIV)
    bounds = [0] + ([pick] if pick else [])
    while bounds[-1] < end:
        bounds.append(bounds[-1] + bar)
    bars: list[list[str]] = [[] for _ in range(len(bounds) - 1)]

    def bar_of(pos: int) -> int:
        return max(i for i, b in enumerate(bounds[:-1]) if b <= pos)

    beams = _beams(notes)
    # Accidentals: a note shows one when its alteration differs from the key
    # signature or from an earlier note on the same line and space in the bar.
    sig = {s: (1 if key.fifths > 0 and s in 'FCGDAEB'[:key.fifths] else -1 if key.fifths < 0 and s in 'BEADGCF'[:-key.fifths] else 0) for s in 'ABCDEFG'}
    held: dict[tuple[int, str, int], int] = {}  # (bar, step, octave) → alteration in force
    signs = {-1: 'flat', 0: 'natural', 1: 'sharp'}

    for note in notes:
        pos, rest = int(note.onset * DIV), int(note.dur * DIV)
        parts: list[tuple[int, int]] = []
        while rest > 0:
            b = bar_of(pos)
            room = min(rest, bounds[b + 1] - pos)
            for v in _pieces(room):
                parts.append((pos, v))
                pos += v
            rest -= room
        step, alter, octave = key.spell(note.midi)
        for i, (p, v) in enumerate(parts):
            kind, dots = TYPES[v]
            tie = ([('stop')] if i else []) + (['start'] if i + 1 < len(parts) else [])
            xml = ['<note>', f'<pitch><step>{step}</step>' + (f'<alter>{alter}</alter>' if alter else '') + f'<octave>{octave}</octave></pitch>',
                   f'<duration>{v}</duration>']
            xml += [f'<tie type="{x}"/>' for x in tie]
            xml += [f'<type>{kind}</type>'] + ['<dot/>'] * dots
            spot = (bar_of(p), step, octave)
            if i == 0 and held.get(spot, sig[step]) != alter:
                xml.append(f'<accidental>{signs[alter]}</accidental>')
            held[spot] = alter
            xml += [f'<beam number="{k}">{b}</beam>' for k, b in beams.get(note.onset, [])] if len(parts) == 1 else []
            if tie:
                xml.append('<notations>' + ''.join(f'<tied type="{x}"/>' for x in tie) + '</notations>')
            xml.append('</note>')
            bars[bar_of(p)].append(''.join(xml))

    mode = 'minor' if key.minor else 'major'
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">',
           '<score-partwise version="4.0">',
           f'<work><work-title>{title}</work-title></work>',
           '<part-list><score-part id="P1"><part-name print-object="no">Melody</part-name></score-part></part-list>',
           '<part id="P1">']
    for i, content in enumerate(bars):
        first = i == 0
        number = i if pick else i + 1
        attrs = ' implicit="yes"' if pick and first else ''
        out.append(f'<measure number="{number}"{attrs}>')
        if first:
            out.append(f'<attributes><divisions>{DIV}</divisions><key><fifths>{key.fifths}</fifths><mode>{mode}</mode></key>'
                       f'<time><beats>{beats_per_bar}</beats><beat-type>{beat_type}</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>')
            out.append(f'<sound tempo="{bpm}"/>')
        out.extend(content)
        if i == len(bars) - 1:
            out.append('<barline location="right"><bar-style>light-heavy</bar-style></barline>')
        out.append('</measure>')
    out += ['</part>', '</score-partwise>', '']
    return '\n'.join(out)
