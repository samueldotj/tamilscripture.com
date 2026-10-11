"""Notation, note timings and audio for one tune (docs/feature_psalms_explorer.md §8).

incipit.svg  the first line on one staff, as the explorer's card shows it
full.svg     the whole tune, wrapped to a 600 px column
*.draw.json  the same two drawings reduced to glyphs and paths, for the app
events.json  every note: when it sounds, its pitch, and where its head is in
             each SVG as a fraction of the drawing's width and height; and when
             each line of a stanza starts, for the card to light the line sung
audio.mp3    one stanza on organ, in four parts: the source MIDI (sources/{id}.mid)
             played at the tune's tempo on FluidR3_GM's Church Organ by FluidSynth,
             then encoded by ffmpeg. The card repeats it for every stanza.
render.json  the SHA-256 of the MusicXML and the MIDI, and the tool versions;
             entity-ingest refuses a render whose sources have changed

Everything is deterministic: Verovio ids come from a fixed seed, FluidSynth renders
the same bytes every time and ffmpeg runs with bitexact flags.

FluidSynth and the SoundFont are found in tools/psalter/.cache/ (README: Setup), or
through the FLUIDSYNTH and SOUNDFONT environment variables.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import wave
from pathlib import Path

import os

import mido
import numpy as np
import verovio

from .infer import slots as syllable_slots

TOOL_VERSION = '0.3.0'
CACHE = Path(__file__).resolve().parents[2] / '.cache'
CHURCH_ORGAN = 19  # General MIDI program 20, zero-based


def _toolkit(width: int, breaks: str) -> verovio.toolkit:
    tk = verovio.toolkit()
    tk.setOptions({
        'pageWidth': width, 'adjustPageHeight': True, 'breaks': breaks, 'scale': 40,
        'header': 'none', 'footer': 'none', 'svgViewBox': True, 'svgFormatRaw': True,
        'svgRemoveXlink': True, 'xmlIdSeed': 1,
        # Wider than Verovio's default, so the words written under the notes have room.
        'spacingLinear': 0.42,
        # The bottom margin leaves room under the last staff for the words the card writes there.
        'pageMarginLeft': 20, 'pageMarginRight': 20, 'pageMarginTop': 0, 'pageMarginBottom': 40,
    })
    return tk


def lyric_baselines(svg: str) -> dict[str, float]:
    """For every note, where the words go under its staff, as a fraction of the drawing's
    height: below the staff's bottom line and below its lowest note, the same for every
    note of the staff so that a line of words reads level."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(svg)
    inner = next(e for e in root.iter(f'{_SVG}svg') if e.get('class') == 'definition-scale')
    h = float(inner.get('viewBox').split()[3])
    out: dict[str, float] = {}

    def walk(el: ET.Element, m: list[float]) -> None:
        m = _mul(m, _matrix(el.get('transform')))
        if el.tag == f'{_SVG}g' and el.get('class') == 'staff':
            lines = [m[5] + m[3] * float(p.get('d').split()[1]) for p in el.findall(f'{_SVG}path') if re.match(r'M[-\d.]+ [-\d.]+ L', p.get('d', ''))]
            heads: dict[str, float] = {}
            for note in el.iter(f'{_SVG}g'):
                if note.get('class') != 'note':
                    continue
                use = note.find(f".//{_SVG}g[@class='notehead']/{_SVG}use")
                if use is not None:
                    t = re.search(r'translate\(([-\d.]+), ([-\d.]+)\)', use.get('transform', ''))
                    heads[note.get('id')] = m[5] + m[3] * float(t.group(2))
            if lines and heads:
                y = max(max(lines) + 560, max(heads.values()) + 400)
                for nid in heads:
                    out[nid] = round(y / h, 4)
            return
        for child in el:
            walk(child, m)

    for child in inner:
        walk(child, [1, 0, 0, 1, 0, 0])
    return out


