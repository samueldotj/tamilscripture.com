"""The words a narrator speaks, from a built chapter JSON (docs/feature_audio_tool.md §5).

Everything here is plain Python so it is tested in CI; romanisation (uroman)
is passed in as a function by the aligner.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable

from . import tamil_numbers

# Headings that are spoken, when a recording reads headings at all; references (r, mr, sr) never are.
SPOKEN_HEADINGS = {'s', 's1', 's2', 's3', 'ms', 'ms1', 'ms2', 'qa', 'sp', 'd'}
MARKS = re.compile(r'[¶\[\](){}<>/\\|*_#@~^`"“”‘’«»‹›…—–]')
NUMBER = re.compile(r'(\d[\d,]*\d|\d)')


@dataclass
class Word:
    text: str  # romanised, filtered to the model's vocabulary
    verse: int | None  # None for a heading word
    heading: bool = False
    mid: bool = False  # a heading word after verse 1 (the probe's evidence)
    number: bool = False  # spelled from digits: aligned, but left out of scores (the model is unsure of them)


@dataclass
class Transcript:
    words: list[Word] = field(default_factory=list)
    verses: list[int] = field(default_factory=list)  # every verse in reading order, even one left without words
    bridges: set[int] = field(default_factory=set)  # first verse of each bridge (\\v 17-18)
    worded: set[int] = field(default_factory=set)  # verses with at least one spoken word
    mid_headings: int = 0  # heading words after verse 1, for the probe


ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
TENS = 'zero ten twenty thirty forty fifty sixty seventy eighty ninety'.split()
ORDINAL = {'one': 'first', 'two': 'second', 'three': 'third', 'five': 'fifth', 'eight': 'eighth', 'nine': 'ninth', 'twelve': 'twelfth'}


def english_cardinal(n: int) -> str:
    """0 to 999,999,999 in words, the way a narrator says it (no "and")."""
    if n < 20:
        return ONES[n]
    if n < 100:
        t, u = divmod(n, 10)
        return TENS[t] + (f' {ONES[u]}' if u else '')
    for size, name in ((1_000_000, 'million'), (1000, 'thousand'), (100, 'hundred')):
        if n >= size:
            q, r = divmod(n, size)
            return f'{english_cardinal(q)} {name}' + (f' {english_cardinal(r)}' if r else '')
    raise ValueError(n)


def english_number(token: str) -> str:
    m = re.fullmatch(r'(\d+)(st|nd|rd|th)', token)
    words = english_cardinal(int((m.group(1) if m else token).replace(',', '')))
    if not m:
        return words
    head, _, last = words.rpartition(' ')
    last = ORDINAL.get(last) or (last[:-1] + 'ieth' if last.endswith('y') else last + 'th')
    return f'{head} {last}'.strip()


def spell_numbers(word: str, lang: str) -> str:
    """Digits to words, keeping any attached suffix: `12-ல்` → பன்னிரண்டு ல்."""
    if not re.search(r'\d', word):
        return word
    if lang == 'eng':
        m = re.fullmatch(r'(\d[\d,]*)(st|nd|rd|th)?(\W*)', word)
        if m:
            return english_number(m.group(1) + (m.group(2) or ''))
    return NUMBER.sub(lambda m: ' ' + tamil_numbers.spell(int(m.group(1).replace(',', ''))) + ' ', word).replace('-', ' ')


def clean(text: str) -> str:
    text = unicodedata.normalize('NFC', text).replace('‌', '').replace('‍', '')
    return MARKS.sub(' ', text)


def spoken_words(text: str, lang: str, romanize: Callable[[str], str], vocab: set[str]) -> list[tuple[str, bool]]:
    """(word, spelled from digits) for each spoken word, romanised and reduced to characters the model knows."""
    out = []
    for raw in clean(text).split():
        digits = bool(re.search(r'\d', raw))
        for w in spell_numbers(raw, lang).split():
            r = ''.join(c for c in romanize(w).lower() if c in vocab)
            if r:
                out.append((r, digits))
    return out


def words_of(text: str, lang: str, romanize: Callable[[str], str], vocab: set[str]) -> list[str]:
    return [w for w, _ in spoken_words(text, lang, romanize, vocab)]


def transcript(chapter: dict, lang: str, romanize: Callable[[str], str], vocab: set[str], headings: bool) -> Transcript:
    """The chapter's words in reading order, each tagged with its verse."""
    t = Transcript()
    seen: set[int] = set()
    started = False
    for block in chapter['blocks']:
        if block['type'] == 'heading':
            kind = block.get('kind', 's')
            if kind in SPOKEN_HEADINGS:
                ws = words_of(block['text'], lang, romanize, vocab)
                if started:
                    t.mid_headings += len(ws)
                if headings:
                    t.words += [Word(w, None, True, started) for w in ws]
            continue
        if block['type'] != 'para':
            continue
        for seg in block['segments']:
            if not seg.get('id'):
                continue
            n = int(seg['id'].split('.')[2])
            started = True
            if n not in seen:
                seen.add(n)
                t.verses.append(n)
                if '-' in (seg.get('n') or ''):
                    t.bridges.add(n)
            ws = spoken_words(seg['text'], lang, romanize, vocab)
            if ws:
                t.worded.add(n)
            t.words += [Word(w, n, number=num) for w, num in ws]
    return t


def verse_starts(first: dict[int, float], last: dict[int, float], order: list[int], duration: float) -> dict[int, tuple[float, float]]:
    """(start, end) in seconds per verse: the start sits in the pause before the
    verse's first word, never more than 0.3 s early; a verse without words takes
    the next verse's start. `first` and `last` are word start and end times."""
    starts: dict[int, float] = {}
    prev_end: float | None = None
    for n in order:
        if n not in first:
            continue
        b = first[n]
        a = prev_end if prev_end is not None else max(0.0, b - 0.6)
        starts[n] = max((a + b) / 2, b - 0.3)
        prev_end = last[n]
    # Wordless verses borrow the next timed verse's start.
    upcoming: float | None = None
    for n in reversed(order):
        if n in starts:
            upcoming = starts[n]
        elif upcoming is not None:
            starts[n] = upcoming
    out = {}
    timed = [n for n in order if n in starts]
    for i, n in enumerate(timed):
        nxt = next((starts[m] for m in timed[i + 1:] if starts[m] > starts[n]), None)
        end = nxt if nxt is not None else min(duration, last.get(n, starts[n]) + 0.3)
        out[n] = (starts[n], end)
    return out
