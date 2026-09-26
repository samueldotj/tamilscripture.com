"""The repository's files the tool reads and writes: books, versions, the
committed recording files under data/audio, and the git-ignored work folder."""

from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(os.environ.get("AUDIO_REPO") or Path(__file__).resolve().parents[4])
DATA_AUDIO = ROOT / "data" / "audio"
WORK = ROOT / ".audio-work"
CHAPTERS_HEADER = ["book", "chapter", "ms", "bytes", "sha256"]
DEFAULT_BASE = "https://stream.tamilaudiobible.com"


@dataclass(frozen=True)
class Book:
    code: str
    order: int  # 1..66
    testament: str  # OT | NT
    chapters: int
    name_en: str
    name_ta: str


def load_books() -> list[Book]:
    with open(ROOT / "data" / "books.toml", "rb") as f:
        raw = tomllib.load(f)["book"]
    return [
        Book(b["code"], b["order"], b["testament"], b["chapters"], b["name_en"], b["name_ta"])
        for b in raw
    ]


def load_version(code: str) -> dict:
    """version.toml for a version code, found by scanning data/versions."""
    for toml in sorted((ROOT / "data" / "versions").glob("*/version.toml")):
        with open(toml, "rb") as f:
            v = tomllib.load(f)
        if v.get("code") == code:
            v["_path"] = toml
            return v
    raise SystemExit(f"no version {code} under data/versions")


def check_id(recording: str) -> str:
    if not re.fullmatch(r"[a-z0-9-]+", recording):
        raise SystemExit(f"recording id {recording!r} must be lower-case letters, digits and -")
    return recording


def rec_dir(version: str, recording: str) -> Path:
    return DATA_AUDIO / version / check_id(recording)


def work_dir(version: str, recording: str) -> Path:
    return WORK / version / check_id(recording)


def object_key(version: str, recording: str, book: str, chapter: int) -> str:
    """The R2 key; crates/usfm-ingest/src/audio.rs builds the same one."""
    return f"{version}/{recording}/{book}/{book}_{chapter:03d}.mp3"


def load_base() -> str:
    path = DATA_AUDIO / "audio.toml"
    if not path.exists():
        return DEFAULT_BASE
    with open(path, "rb") as f:
        return tomllib.load(f)["base"].rstrip("/")


def load_recording(version: str, recording: str) -> dict:
    path = rec_dir(version, recording) / "recording.toml"
    if not path.exists():
        raise SystemExit(f"{path} is missing; run `audio init` first")
    with open(path, "rb") as f:
        rec = tomllib.load(f)
    if rec.get("version") != version or rec.get("recording") != recording:
        raise SystemExit(f"{path} names {rec.get('version')} {rec.get('recording')}")
    return rec


# ---- chapters.tsv ----------------------------------------------------------

@dataclass
class ChapterRow:
    book: str
    chapter: int
    ms: int
    bytes: int
    sha256: str


def read_chapters(version: str, recording: str) -> list[ChapterRow]:
    path = rec_dir(version, recording) / "chapters.tsv"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].split("\t") != CHAPTERS_HEADER:
        raise SystemExit(f"{path}: unexpected header")
    rows = []
    for line in lines[1:]:
        if line:
            b, c, ms, n, sha = line.split("\t")
            rows.append(ChapterRow(b, int(c), int(ms), int(n), sha))
    return rows


def write_chapters(version: str, recording: str, rows: list[ChapterRow], books: list[Book]) -> Path:
    order = {b.code: b.order for b in books}
    rows = sorted(rows, key=lambda r: (order[r.book], r.chapter))
    path = rec_dir(version, recording) / "chapters.tsv"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = ["\t".join(CHAPTERS_HEADER)]
    body += [f"{r.book}\t{r.chapter}\t{r.ms}\t{r.bytes}\t{r.sha256}" for r in rows]
    path.write_text("\n".join(body) + "\n", encoding="utf-8", newline="\n")
    return path


# ---- state.json in the work folder -----------------------------------------

class State:
    """Per-chapter progress, keyed "JHN.3", so every step can resume."""

    def __init__(self, version: str, recording: str):
        self.path = work_dir(version, recording) / "state.json"
        self.data: dict = {"zips": {}, "chapters": {}}
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def chapter(self, book: str, chapter: int) -> dict:
        return self.data["chapters"].setdefault(f"{book}.{chapter}", {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)


# ---- tiny TOML writer (tomllib reads; the standard library has no writer) --

def toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        # A JSON string is a valid TOML basic string.
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {toml_value(x)}" for k, x in v.items()) + " }"
    raise TypeError(type(v))