def first_line(xml: str, line_beats: int, pickup: int, beats_per_bar: int) -> str:
    """The MusicXML cut after the first line: whole bars up to `line_beats`, the
    last one ending where the line ends (the next line's pickup dropped)."""
    measures = re.findall(r'<measure .*?</measure>', xml, flags=re.S)
    keep, beats = [], 0
    for i, m in enumerate(measures):
        if beats >= line_beats:
            break
        size = pickup if (pickup and i == 0) else beats_per_bar
        if beats + size > line_beats:
            # Drop the notes that belong to the next line.
            room = (line_beats - beats) * 4
            notes = re.findall(r'<note>.*?</note>', m, flags=re.S)
            kept, used = [], 0
            for n in notes:
                d = int(re.search(r'<duration>(\d+)</duration>', n).group(1))
                if used + d > room:
                    break
                kept.append(n)
                used += d
            head = m[:m.index('<note>')]
            m = head + ''.join(kept) + '</measure>'
        m = re.sub(r'<barline .*?</barline>', '', m, flags=re.S)
        keep.append(m)
        beats += size
    keep[-1] = keep[-1].replace('</measure>', '<barline location="right"><bar-style>light-light</bar-style></barline></measure>')
    start = xml.index('<measure ')
    end = xml.rindex('</measure>') + len('</measure>')
    return xml[:start] + '\n'.join(keep) + xml[end:]


def _svg(tk: verovio.toolkit, xml: str) -> tuple[str, dict[str, tuple[float, float]], list[dict]]:
    if not tk.loadData(xml):
        raise ValueError('Verovio could not read the MusicXML')
    svg = tk.renderToSVG(1)
    # The theme's ink, not black: the page or app sets `color`.
    svg = svg.replace('color="black"', 'color="currentColor" fill="currentColor"')
    vb = re.search(r'class="definition-scale"[^>]*viewBox="0 0 (\d+) (\d+)"', svg)
    w, h = int(vb.group(1)), int(vb.group(2))
    heads: dict[str, tuple[float, float]] = {}
    for m in re.finditer(r'<g id="([^"]+)" class="note"[^>]*>.*?class="notehead"[^>]*>\s*<use [^>]*transform="translate\(([-\d.]+), ([-\d.]+)\)', svg, flags=re.S):
        heads[m.group(1)] = (round(float(m.group(2)) / w, 4), round(float(m.group(3)) / h, 4))
    return svg, heads, tk.renderToTimemap()


_SVG = '{http://www.w3.org/2000/svg}'
_NUM = r'-?[\d.]+(?:e-?\d+)?'


def _matrix(transform: str | None) -> list[float]:
    """An SVG transform of translate() and scale() as [a, b, c, d, e, f]."""
    m = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    for fn, args in re.findall(r'(translate|scale)\(([^)]*)\)', transform or ''):
        v = [float(x) for x in re.findall(_NUM, args)]
        if fn == 'translate':
            tx, ty = v[0], v[1] if len(v) > 1 else 0.0
            m = [m[0], m[1], m[2], m[3], m[0] * tx + m[2] * ty + m[4], m[1] * tx + m[3] * ty + m[5]]
        else:
            sx, sy = v[0], v[1] if len(v) > 1 else v[0]
            m = [m[0] * sx, m[1] * sx, m[2] * sy, m[3] * sy, m[4], m[5]]
    return m


def _mul(p: list[float], q: list[float]) -> list[float]:
    return [p[0] * q[0] + p[2] * q[1], p[1] * q[0] + p[3] * q[1], p[0] * q[2] + p[2] * q[3],
            p[1] * q[2] + p[3] * q[3], p[0] * q[4] + p[2] * q[5] + p[4], p[1] * q[4] + p[3] * q[5] + p[5]]


