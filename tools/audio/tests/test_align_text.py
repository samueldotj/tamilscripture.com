"""Tests for the plain-Python half of `audio align`. Run: python -m unittest discover -s tools/audio/tests"""

import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from audio_tool import repo, tamil_numbers, text  # noqa: E402

VOCAB = set("abcdefghijklmnopqrstuvwxyz'")


def rom(w: str) -> str:
    """A stand-in for uroman: Latin text passes, Tamil becomes a placeholder word."""
    return w if w.isascii() else "tamil"


class TamilNumbers(unittest.TestCase):
    def test_small(self):
        self.assertEqual(tamil_numbers.spell(7), "ஏழு")
        self.assertEqual(tamil_numbers.spell(12), "பன்னிரண்டு")
        self.assertEqual(tamil_numbers.spell(40), "நாற்பது")
        self.assertEqual(tamil_numbers.spell(42), "நாற்பத்து இரண்டு")

    def test_hundreds_and_thousands(self):
        self.assertEqual(tamil_numbers.spell(200), "இருநூறு")
        self.assertEqual(tamil_numbers.spell(600), "அறுநூறு")
        self.assertEqual(tamil_numbers.spell(1400), "ஆயிரத்து நானூறு")
        self.assertEqual(tamil_numbers.spell(3700), "மூவாயிரத்து எழுநூறு")
        self.assertEqual(tamil_numbers.spell(6800), "ஆறாயிரத்து எண்ணூறு")
        self.assertEqual(tamil_numbers.spell(5000), "ஐயாயிரம்")
        self.assertEqual(tamil_numbers.spell(12000), "பன்னிரண்டாயிரம்")

    def test_lakhs(self):
        self.assertEqual(tamil_numbers.spell(144000), "இலட்சத்து நாற்பத்து நான்காயிரம்")
        self.assertEqual(tamil_numbers.spell(300000), "மூன்று இலட்சம்")


class Normalise(unittest.TestCase):
    def test_marks_and_joiners_go(self):
        self.assertEqual(text.clean("அ‌ஆ ¶ [the] “word”—x").split(), ["அஆ", "the", "word", "x"])

    def test_english_numbers(self):
        words = text.words_of("From Judah: 6,800 armed troops, the 12th", "eng", rom, VOCAB)
        self.assertEqual(words[:5], ["from", "judah", "six", "thousand", "eight"])
        self.assertEqual(words[-1], "twelfth")

    def test_tamil_numbers_are_spelled(self):
        self.assertIn("ஆயிரத்து", text.spell_numbers("1,400", "tam"))
        self.assertEqual(text.spell_numbers("12-ல்", "tam").split(), ["பன்னிரண்டு", "ல்"])

    def test_number_words_are_tagged(self):
        got = text.spoken_words("numbers 74,600.", "eng", rom, VOCAB)
        self.assertEqual(got[0], ("numbers", False))
        self.assertTrue(all(num for _, num in got[1:]))
        self.assertEqual([w for w, _ in got[1:]], ["seventy", "four", "thousand", "six", "hundred"])

    def test_filter_to_vocabulary(self):
        self.assertEqual(text.words_of("LORD's 42!", "eng", rom, VOCAB), ["lord's", "forty", "two"])


CHAPTER = {
    "book": "JHN", "chapter": 3,
    "blocks": [
        {"type": "heading", "kind": "s", "level": 1, "text": "Jesus and Nicodemus"},
        {"type": "para", "style": "p", "segments": [
            {"id": "JHN.3.1", "n": "1", "text": "Now there was a man"},
            {"id": "JHN.3.2", "n": "2", "text": "He came by night"},
        ]},
        {"type": "heading", "kind": "r", "level": 1, "text": "(Mark 1:1)"},
        {"type": "heading", "kind": "s", "level": 1, "text": "Mid heading"},
        {"type": "para", "style": "q1", "segments": [
            {"id": "JHN.3.2", "text": "continues here"},
            {"id": "JHN.3.3", "n": "3-4", "text": "Bridged"},
            {"id": "JHN.3.5", "n": "5", "text": "¶"},
        ]},
    ],
}


