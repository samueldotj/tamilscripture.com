"""Notation, note timings and audio for one tune (docs/feature_psalms_explorer.md §8).

incipit.svg  the first line on one staff, as the explorer's card shows it
full.svg     the whole tune, wrapped to a 600 px column
*.draw.json  the same two drawings reduced to glyphs and paths, for the app
events.json  every note: when it sounds, its pitch, and where its head is in
             each SVG as a fraction of the drawing's width and height
audio.mp3    the melody, synthesised here (an organ-like tone) and encoded by ffmpeg
render.json  the MusicXML's SHA-256 and the tool versions; entity-ingest refuses
             a render whose hash no longer matches the MusicXML

Everything is deterministic: Verovio ids come from a fixed seed, the synthesis
has no randomness and ffmpeg runs with bitexact flags.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
import verovio

TOOL_VERSION = '0.1.0'
RATE = 22050


def _toolkit(width: int, breaks: str) -> verovio.toolkit:
    tk = verovio.toolkit()
    tk.setOptions({
        'pageWidth': width, 'adjustPageHeight': True, 'breaks': breaks, 'scale': 40,
        'header': 'none', 'footer': 'none', 'svgViewBox': True, 'svgFormatRaw': True,
        'svgRemoveXlink': True, 'xmlIdSeed': 1,
        'pageMarginLeft': 20, 'pageMarginRight': 20, 'pageMarginTop': 0, 'pageMarginBottom': 0,
    })
    return tk


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


def synth(events: list[dict]) -> np.ndarray:
    """A soft organ tone per note: a few harmonics, short attack and release."""
    total = events[-1]['off'] / 1000 + 0.6
    out = np.zeros(int(total * RATE), dtype=np.float64)
    harmonics = [(1, 1.0), (2, 0.45), (3, 0.25), (4, 0.12), (5, 0.06)]
    for e in events:
        f = 440 * 2 ** ((e['midi'] - 69) / 12)
        a, b = e['on'] / 1000, e['off'] / 1000
        n = int((b - a + 0.08) * RATE)
        t = np.arange(n) / RATE
        tone = sum(amp * np.sin(2 * np.pi * f * k * t) for k, amp in harmonics)
        env = np.minimum(1, t / 0.03) * np.clip((b - a + 0.08 - t) / 0.12, 0, 1)
        start = int(a * RATE)
        out[start:start + n] += tone * env
    return out / max(1e-9, np.abs(out).max()) * 0.7


def _mp3(samples: np.ndarray, path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / 'tune.wav'
        with wave.open(str(wav), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes((samples * 32767).astype('<i2').tobytes())
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(wav), '-map_metadata', '-1', '-fflags', '+bitexact',
                        '-flags:a', '+bitexact', '-ac', '1', '-codec:a', 'libmp3lame', '-b:a', '32k', str(path)], check=True)


def render(xml_path: Path, out: Path, tune: dict, beats_per_bar: int) -> dict:
    xml = xml_path.read_text(encoding='utf-8')
    out.mkdir(parents=True, exist_ok=True)

    full_tk = _toolkit(1500, 'auto')
    full_svg, full_heads, timemap = _svg(full_tk, xml)
    events = _events(full_tk, timemap, tune['bpm'])

    line = first_line(xml, tune['line_beats'], tune['pickup'], beats_per_bar)
    inc_tk = _toolkit(4000, 'none')
    inc_svg, inc_heads, inc_map = _svg(inc_tk, line)
    inc_ids = [e['id'] for e in _events(inc_tk, inc_map, tune['bpm'])]

    # Notes pair up by order: the incipit is the first notes of the tune.
    notes = []
    for i, e in enumerate(events):
        n = {'on': e['on'], 'off': e['off'], 'midi': e['midi'], 'full': [*full_heads.get(e['id'], (None, None)), e['id']]}
        if i < len(inc_ids):
            n['incipit'] = [*inc_heads.get(inc_ids[i], (None, None)), inc_ids[i]]
        notes.append(n)
    (out / 'incipit.svg').write_text(inc_svg, encoding='utf-8', newline='\n')
    (out / 'full.svg').write_text(full_svg, encoding='utf-8', newline='\n')
    for name, svg in (('incipit', inc_svg), ('full', full_svg)):
        (out / f'{name}.draw.json').write_text(json.dumps(drawing(svg), separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    (out / 'events.json').write_text(json.dumps({'duration': events[-1]['off'], 'incipit_notes': len(inc_ids), 'notes': notes}, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    _mp3(synth(events), out / 'audio.mp3')
    meta = {'source_sha256': hashlib.sha256(xml_path.read_bytes()).hexdigest(), 'verovio': verovio.toolkit().getVersion().split('[')[0], 'tool': TOOL_VERSION}
    (out / 'render.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8', newline='\n')
    return meta