def drawing(svg: str) -> dict:
    """The SVG reduced to what the app draws (core/model PsalterDrawing): glyph outlines
    once, then every mark as a glyph or a path with its matrix and stroke width. Marks
    inside a note are tagged with its id so the app can colour the sounding note."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(svg)
    glyphs: dict[str, str] = {}
    for g in root.iter(f'{_SVG}g'):
        gid = g.get('id', '')
        p = g.find(f'{_SVG}path')
        if gid[:1] == 'E' and '-' in gid and p is not None:
            glyphs[gid.split('-')[0]] = p.get('d')
    inner = next(e for e in root.iter(f'{_SVG}svg') if e.get('class') == 'definition-scale')
    w, h = (float(x) for x in inner.get('viewBox').split()[2:])
    items: list[dict] = []

    def r(m: list[float]) -> list[float]:
        return [round(x, 3) for x in m]

    def walk(el: ET.Element, m: list[float], note: str | None) -> None:
        tag = el.tag.removeprefix(_SVG)
        if tag in ('text', 'desc', 'style', 'defs'):
            return
        mm = _mul(m, _matrix(el.get('transform')))
        if tag == 'g' and el.get('class') == 'note':
            note = el.get('id')
        item = None
        if tag == 'use':
            item = {'g': (el.get('href') or el.get('{http://www.w3.org/1999/xlink}href')).lstrip('#').split('-')[0], 'm': r(_mul(mm, [1, 0, 0, -1, 0, 0]))}
        elif tag == 'path':
            item = {'d': el.get('d'), 'm': r(mm)}
            if el.get('stroke-width'):
                item['s'] = float(el.get('stroke-width'))
        elif tag == 'polygon':
            pts = re.findall(_NUM, el.get('points'))
            d = 'M' + ' L'.join(f'{pts[i]} {pts[i + 1]}' for i in range(0, len(pts), 2)) + ' Z'
            item = {'d': d, 'm': r(mm)}
        elif tag == 'ellipse':
            cx, cy, rx, ry = (float(el.get(k)) for k in ('cx', 'cy', 'rx', 'ry'))
            d = f'M{cx - rx} {cy} a{rx} {ry} 0 1 0 {2 * rx} 0 a{rx} {ry} 0 1 0 {-2 * rx} 0 Z'
            item = {'d': d, 'm': r(mm)}
        if item is not None:
            if note:
                item['n'] = note
            items.append(item)
        for child in el:
            walk(child, mm, note)

    for child in inner:
        walk(child, [1, 0, 0, 1, 0, 0], None)
    # Glyph outlines are drawn upside down (scale(1,-1) in the SVG): folded into each use's matrix above.
    used = {i['g'] for i in items if 'g' in i}
    return {'w': w, 'h': h, 'glyphs': {k: v for k, v in sorted(glyphs.items()) if k in used}, 'items': items}


def _events(tk: verovio.toolkit, timemap: list[dict], bpm: int) -> list[dict]:
    """Note ids in sounding order with on/off times (ms, from the quarter-note stamps) and MIDI pitch."""
    starts: dict[str, float] = {}
    out = []
    for entry in timemap:
        q = entry['qstamp']
        for nid in entry.get('on', []):
            starts[nid] = q
        for nid in entry.get('off', []):
            if nid in starts:
                out.append({'id': nid, 'q0': starts.pop(nid), 'q1': q, 'midi': tk.getMIDIValuesForElement(nid)['pitch']})
    out.sort(key=lambda e: e['q0'])
    ms = 60000 / bpm
    return [{'id': e['id'], 'on': round(e['q0'] * ms), 'off': round(e['q1'] * ms), 'midi': e['midi']} for e in out]


def _tool(env: str, *candidates: Path) -> Path:
    if os.environ.get(env):
        return Path(os.environ[env])
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f'{env} not found: set it or unpack it into {CACHE} (tools/psalter/README.md)')


def fluidsynth() -> Path:
    return _tool('FLUIDSYNTH', *sorted(CACHE.glob('fluidsynth/*/bin/fluidsynth.exe')), *sorted(CACHE.glob('fluidsynth/*/bin/fluidsynth')))


def soundfont() -> Path:
    return _tool('SOUNDFONT', CACHE / 'FluidR3_GM.sf2')


def organ_midi(src: Path, bpm: int, dst: Path) -> None:
    """The source MIDI's notes, all four parts, at `bpm` on the Church Organ. Ticks are
    kept, so the audio lines up with the notation's timings to the millisecond."""
    mid = mido.MidiFile(str(src))
    out = mido.MidiFile(type=1, ticks_per_beat=mid.ticks_per_beat)
    head = mido.MidiTrack([mido.MetaMessage('set_tempo', tempo=round(60_000_000 / bpm), time=0)])
    out.tracks.append(head)
    channels: set[int] = set()
    for track in mid.tracks[1:]:
        t, carry = mido.MidiTrack(), 0
        for m in track:
            if m.type in ('note_on', 'note_off'):
                channels.add(m.channel)
                t.append(m.copy(time=m.time + carry))
                carry = 0
            else:
                carry += m.time
        out.tracks.append(t)
    for ch in sorted(channels):
        head.append(mido.Message('program_change', channel=ch, program=CHURCH_ORGAN, time=0))
    out.save(str(dst))


