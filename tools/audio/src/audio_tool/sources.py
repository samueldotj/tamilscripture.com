"""Match the files in a recording's zips to (book, chapter).

Presets cover the naming schemes in use (docs/feature_audio_tool.md §4):

  fcbh   A19__150_Psalms______EN1WEBO2DA.mp3      A = OT, B = NT, then the book's
         B01___01_Matthew_____TAMDPIN1DA.mp3      number within its testament;
                                                  the chapter is padded with _
  dbp    ENGBERO1DA_A19_PSA_150.mp3               the USFM code, checked against A19

`custom` takes a regex with named groups `book` and `chapter`, and `book_key`
says how to read `book`: "number" (1-66), "usfm" or "name" (via [source.names]).
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from .repo import Book

# The name is padded with _ to a fixed width, so a name that fills it runs
# straight into the fileset id (A21___01_EcclesiastesEN1WEBO2DA.mp3); the id
# is the last ten upper-case characters.
FCBH = re.compile(
    r"(?P<t>[AB])(?P<n>\d{2})_+(?P<chapter>\d{1,3})_(?P<name>.*?)_*(?P<fileset>[A-Z0-9]{10})(?i:\.mp3)$"
)
DBP = re.compile(
    r"(?P<fileset>[A-Z0-9]{6,})_(?P<t>[AB])(?P<n>\d{2})_(?P<book>[1-4A-Z]{3})_(?P<chapter>\d{1,3})\.mp3$",
    re.IGNORECASE,
)
AUDIO = (".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus")


@dataclass
class Member:
    zip: str  # path of the zip
    name: str  # member name inside it
    size: int
    crc: int


@dataclass
class Mapping:
    chapters: dict[tuple[str, int], Member] = field(default_factory=dict)
    unmatched: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    intros: list[str] = field(default_factory=list)  # chapter 0
    bad: list[str] = field(default_factory=list)  # matched but impossible
    skipped: list[str] = field(default_factory=list)  # not audio
    fileset: set[str] = field(default_factory=set)
    extras: list[Member] = field(default_factory=list)  # copyright.pdf and the like

    def missing(self, books: list[Book]) -> tuple[list[str], dict[str, list[int]]]:
        """Books with no files at all, and books with some chapters missing."""
        whole, partial = [], {}
        for b in books:
            have = [c for c in range(1, b.chapters + 1) if (b.code, c) in self.chapters]
            if not have:
                whole.append(b.code)
            elif len(have) < b.chapters:
                partial[b.code] = [c for c in range(1, b.chapters + 1) if (b.code, c) not in self.chapters]
        return whole, partial


class Matcher:
    def __init__(self, source: dict, books: list[Book]):
        self.preset = source.get("preset", "custom")
        self.books = books
        self.by_code = {b.code: b for b in books}
        self.by_order = {b.order: b for b in books}
        if self.preset == "custom":
            self.pattern = re.compile(source["pattern"])
            self.book_key = source.get("book_key", "usfm")
            self.names = source.get("names", {})
        elif self.preset not in ("fcbh", "dbp"):
            raise SystemExit(f"unknown preset {self.preset!r}; use fcbh, dbp or custom")

    def _testament(self, t: str, n: int) -> Book | None:
        order = n if t.upper() == "A" else 39 + n
        if (t.upper() == "A" and not 1 <= n <= 39) or (t.upper() == "B" and not 1 <= n <= 27):
            return None
        return self.by_order.get(order)

    def match(self, name: str) -> tuple[Book | None, int | None, str | None, str | None]:
        """(book, chapter, fileset, problem) for a member's base name, or all None if no match."""
        base = PurePosixPath(name).name
        if self.preset == "fcbh":
            m = FCBH.search(base)
            if not m:
                return None, None, None, None
            book = self._testament(m["t"], int(m["n"]))
            if not book:
                return None, None, None, f"{base}: no book {m['t']}{m['n']}"
            return book, int(m["chapter"]), m["fileset"].upper(), None
        if self.preset == "dbp":
            m = DBP.search(base)
            if not m:
                return None, None, None, None
            book = self.by_code.get(m["book"].upper())
            if not book:
                return None, None, None, f"{base}: unknown book {m['book']}"
            if self._testament(m["t"], int(m["n"])) is not book:
                return None, None, None, f"{base}: {m['t']}{m['n']} is not {book.code}"
            return book, int(m["chapter"]), m["fileset"].upper(), None
        m = self.pattern.search(base)
        if not m:
            return None, None, None, None
        key = m["book"]
        if self.book_key == "number":
            book = self.by_order.get(int(key))
        elif self.book_key == "name":
            book = self.by_code.get(self.names.get(key, ""))
        else:
            book = self.by_code.get(key.upper())
        if not book:
            return None, None, None, f"{base}: unknown book {key!r}"
        return book, int(m["chapter"]), None, None


def is_junk(name: str) -> bool:
    parts = PurePosixPath(name).parts
    return name.endswith("/") or any(p == "__MACOSX" or p.startswith(".") for p in parts)


def scan(zips: list[str], matcher: Matcher) -> Mapping:
    out = Mapping()
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            for info in zf.infolist():
                name = info.filename
                if is_junk(name):
                    continue
                if not name.lower().endswith(AUDIO):
                    out.skipped.append(f"{z}:{name}")
                    if name.lower().endswith((".pdf", ".txt", ".md")):
                        out.extras.append(Member(z, name, info.file_size, info.CRC))
                    continue
                book, chapter, fileset, problem = matcher.match(name)
                if problem:
                    out.bad.append(problem)
                    continue
                if not book:
                    out.unmatched.append(name)
                    continue
                if chapter == 0:
                    out.intros.append(name)
                    continue
                if chapter > book.chapters:
                    out.bad.append(f"{name}: {book.code} has {book.chapters} chapters")
                    continue
                if fileset:
                    out.fileset.add(fileset)
                key = (book.code, chapter)
                member = Member(z, name, info.file_size, info.CRC)
                if key in out.chapters:
                    out.duplicates.append(f"{book.code} {chapter}: {out.chapters[key].name} and {name}")
                    continue
                out.chapters[key] = member
    return out
