"""Unit tests for tools/audio. Run: python -m unittest discover -s tools/audio/tests"""

import os
import sys
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from audio_tool import repo  # noqa: E402
from audio_tool.sources import Matcher, scan  # noqa: E402

BOOKS = repo.load_books()


def make_zip(names: list[str]) -> str:
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w") as z:
        for n in names:
            z.writestr(n, b"x")
    return path


class Presets(unittest.TestCase):
    def test_fcbh_counts_books_within_each_testament(self):
        m = Matcher({"preset": "fcbh"}, BOOKS)
        book, ch, fs, err = m.match("English_eng_WEB_OT_Drama/A19__150_Psalms______EN1WEBO2DA.mp3")
        self.assertEqual((book.code, ch, fs, err), ("PSA", 150, "EN1WEBO2DA", None))
        book, ch, fs, _ = m.match("Tamil_tam_DPI_NT_Non-Drama/B01___01_Matthew_____TAMDPIN1DA.mp3")
        self.assertEqual((book.code, ch, fs), ("MAT", 1, "TAMDPIN1DA"))
        book, ch, _, _ = m.match("B27___22_Revelation__EN1WEBN2DA.mp3")
        self.assertEqual((book.code, ch), ("REV", 22))
        book, ch, _, _ = m.match("A01___01_Genesis_______TAMDPIO1DA.mp3")
        self.assertEqual((book.code, ch), ("GEN", 1))
        # A name that fills its padded width leaves no _ before the fileset id.
        book, ch, fs, _ = m.match("A21___12_EcclesiastesEN1WEBO2DA.mp3")
        self.assertEqual((book.code, ch, fs), ("ECC", 12, "EN1WEBO2DA"))
        book, ch, fs, _ = m.match("Tamil_tam_DPI_NT_Non-Drama/B08___13_2CorinthiansTAMDPIN1DA.MP3")
        self.assertEqual((book.code, ch, fs), ("2CO", 13, "TAMDPIN1DA"))

    def test_fcbh_rejects_out_of_range_books(self):
        m = Matcher({"preset": "fcbh"}, BOOKS)
        self.assertIsNotNone(m.match("A40___01_Nothing_____EN1WEBO2DA.mp3")[3])
        self.assertIsNotNone(m.match("B28___01_Nothing_____EN1WEBN2DA.mp3")[3])
        self.assertEqual(m.match("readme.mp3"), (None, None, None, None))

    def test_dbp_checks_code_against_number(self):
        m = Matcher({"preset": "dbp"}, BOOKS)
        book, ch, fs, err = m.match("ENGBERO1DA_A19_PSA_150.mp3")
        self.assertEqual((book.code, ch, fs, err), ("PSA", 150, "ENGBERO1DA", None))
        self.assertEqual(m.match("ENGBERN1DA_B27_REV_022.mp3")[0].code, "REV")
        self.assertIsNotNone(m.match("ENGBERO1DA_A19_PRO_001.mp3")[3])

    def test_custom_pattern(self):
        m = Matcher({"preset": "custom", "pattern": r"(?P<book>\d{2})_(?P<chapter>\d{3})\.mp3$", "book_key": "number"}, BOOKS)
        self.assertEqual(m.match("43_003.mp3")[0].code, "JHN")
        m = Matcher({"preset": "custom", "pattern": r"(?P<book>\S+) (?P<chapter>\d+)\.mp3$", "book_key": "name", "names": {"யோவான்": "JHN"}}, BOOKS)
        self.assertEqual(m.match("யோவான் 3.mp3")[:2][1], 3)


class Scan(unittest.TestCase):
    def test_mapping_reports(self):
        z = make_zip([
            "RUT/ENGBERO1DA_A08_RUT_001.mp3",
            "RUT/ENGBERO1DA_A08_RUT_002.mp3",
            "ENGBERO1DA_A08_RUT_002.mp3",  # duplicate
            "ENGBERO1DA_A08_RUT_000.mp3",  # introduction
            "ENGBERO1DA_A08_RUT_009.mp3",  # Ruth has 4 chapters
            "__MACOSX/._ENGBERO1DA_A08_RUT_001.mp3",
            "copyright.pdf",
            "cover.jpg",
            "something.mp3",
        ])
        try:
            m = scan([z], Matcher({"preset": "dbp"}, BOOKS))
        finally:
            os.remove(z)
        self.assertEqual(sorted(m.chapters), [("RUT", 1), ("RUT", 2)])
        self.assertEqual(len(m.duplicates), 1)
        self.assertEqual(len(m.intros), 1)
        self.assertEqual(len(m.bad), 1)
        self.assertEqual(m.unmatched, ["something.mp3"])
        self.assertEqual([e.name for e in m.extras], ["copyright.pdf"])
        whole, partial = m.missing(BOOKS)
        self.assertEqual(partial, {"RUT": [3, 4]})
        self.assertIn("GEN", whole)
        self.assertEqual(m.fileset, {"ENGBERO1DA"})


class Files(unittest.TestCase):
    def test_object_key_matches_usfm_ingest(self):
        self.assertEqual(repo.object_key("IRVTAM", "r1", "JHN", 3), "IRVTAM/r1/JHN/JHN_003.mp3")

    def test_toml_writer_round_trips(self):
        value = {"name": 'a "quoted" தமிழ் ℗ \\ line\nbreak', "sha256": "ab" * 32}
        text = f"x = {repo.toml_value(value)}\ny = {repo.toml_value([True, 64, -16.0])}\n"
        self.assertEqual(tomllib.loads(text), {"x": value, "y": [True, 64, -16.0]})

    def test_recording_ids(self):
        self.assertEqual(repo.check_id("r2-remaster"), "r2-remaster")
        with self.assertRaises(SystemExit):
            repo.check_id("../r1")


if __name__ == "__main__":
    unittest.main()