def organ_mp3(src: Path, bpm: int, path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        midi, wav = Path(tmp) / 'organ.mid', Path(tmp) / 'organ.wav'
        organ_midi(src, bpm, midi)
        subprocess.run([str(fluidsynth()), '-ni', '-g', '0.6', '-r', '44100', '-F', str(wav), str(soundfont()), str(midi)],
                       check=True, capture_output=True)
        # Even loudness from tune to tune: the peak at -1 dBFS.
        with wave.open(str(wav)) as w:
            rate, ch = w.getframerate(), w.getnchannels()
            a = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64)
        a = a / max(1.0, np.abs(a).max()) * 0.89 * 32767
        with wave.open(str(wav), 'wb') as w:
            w.setnchannels(ch)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(a.astype('<i2').tobytes())
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(wav), '-map_metadata', '-1', '-fflags', '+bitexact',
                        '-flags:a', '+bitexact', '-ac', '1', '-ar', '44100', '-codec:a', 'libmp3lame', '-b:a', '48k', str(path)], check=True)


def render(xml_path: Path, midi_path: Path, out: Path, tune: dict, beats_per_bar: int) -> dict:
    xml = xml_path.read_text(encoding='utf-8')
    out.mkdir(parents=True, exist_ok=True)

    full_tk = _toolkit(1500, 'auto')
    full_svg, full_heads, timemap = _svg(full_tk, xml)
    events = _events(full_tk, timemap, tune['bpm'])

    line = first_line(xml, tune['line_beats'], tune['pickup'], beats_per_bar)
    inc_tk = _toolkit(4000, 'none')
    inc_svg, inc_heads, inc_map = _svg(inc_tk, line)
    inc_ids = [e['id'] for e in _events(inc_tk, inc_map, tune['bpm'])]

    # Notes pair up by order: the incipit is the first notes of the tune. Each drawing gives
    # [x, y, id, lyric baseline], positions as fractions of the drawing.
    full_ly, inc_ly = lyric_baselines(full_svg), lyric_baselines(inc_svg)
    notes = []
    for i, e in enumerate(events):
        n = {'on': e['on'], 'off': e['off'], 'midi': e['midi'], 'full': [*full_heads.get(e['id'], (None, None)), e['id'], full_ly.get(e['id'])]}
        if i < len(inc_ids):
            n['incipit'] = [*inc_heads.get(inc_ids[i], (None, None)), inc_ids[i], inc_ly.get(inc_ids[i])]
        notes.append(n)
    (out / 'incipit.svg').write_text(inc_svg, encoding='utf-8', newline='\n')
    (out / 'full.svg').write_text(full_svg, encoding='utf-8', newline='\n')
    for name, svg in (('incipit', inc_svg), ('full', full_svg)):
        (out / f'{name}.draw.json').write_text(json.dumps(drawing(svg), separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    slots = syllable_slots(events, tune['meter'], tune['bpm'])
    lines = [events[line[0]]['on'] for line in slots if line]
    body = {'duration': events[-1]['off'], 'bpm': tune['bpm'], 'incipit_notes': len(inc_ids), 'lines': lines, 'slots': slots, 'notes': notes}
    (out / 'events.json').write_text(json.dumps(body, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    organ_mp3(midi_path, tune['bpm'], out / 'audio.mp3')
    meta = {'source_sha256': hashlib.sha256(xml_path.read_bytes()).hexdigest(), 'midi_sha256': hashlib.sha256(midi_path.read_bytes()).hexdigest(),
            'verovio': verovio.toolkit().getVersion().split('[')[0], 'soundfont': 'FluidR3_GM (Church Organ)', 'tool': TOOL_VERSION}
    (out / 'render.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8', newline='\n')
    return meta
