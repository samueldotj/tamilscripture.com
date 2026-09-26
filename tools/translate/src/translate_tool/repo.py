"""The repository's files the tool reads and writes: the built English
articles, books, the IRV text, the BSB's Strong's tags, the name and term
glossaries, and the Tamil drafts (docs/feature_dictionary_translation.md)."""

from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

ROOT = Path(os.environ.get("TRANSLATE_REPO") or Path(__file__).resolve().parents[4])
DATA = ROOT / "data"
ENTITIES = DATA / "entities"
DRAFTS = ENTITIES / "drafts"
CONTENT = ROOT / "apps" / "web" / "static" / "content"
GLOSSARY = ENTITIES / "glossary-theology-ta.toml"
NAMES = ENTITIES / "names-ta.toml"
WORK = ROOT / ".translate-work"

TAMIL_VERSION = "IRVTAM"
STRONGS_VERSION = "bsb"  # data/versions/{dir} whose USFM carries strong="…" tags


# ---- build output ----


@cache
def build_dir() -> Path:
    """content/{build}/ of the current build; `pnpm content` makes it."""
    path = CONTENT / "manifest.json"
    if not path.exists():
        raise SystemExit(f"{path} is missing; run `pnpm content` first")
    build = json.loads(path.read_text(encoding="utf-8"))["build"]
    return CONTENT / build


def articles_index() -> list[dict]:
    """[{id, source, title, hash, paragraphs, entities?}] for every article."""
    return json.loads((build_dir() / "entities" / "articles" / "index.json").read_text(encoding="utf-8"))


def load_article(article_id: str) -> dict:
    source, slug = article_id.split("/", 1)
    path = build_dir() / "entities" / "articles" / source / f"{slug}.json"
    if not path.exists():
        raise SystemExit(f"no article {article_id} in the build")
    return json.loads(path.read_text(encoding="utf-8"))


def is_sharealike(article: dict) -> bool:
    return "SA" in article.get("licence", "")


# ---- books ----


@dataclass(frozen=True)
class Book:
    code: str
    order: int
    name_en: str
    name_ta: str
    abbr_en: tuple[str, ...]


@cache
def books() -> list[Book]:
    with open(DATA / "books.toml", "rb") as f:
        raw = tomllib.load(f)["book"]
    return [Book(b["code"], b["order"], b["name_en"], b["name_ta"], tuple(b.get("abbr_en", []))) for b in raw]


# Spellings the dictionaries use that books.toml does not list.
_BOOK_ALIASES = {
    "SNG": ["Song of Solomon", "Song of Songs", "Canticles"],
    "PSA": ["Psalm"],
    "REV": ["Revelations", "Apocalypse"],
    "ECC": ["Ecclesiastes", "Eccl", "Eccles"],
}


def book_key(s: str) -> str:
    return re.sub(r"[\s.]", "", s.lower())


@cache
def book_lookup() -> dict[str, Book]:
    """English name, abbreviation or USFM code, lowercased without spaces
    or dots → book."""
    out: dict[str, Book] = {}
    for b in books():
        for key in (b.code, b.name_en, *b.abbr_en, *_BOOK_ALIASES.get(b.code, [])):
            out[book_key(key)] = b
    return out


# ---- verses ----


@cache
def chapter_verses(version: str, book: str, chapter: int) -> dict[str, str]:
    """Verse id → text for one chapter of the built reader JSON. A verse split
    across paragraphs or poetry lines is joined."""
    path = build_dir() / version / book / f"{chapter}.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}

    def walk(node):
        if isinstance(node, dict):
            if "id" in node and "text" in node and re.fullmatch(r"[1-4A-Z]{3}\.\d+\.\d+", str(node["id"])):
                out.setdefault(node["id"], []).append(node["text"].strip())
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data.get("blocks", []))
    return {k: " ".join(t for t in v if t) for k, v in out.items()}


def verse_text(verse_id: str, version: str = TAMIL_VERSION) -> str | None:
    book, ch, _ = verse_id.split(".")
    return chapter_verses(version, book, int(ch)).get(verse_id)


_REF = re.compile(
    r"^(?P<book>(?:[1-3]\s?)?[A-Za-z][A-Za-z .]*?)\.?\s+(?P<ch>\d+)(?::(?P<v1>\d+)(?:\s*[-–]\s*(?P<v2>\d+))?)?$"
)


def parse_ref(ref: str) -> list[str]:
    """`Romans 5:1-10`, `Rom. 5:1`, `EST 1:10` → verse ids. Whole chapters
    and unknown books give nothing (too long, or not a Bible reference)."""
    m = _REF.match(ref.strip())
    if not m or not m["v1"]:
        return []
    b = book_lookup().get(book_key(m["book"]))
    if not b:
        return []
    v1 = int(m["v1"])
    v2 = int(m["v2"]) if m["v2"] else v1
    if v2 < v1 or v2 - v1 > 30:
        v2 = v1
    return [f"{b.code}.{m['ch']}.{v}" for v in range(v1, v2 + 1)]


# ---- Strong's numbers from the BSB ----


