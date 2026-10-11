#!/usr/bin/env python3
"""Draft data/psalter/scottish-1650/ from CCEL's Scottish Psalter (ThML).

The source is "Scottish Psalter and Paraphrases", Christian Classics Ethereal Library,
https://www.ccel.org/ccel/a/anonymous/scotpsalter.xml (DC.Rights: Public Domain), itself
from The Psalms and Church Hymnary (1973). Only the 1650 Psalms of David in Metre are
taken, not the 1781 Paraphrases. Writes one TOML per psalm (Psalm 119 holds its 22 parts),
with each version's metre and its stanzas; a scripture verse starts where a line carries
a superscript number, and an indented line starts with two spaces.

Syllables are counted line by line against the metre and the lines that differ are
listed. The count is a heuristic (English spelling, the psalter's elisions such as
"heav'n" and "pow'r"), so a listed line is a line to look at, not an error.

Refuses to overwrite files that exist (they may hold corrections) unless --force.

  python scripts/import-scottish-psalter.py scotpsalter.xml
"""
import html
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / 'data' / 'psalter' / 'scottish-1650'
SUP = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
LABELS = {'8.6.8.6': 'C.M.', '8.8.8.8': 'L.M.', '6.6.8.6': 'S.M.'}


def text_of(fragment: str) -> str:
    fragment = re.sub(r'<small[^>]*><sup[^>]*>(\d+)</sup></small>', lambda m: m.group(1).translate(SUP), fragment)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', fragment))).strip()


def syllables(line: str) -> int:
    """English syllables, roughly: vowel groups, less a silent final e, with the
    psalter's apostrophe elisions already removing letters."""
    n = 0
    for w in re.findall(r"[A-Za-z’']+", line.lower().translate(str.maketrans('', '', '⁰¹²³⁴⁵⁶⁷⁸⁹'))):
        w = w.replace('’', "'")
        bare = w.replace("'", '')
        c = 0
        for g in re.finditer(r'[aeiouy]+', bare):
            c += 1
            # Two vowels sung apart: li-on, qui-et, cru-el, per-pet-u-al, Is-ra-el, do-er
            # (not the -ion of -tion, counted below, nor the u of qu- and gu-).
            if (re.fullmatch(r'i[aoe]|u[ae]|oe|ae', g.group()) and bare[g.end():] not in ('n', 'ns', 's', 'e')
                    and not (g.group()[0] == 'u' and bare[g.start() - 1:g.start()] in ('q', 'g'))
                    and not bare.endswith(('tion', 'sion', 'tions', 'sions'))):
                c += 1
        # A silent e, also before s ("make", "makes"), but not in "able" or "graces".
        if re.search(r'[^aeiouy]es?$', w) and not re.search(r'(le|[cgsxz]es)$', w) and c > 1:
            c -= 1
        # The psalter elides with an apostrophe ("sham'd"), so a written -ed is sung
        # ("vex-ed"); and -tion, -sion are often two syllables ("in-dig-na-ti-on").
        if re.search(r'[st]ions?$', w):
            c += 1
        n += max(1, c)
    return n


