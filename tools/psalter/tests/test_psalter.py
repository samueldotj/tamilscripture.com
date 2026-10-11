"""tools/psalter: key arithmetic, MusicXML writing and the committed tunes.

  tools/psalter/.venv/Scripts/python -m pytest tools/psalter/tests   (or: python -m unittest discover tools/psalter/tests)
"""
import hashlib
import json
import re
import tomllib
import unittest
from fractions import Fraction as F
from pathlib import Path

from psalter_tool.melody import Key, Note, _beams, check_incipit, musicxml
from psalter_tool.render import drawing, first_line

ROOT = Path(__file__).resolve().parents[3]
PSALTER = ROOT / 'data' / 'psalter'


class KeyTest(unittest.TestCase):
    def test_parse_and_fifths(self):
        self.assertEqual(Key.parse('G major').fifths, 1)
        self.assertEqual(Key.parse('E-flat major').fifths, -3)
        self.assertEqual(Key.parse('A minor').fifths, 0)
        self.assertEqual(Key.parse('F major').fifths, -1)

    def test_degrees(self):
        f = Key.parse('F major')
        self.assertEqual([f.degree(m) for m in (65, 67, 69, 70, 72, 74, 76)], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(Key.parse('A minor').degree(68), 7)  # G sharp, the raised leading note

    def test_spelling(self):
        self.assertEqual(Key.parse('E-flat major').spell(70), ('B', -1, 4))
        self.assertEqual(Key.parse('G major').spell(66), ('F', 1, 4))


class MusicXmlTest(unittest.TestCase):
    def test_accidentals_once_per_bar(self):
        f = Key.parse('F major')
        notes = [Note(F(0), F(1), 71), Note(F(1), F(1), 71), Note(F(2), F(1), 70), Note(F(3), F(1), 71)]
        xml = musicxml(notes, f, 4, F(0), 84, 'Test')
        self.assertEqual(re.findall(r'<accidental>(\w+)</accidental>', xml), ['natural', 'flat', 'natural'])

    def test_beams_within_a_beat(self):
        notes = [Note(F(0), F(1, 2), 60), Note(F(1, 2), F(1, 2), 62), Note(F(1), F(3, 4), 64), Note(F(7, 4), F(1, 4), 65), Note(F(2), F(1, 2), 67)]
        b = _beams(notes)
        self.assertEqual(b[F(0)], [(1, 'begin')])
        self.assertEqual(b[F(1, 2)], [(1, 'end')])
        self.assertEqual(b[F(7, 4)], [(1, 'end'), (2, 'backward hook')])
        self.assertNotIn(F(2), b)  # alone in its beat: a flag

    def test_pickup_bar(self):
        notes = [Note(F(0), F(1), 60), Note(F(1), F(2), 65)]
        xml = musicxml(notes, Key.parse('F major'), 3, F(1), 84, 'Test')
        self.assertIn('<measure number="0" implicit="yes">', xml)

    def test_incipit_mismatch(self):
        with self.assertRaises(ValueError):
            check_incipit([Note(F(0), F(1), 65), Note(F(1), F(1), 67)], Key.parse('F major'), '13')


class CommittedTunesTest(unittest.TestCase):
    """Every tune in tunes.toml has MusicXML, a current render, and a first line of the right length."""

    def test_tunes(self):
        with open(PSALTER / 'tunes.toml', 'rb') as fh:
            tunes = tomllib.load(fh)['tune']
        for t in tunes:
            with self.subTest(t['id']):
                src = PSALTER / 'tunes' / f"{t['id']}.musicxml"
                xml = src.read_text(encoding='utf-8')
                meta = json.loads((PSALTER / 'rendered' / t['id'] / 'render.json').read_text(encoding='utf-8'))
                self.assertEqual(meta['source_sha256'], hashlib.sha256(src.read_bytes()).hexdigest())
                beats = int(re.search(r'<beats>(\d+)</beats>', xml).group(1))
                line = first_line(xml, t['line_beats'], t['pickup'], beats)
                total = sum(int(d) for d in re.findall(r'<duration>(\d+)</duration>', line)) / 4
                self.assertEqual(total, t['line_beats'])
                events = json.loads((PSALTER / 'rendered' / t['id'] / 'events.json').read_text(encoding='utf-8'))
                draw = drawing((PSALTER / 'rendered' / t['id'] / 'incipit.svg').read_text(encoding='utf-8'))
                tagged = {i['n'] for i in draw['items'] if 'n' in i}
                self.assertEqual(len(tagged), events['incipit_notes'])


if __name__ == '__main__':
    unittest.main()