@dataclass
class StrongsIndex:
    """Strong's number → [(verse id, English words tagged with it)]."""

    by_number: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    def verses(self, number: str) -> list[tuple[str, str]]:
        return self.by_number.get(normalise_strongs(number), [])


def normalise_strongs(n: str) -> str:
    """`G1344`, `g01344`, `H7225a` → `G1344` / `H7225` (letter suffixes dropped)."""
    m = re.fullmatch(r"([GHgh])0*(\d+)[a-zA-Z]?", n.strip())
    if not m:
        raise ValueError(f"not a Strong's number: {n!r}")
    return f"{m[1].upper()}{int(m[2])}"


_USFM_WORD = re.compile(r'\\\+?w\s+([^|\\]+)\|strong="([^"]+)"\s*\\\+?w\*')


def parse_usfm_strongs(text: str) -> list[tuple[str, str, str]]:
    """(verse id, English word, Strong's number) for every tagged word."""
    out = []
    book = None
    ch = v = 0
    for line in text.splitlines():
        if line.startswith("\\id "):
            book = line[4:7]
        for m in re.finditer(r"\\c\s+(\d+)|\\v\s+(\d+)|" + _USFM_WORD.pattern, line):
            if m[1]:
                ch, v = int(m[1]), 0
            elif m[2]:
                v = int(m[2])
            elif book and ch and v:
                for num in m[4].split(","):
                    try:
                        out.append((f"{book}.{ch}.{v}", m[3].strip(), normalise_strongs(num)))
                    except ValueError:
                        pass
    return out


@cache
def strongs_index() -> StrongsIndex:
    idx = StrongsIndex()
    for path in sorted((DATA / "versions" / STRONGS_VERSION).glob("*.usfm")):
        words: dict[tuple[str, str], list[str]] = {}
        for vid, word, num in parse_usfm_strongs(path.read_text(encoding="utf-8-sig")):
            words.setdefault((num, vid), []).append(word)
        for (num, vid), ws in words.items():
            idx.by_number.setdefault(num, []).append((vid, " ".join(dict.fromkeys(ws))))
    return idx


# ---- glossaries ----


@dataclass
class Term:
    en: str
    ta: str
    forms: list[str]
    avoid: list[str]
    also: list[str]  # other English forms of the term: justify, justified
    note: str
    review: bool


def load_glossary(path: Path = GLOSSARY) -> dict[str, Term]:
    """English term (lowercase) → entry. Missing file → empty."""
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    return {
        en.lower(): Term(
            en,
            e.get("ta", ""),
            list(e.get("forms", [])) or [e.get("ta", "")],
            list(e.get("avoid", [])),
            list(e.get("also", [])),
            e.get("note", ""),
            bool(e.get("review", False)),
        )
        for en, e in raw.items()
        if isinstance(e, dict) and e.get("ta")
    }


def reviewed_terms(path: Path = GLOSSARY) -> dict[str, Term]:
    return {k: t for k, t in load_glossary(path).items() if not t.review}


@dataclass
class Name:
    en: str
    label: str
    forms: list[str]


def load_names(path: Path | None = None) -> dict[str, dict]:
    """English name → its entry `{label, forms, confidence, n, review?}`, one
    per name for every Tamil version."""
    path = path or NAMES
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    return {en: e for en, e in raw.items() if isinstance(e, dict) and e.get("label")}


def reviewed_names(path: Path | None = None) -> dict[str, Name]:
    """English name → accepted Tamil name; unreviewed entries are left out,
    since many single-verse drafts are wrong."""
    return {
        en: Name(en, e["label"], list(e.get("forms", [])) or [e["label"]])
        for en, e in load_names(path).items()
        if not e.get("review", False)
    }


def toml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def name_line(name: str, e: dict) -> str:
    """One line of names-ta.toml, exactly as entity-ingest's `names::save` writes it."""
    forms = ", ".join(toml_str(f) for f in e["forms"])
    review = ", review = true" if e.get("review") else ""
    return (
        f"{toml_str(name)} = {{ label = {toml_str(e['label'])}, forms = [{forms}], "
        f"confidence = {e.get('confidence', 1.0):.2f}, n = {e.get('n', 0)}{review} }}"
    )


def save_name(name: str, e: dict, path: Path | None = None) -> None:
    """Replace (or insert, in sorted place) one name's line, leaving the rest
    of the file as it is."""
    path = path or NAMES
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    new = name_line(name, e)
    prefix = toml_str(name) + " = "
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = new
            break
    else:
        def key(line: str) -> str | None:
            m = re.match(r'^"((?:[^"\\]|\\.)*)" = ', line)
            return json.loads(f'"{m[1]}"') if m else None

        at = next((i for i, l in enumerate(lines) if (k := key(l)) is not None and k > name), len(lines))
        lines.insert(at, new)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


# ---- drafts ----


def draft_path(article: dict) -> Path:
    sub = "ta-sa" if is_sharealike(article) else "ta"
    source, slug = article["id"].split("/", 1)
    return DRAFTS / sub / source / f"{slug}.json"


def load_draft(article: dict) -> dict | None:
    p = draft_path(article)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def write_draft(article: dict, draft: dict) -> Path:
    p = draft_path(article)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return p
