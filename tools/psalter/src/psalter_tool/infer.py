"""Guesses for a new tune's settings, from its melody: the pickup, the tonic and mode, and
where the first line ends. `psalter import --infer` uses them when tunes.toml leaves them
out; review them by eye before trusting the bar lines.
"""
from __future__ import annotations

from fractions import Fraction

from .melody import Key, Note, incipit_digits

MAJOR_FIFTHS = {0: 'C', 7: 'G', 2: 'D', 9: 'A', 4: 'E', 11: 'B', 5: 'F', 10: 'B-flat', 3: 'E-flat', 8: 'A-flat', 1: 'D-flat', 6: 'F-sharp'}
MINOR_OF = {0: 'A', 7: 'E', 2: 'B', 9: 'F-sharp', 4: 'C-sharp', 5: 'D', 10: 'G', 3: 'C', 8: 'F'}


def key_for(sig_tonic: int, notes: list[Note], incipit: str) -> str:
    """The major key of the signature or its relative minor: whichever the incipit fits.
    A tie goes to the mode whose tonic the tune ends on."""
    want = incipit.replace(' ', '').rstrip('_').replace('_', '')
    major = f'{MAJOR_FIFTHS[sig_tonic]} major'
    minor = f'{MINOR_OF.get(sig_tonic, "A")} minor'
    scores = []
    for name in (major, minor):
        got = incipit_digits(notes, Key.parse(name), len(want))
        scores.append((sum(a == b for a, b in zip(got, want)), Key.parse(name).tonic == notes[-1].midi % 12, name))
    return max(scores)[2]


def pickup(notes: list[Note], beats_per_bar: int) -> Fraction:
    """The anacrusis that puts the most weight on downbeats: long notes start bars in
    psalm tunes. Ties (a tune in equal notes) go to the shortest pickup."""
    best: tuple[Fraction, Fraction] | None = None
    for p in range(beats_per_bar):
        score = Fraction(0)
        for n in notes:
            pos = (n.onset - p) % beats_per_bar
            if pos == 0:
                score += n.dur * 2
            elif beats_per_bar == 4 and pos == 2:
                score += n.dur
        if best is None or score > best[0]:
            best = (score, Fraction(p))
    return best[1]


def line_beats(notes: list[Note], syllables: int) -> int:
    """Beats from the start to the end of the first line: `syllables` sung notes, where the
    short notes sharing a beat are one syllable."""
    sung, i = 0, 0
    while i < len(notes) and sung < syllables:
        n = notes[i]
        if n.dur < 1:
            beat = int(n.onset)
            while i + 1 < len(notes) and int(notes[i + 1].onset) == beat and notes[i + 1].dur < 1:
                i += 1
        sung += 1
        i += 1
    # A line that stops on a short note usually closes on the long note just after it.
    if notes[i - 1].dur < 2 and i < len(notes) and notes[i].dur >= 2:
        i += 1
    last = notes[i - 1]
    return int(last.onset + last.dur + Fraction(1, 2))


METRES = {'C.M.': '8.6.8.6', 'L.M.': '8.8.8.8', 'S.M.': '6.6.8.6', 'C.M.D.': '8.6.8.6.8.6.8.6',
          'L.M.D.': '8.8.8.8.8.8.8.8', 'S.M.D.': '6.6.8.6.6.6.8.6'}


def lines(events: list[dict], meter: str, bpm: int) -> list[int]:
    """Indices of the notes that start each line of a stanza (events in ms, as render
    writes them), from the metre's syllables per line, by the same rules as line_beats."""
    pattern = METRES.get(meter, meter)
    counts = [int(x) for x in pattern.split('.') if x.isdigit()]
    if pattern.endswith('.D'):
        counts *= 2
    beat = 60000 / bpm

    def short(e: dict, beats: float = 1) -> bool:
        return e['off'] - e['on'] < beat * beats * 0.99

    starts, i = [], 0
    for li, count in enumerate(counts):
        if i >= len(events):
            break
        starts.append(i)
        sung = 0
        while i < len(events) and sung < count:
            if short(events[i]):
                b = int(events[i]['on'] // beat)
                while i + 1 < len(events) and int(events[i + 1]['on'] // beat) == b and short(events[i + 1]):
                    i += 1
            sung += 1
            i += 1
        if li + 1 < len(counts) and i < len(events) and short(events[i - 1], 2) and not short(events[i], 2):
            i += 1
    return starts
