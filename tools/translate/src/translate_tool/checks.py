"""Checks on a Tamil draft before it is written (feature_dictionary_translation.md §4).
The first three repeat the build's own rules (entity-ingest community.rs) so a
draft the build would reject is caught here and repaired."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .repo import Name, Term

TAMIL = re.compile(r"[஀-௿]")
TAG = re.compile(r"<[A-Za-z/]")
# A run of five or more Latin words is an untranslated sentence; single words
# (a Hebrew transliteration, "q.v.") are fine.
ENGLISH_RUN = re.compile(r"(?:\b[A-Za-z]{2,}\b[\s,;:'’-]+){4,}\b[A-Za-z]{2,}\b")
VERSE_NUM = re.compile(r"\b\d{1,3}:\d{1,3}\b")
MAX_CHARS = 4000


@dataclass
class Problem:
    where: str  # paragraph id, or "title"
    what: str

    def __str__(self) -> str:
        return f"{self.where}: {self.what}"


def check_text(text: str) -> str | None:
    """The build's rule: Tamil script, no markup, not empty, not too long."""
    t = text.strip()
    if not t:
        return "empty"
    if len(t) > MAX_CHARS:
        return f"longer than {MAX_CHARS} characters"
    if not TAMIL.search(t):
        return "no Tamil script"
    if TAG.search(t):
        return "contains HTML"
    return None


def terms_in(english: str, terms: dict[str, Term]) -> list[Term]:
    """Glossary terms whose English (or one of its `also` forms) occurs in the
    text as a word or phrase; a plural or possessive ending is allowed."""
    return [t for t in terms.values() if any(mentions(english, k) for k in (t.en, *t.also))]


def mentions(english: str, form: str) -> bool:
    """`form` occurs as a word or phrase (plural or possessive allowed). A form
    in capitals (LORD) matches only in capitals; any other form matches in any
    case except all capitals, so "Lord" does not match "LORD"."""
    english = english.replace("’", "'")
    form = form.replace("’", "'")
    pat = rf"\b{re.escape(form)}(?:s|es|'s)?\b"
    if form.isupper() and len(form) > 1:
        return re.search(pat, english) is not None
    return any(not (m[0].isupper() and len(m[0]) > 1) for m in re.finditer(pat, english, re.IGNORECASE))


# Names that are also everyday English words at the start of a sentence.
COMMON_WORDS = {"On", "No", "So", "Am", "As", "Job", "Will", "Mark", "Hope"}


def names_in(english: str, names: dict[str, Name]) -> list[Name]:
    return [
        n
        for en, n in names.items()
        if en not in COMMON_WORDS and re.search(rf"\b{re.escape(en)}\b", english)
    ]


def _stem(form: str) -> str:
    # Tamil adds case endings to the noun; match on the first few letters of
    # the shortest form, as the build does for article titles.
    return form[: max(3, min(len(form), 4))]


def uses_any(tamil: str, forms: list[str]) -> bool:
    return any(f and (f in tamil or _stem(f) in tamil) for f in forms)


def check_draft(
    article: dict,
    title: str,
    paragraphs: list[dict],
    terms: dict[str, Term],
    names: dict[str, Name],
) -> list[Problem]:
    """Every problem with a draft of `article`; empty means it can be written."""
    out: list[Problem] = []
    if why := check_text(title):
        out.append(Problem("title", why))

    english = {p["id"]: p for p in article["paragraphs"]}
    got = [p["id"] for p in paragraphs]
    if got != list(english):
        missing = [i for i in english if i not in got]
        extra = [i for i in got if i not in english]
        out.append(Problem("paragraphs", f"ids differ from the English (missing {missing}, unexpected {extra})"))

    for p in paragraphs:
        en = english.get(p["id"])
        if en is None:
            continue
        ta = p["text"]
        where = p["id"]
        if why := check_text(ta):
            out.append(Problem(where, why))
            continue
        if m := ENGLISH_RUN.search(ta):
            out.append(Problem(where, f"untranslated English: {m[0]!r}"))
        missing_refs = sorted(set(VERSE_NUM.findall(en["text"])) - set(VERSE_NUM.findall(ta)))
        if missing_refs:
            out.append(Problem(where, f"verse references missing: {', '.join(missing_refs)}"))
        ratio = len(ta) / max(1, len(en["text"]))
        if len(en["text"]) > 80 and not 0.6 <= ratio <= 3.5:
            out.append(Problem(where, f"length {ratio:.1f}× the English; likely something left out or added"))
        for t in terms_in(en["text"], terms):
            if not uses_any(ta, t.forms):
                out.append(Problem(where, f"glossary: “{t.en}” should be {t.ta}"))
            for bad in t.avoid:
                if bad and bad in ta:
                    out.append(Problem(where, f"glossary: “{bad}” is not used for “{t.en}”; use {t.ta}"))
        for n in names_in(en["text"], names):
            if not uses_any(ta, n.forms):
                out.append(Problem(where, f"name: {n.en} is {n.label} in the IRV"))
    return out