class Transcripts(unittest.TestCase):
    def test_words_verses_bridges(self):
        t = text.transcript(CHAPTER, "eng", rom, VOCAB, headings=False)
        self.assertEqual(t.verses, [1, 2, 3, 5])
        self.assertEqual(t.bridges, {3})
        self.assertEqual([w.verse for w in t.words].count(2), 6)
        self.assertFalse(any(w.heading for w in t.words))
        self.assertEqual(t.mid_headings, 2)  # "Mid heading"; the reference never counts

    def test_headings_included_and_marked(self):
        t = text.transcript(CHAPTER, "eng", rom, VOCAB, headings=True)
        heads = [(w.text, w.mid) for w in t.words if w.heading]
        self.assertEqual(heads, [("jesus", False), ("and", False), ("nicodemus", False), ("mid", True), ("heading", True)])


class VerseStarts(unittest.TestCase):
    def test_pause_midpoint_capped(self):
        first = {1: 4.0, 2: 10.0, 3: 20.0}
        last = {1: 9.0, 2: 19.9, 3: 25.0}
        se = text.verse_starts(first, last, [1, 2, 3, 5], 30.0)
        self.assertAlmostEqual(se[1][0], 3.7)  # 0.3 s before its first word
        self.assertAlmostEqual(se[2][0], 9.7)  # gap 9.0-10.0: capped at 0.3 s early
        self.assertAlmostEqual(se[3][0], 19.95)  # short gap: its midpoint
        self.assertAlmostEqual(se[1][1], se[2][0])
        self.assertAlmostEqual(se[3][1], 25.3)
        self.assertNotIn(5, se)  # wordless at the end: nothing to borrow

    def test_wordless_verse_borrows_next(self):
        se = text.verse_starts({1: 1.0, 3: 5.0}, {1: 4.0, 3: 8.0}, [1, 2, 3], 10.0)
        self.assertEqual(se[2][0], se[3][0])


class TimingsFiles(unittest.TestCase):
    def test_merge_keeps_edits(self):
        old = [repo.TimingRow(1, 1, 0, 10, 0.9), repo.TimingRow(3, 1, 0, 50, 0.9, "edited"), repo.TimingRow(3, 2, 50, 90, 0.9)]
        new = [repo.TimingRow(3, 1, 5, 55, 0.95), repo.TimingRow(3, 2, 55, 95, 0.95)]
        merged = repo.merge_timings(old, 3, new, force=False)
        self.assertEqual([(r.chapter, r.verse, r.start_ms, r.flag) for r in merged], [(1, 1, 0, ""), (3, 1, 0, "edited"), (3, 2, 55, "")])
        self.assertEqual(repo.merge_timings(old, 3, new, force=True)[1].start_ms, 5)

    def test_round_trip_and_align_section(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            old_data = repo.DATA_AUDIO
            repo.DATA_AUDIO = tmp
            d = tmp / "BSB" / "r1"
            d.mkdir(parents=True)
            (d / "recording.toml").write_text('version = "BSB"\nrecording = "r1"\n\n[source]\npreset = "dbp"\n\n[align]\nold = 1\n', encoding="utf-8")
            rows = [repo.TimingRow(3, 1, 3700, 9700, 0.97), repo.TimingRow(3, 3, 9700, 20000, 0.4, "low")]
            repo.write_timings("BSB", "r1", "JHN", rows)
            self.assertEqual(repo.read_timings("BSB", "r1", "JHN"), [repo.TimingRow(3, 1, 3700, 9700, 0.97), repo.TimingRow(3, 3, 9700, 20000, 0.4, "low")])
            repo.set_align_section("BSB", "r1", {"reads_text": "BSB", "other_texts": {"WEB": 0.61}, "reads_headings": False})
            data = tomllib.loads((d / "recording.toml").read_text(encoding="utf-8"))
            self.assertEqual(data["align"], {"reads_text": "BSB", "other_texts": {"WEB": 0.61}, "reads_headings": False})
            self.assertEqual(data["source"], {"preset": "dbp"})
        finally:
            repo.DATA_AUDIO = old_data
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