def toml_str(s: str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    xml = Path(args[0]).read_text(encoding='utf-8')
    xml = xml[xml.index('id="psalter"'):]
    xml = xml[:xml.find('<div1', 10)] if '<div1' in xml[10:] else xml
    hymns = re.findall(r'<div2 class="hymn" title="([^"]+)".*?</div2>', xml, flags=re.S)
    bodies = re.findall(r'<div2 class="hymn" title="[^"]+".*?</div2>', xml, flags=re.S)
    psalms: dict[int, list[dict]] = {}
    odd: list[str] = []
    for title, body in zip(hymns, bodies):
        title = html.unescape(title)
        # "Psalm 6, L.M.: Lord, in thy wrath…", "Psalm 119, Part 4: …"; a colon inside the
        # first line ("Praise ye the Lord: …") is not a label.
        m = re.match(r'Psalm (\d+)(?:, Part (\d+))?[,:]?\s*(?:([CLS]\.M\.|10s|[\d.]+D?\.?):)?\s*(.*)$', title)
        if not m:
            continue
        n, part, label = int(m.group(1)), m.group(2), (m.group(3) or '').strip()
        meter = re.search(r'<meter standard="([^"]+)"', body).group(1).rstrip('.')
        if label.rstrip('.').endswith('.D'):
            meter += '.D'  # a doubled metre: the metre element gives only the half
            label = label.rstrip('.')
        elif re.fullmatch(r'[\d.]+', label):
            label = meter  # a numeric label in the title: the metre element is the reliable one
        arg = re.search(r'<argument[^>]*>(.*?)</argument>', body, flags=re.S)
        stanzas = []
        for verse in re.findall(r'<verse[^>]*>(.*?)</verse>', body, flags=re.S):
            lines = []
            for cls, l in re.findall(r'<l(?: class="([^"]*)")?[^>]*>(.*?)</l>', verse, flags=re.S):
                t = text_of(l)
                lines.append(('  ' if cls and cls.startswith('t') else '') + t)
            # Long lines printed in halves (Psalm 124's 10s): join each pair.
            pattern = [x for x in meter.split('.') if x.isdigit()]
            if pattern and len(lines) == 2 * len(pattern) and all(int(x) >= 10 for x in pattern):
                lines = [f'{lines[i].strip()} {lines[i + 1].strip()}' for i in range(0, len(lines), 2)]
            stanzas.append(lines)
        psalms.setdefault(n, []).append({
            'part': int(part) if part else None, 'label': label, 'meter': meter,
            'argument': text_of(arg.group(1)) if arg else '', 'stanzas': stanzas,
        })
        pattern = [int(x) for x in meter.replace('D', '').split('.') if x]
        for si, st in enumerate(stanzas):
            for li, line in enumerate(st):
                want = pattern[li % len(pattern)] if pattern else 0
                got = syllables(line)
                # One extra syllable is the psalter's feminine ending ("by a river").
                if want and got not in (want, want + 1):
                    odd.append(f'Psalm {n}{f" part {part}" if part else ""}{f" ({label})" if label else ""} stanza {si + 1} line {li + 1}: {got} for {want}: {line.strip()}')

    if sorted(psalms) != list(range(1, 151)):
        sys.exit(f'expected psalms 1-150, found {len(psalms)}')
    OUT.mkdir(parents=True, exist_ok=True)
    written = 0
    for n, versions in sorted(psalms.items()):
        path = OUT / f'psalm-{n:03}.toml'
        if path.exists() and '--force' not in sys.argv:
            continue
        out = [f'# Psalm {n} in the Psalms of David in Metre (Scottish Psalter, 1650).',
               '# From CCEL (public domain): scripts/import-scottish-psalter.py; edit freely.',
               '# A line starting with two spaces is indented; superscript numbers start verses.',
               f'psalm = {n}', '']
        for i, v in enumerate(versions):
            key = f'{n}-{v["part"]}' if v['part'] else (f'{n}' if i == 0 else f'{n}-{i + 1}')
            out.append('[[version]]')
            out.append(f'key = {toml_str(key)}')
            if v['part']:
                out.append(f'part = {v["part"]}')
            out.append(f'label = {toml_str(v["label"] or LABELS.get(v["meter"], ""))}')
            out.append(f'meter = {toml_str(v["meter"])}')
            if v['argument']:
                out.append(f'argument = {toml_str(v["argument"])}')
            out.append('stanzas = [')
            for st in v['stanzas']:
                out.append('  [' + ', '.join(toml_str(l) for l in st) + '],')
            out.append(']')
            out.append('')
        path.write_text('\n'.join(out), encoding='utf-8', newline='\n')
        written += 1
    stanzas = sum(len(v['stanzas']) for vs in psalms.values() for v in vs)
    lines = sum(len(st) for vs in psalms.values() for v in vs for st in v['stanzas'])
    print(f'{written} files written to {OUT}; {sum(len(v) for v in psalms.values())} versions, {stanzas} stanzas, {lines} lines')
    print(f'{len(odd)} lines whose syllable count differs from the metre (heuristic):')
    for o in odd[:40]:
        print('  ', o)


if __name__ == '__main__':
    main()
