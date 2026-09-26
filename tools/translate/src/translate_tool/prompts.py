"""What is sent to the model (feature_dictionary_translation.md §4).

The system prompt is identical for every article in a run (style guide, the
reviewed glossary, the Tamil book names) so it is cached; everything specific
to an article goes in the user message. Bump PROMPT_VERSION whenever the
wording or the rules change: drafts record it, and a run redoes drafts made
with an older version only when asked (--force).
"""

from __future__ import annotations

import json
import re

from . import checks, repo
from .repo import Name, Term

PROMPT_VERSION = "1"

STYLE = """\
You translate articles from English Bible dictionaries (Easton's, Smith's and the Aquifer Open Bible Dictionary) into Tamil for tamilscripture.com, a Tamil Bible study site whose readers are Tamil Protestant Christians in the Reformed tradition. The site's Bible is the Indian Revised Version (IRV, 2019), and the Tamil must read as though written for readers of the IRV.

How to translate:
- Translate faithfully and completely. Do not summarise, explain, soften, add to, or correct what the article says, even where you would put it differently. Keep the author's reasoning and order.
- Write formal written Tamil in the register of the IRV and of Tamil Protestant teaching, not colloquial Tamil and not Sanskritised or Hindu religious vocabulary where the IRV uses another word.
- Theological terms: use the Tamil given in the glossary below whenever the English term or one of its forms occurs, inflecting it as the sentence needs. Never use a rendering listed under "avoid". For a theological term not in the glossary, use the word the IRV uses in the verses where that idea occurs; if the IRV has none, choose the term established in Tamil Protestant (Reformed) teaching.
- Names of people and places: use the Tamil names given with each article. Otherwise use the spelling the IRV uses; transliterate only a name the IRV does not contain.
- The divine name: follow the IRV. Where the English article quotes or refers to a verse, the IRV text of that verse is supplied; use its wording for any quotation.
- Scripture references: write the book in Tamil using the book names below and keep chapter and verse numbers exactly as in the English (Rom. 5:1-10 → ரோமர் 5:1-10). Keep every reference.
- Hebrew, Greek and Aramaic words cited in the English stay in Latin letters as given, followed by the Tamil meaning if the English gives one.
- "q.v.", "cf.", "i.e." and similar become their plain Tamil equivalents (காண்க, ஒப்பிடுக, அதாவது).
- Measurements, dates and numbers keep their values.
- Headings (marked "heading": true) are translated as short headings.
- Produce plain text only: no HTML, Markdown or notes of your own.

Output: JSON with the article title in Tamil and one Tamil paragraph for every English paragraph, with the same "id" values in the same order."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "paragraphs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
                "required": ["id", "text"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "paragraphs"],
    "additionalProperties": False,
}

# Chunk long articles so a single response stays well inside the output limit
# (Tamil runs to several times the English token count).
CHUNK_WORDS = 2500
# Cited verses sent with one request; more are rarely quoted in full.
MAX_VERSES = 40


def glossary_block(terms: dict[str, Term]) -> str:
    if not terms:
        return "Glossary: (none reviewed yet)"
    lines = ["Glossary (English → Tamil; forms show accepted inflections; never use the avoid list):"]
    for key in sorted(terms):
        t = terms[key]
        line = f"- {t.en}"
        if t.also:
            line += f" ({', '.join(t.also)})"
        line += f" → {t.ta}"
        extra = [f for f in t.forms if f != t.ta]
        if extra:
            line += f"; forms: {', '.join(extra)}"
        if t.avoid:
            line += f"; avoid: {', '.join(t.avoid)}"
        if t.note:
            line += f"; note: {t.note}"
        lines.append(line)
    return "\n".join(lines)


def books_block() -> str:
    return "Tamil book names (IRV):\n" + "\n".join(f"- {b.name_en} → {b.name_ta}" for b in repo.books())


def system_blocks(terms: dict[str, Term]) -> list[dict]:
    """The cached system prompt. Deterministic for a given glossary: sorted,
    no dates or ids, so every request in a run shares the cache."""
    text = "\n\n".join([STYLE, glossary_block(terms), books_block()])
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


_INLINE_REF = re.compile(r"\b((?:[1-3]\s?)?[A-Z][a-z]+\.?)\s+(\d{1,3}):(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?")


def cited_verses(article: dict, paragraphs: list[dict]) -> list[str]:
    """Verse ids the article cites, from its refs and from references in the
    text of these paragraphs, in order of first mention, capped."""
    ids: list[str] = []
    refs = list(article.get("refs", []))
    for p in paragraphs:
        refs += [m[0] for m in _INLINE_REF.finditer(p["text"])]
    for r in refs:
        for vid in repo.parse_ref(r):
            if vid not in ids:
                ids.append(vid)
    return ids[:MAX_VERSES]


def chunks(article: dict) -> list[list[dict]]:
    """Paragraph groups of at most CHUNK_WORDS English words (a longer single
    paragraph is its own group)."""
    out: list[list[dict]] = [[]]
    words = 0
    for p in article["paragraphs"]:
        n = len(p["text"].split())
        if out[-1] and words + n > CHUNK_WORDS:
            out.append([])
            words = 0
        out[-1].append(p)
        words += n
    return out


def user_message(
    article: dict,
    paragraphs: list[dict],
    part: tuple[int, int],
    names: dict[str, Name],
    title_hint: str | None,
) -> str:
    """The article (or one part of it) with the names and verses it needs."""
    english = " ".join([article["title"], *(p["text"] for p in paragraphs)])
    sections = []

    found = checks.names_in(english, names)
    if found:
        sections.append(
            "Tamil names in the IRV for names in this article:\n"
            + "\n".join(f"- {n.en} → {', '.join(dict.fromkeys([n.label, *n.forms[:4]]))}" for n in found)
        )

    verses = [(vid, repo.verse_text(vid)) for vid in cited_verses(article, paragraphs)]
    verses = [(vid, t) for vid, t in verses if t]
    if verses:
        sections.append("IRV text of verses cited:\n" + "\n".join(f"- {vid}: {t}" for vid, t in verses))

    if title_hint:
        sections.append(f"This headword is already translated elsewhere on the site as “{title_hint}”; use that title.")

    k, n = part
    if n > 1:
        sections.append(
            f"This is part {k} of {n} of a long article; translate only these paragraphs. "
            "Give the article title every time."
        )

    payload = {
        "id": article["id"],
        "title": article["title"],
        "paragraphs": [
            {"id": p["id"], "text": p["text"], **({"heading": True} if p.get("heading") else {})} for p in paragraphs
        ],
    }
    sections.append("Article:\n" + json.dumps(payload, ensure_ascii=False, indent=1))
    return "\n\n".join(sections)


def repair_message(problems: list[checks.Problem]) -> str:
    return (
        "The translation has these problems:\n"
        + "\n".join(f"- {p}" for p in problems)
        + "\n\nReturn the whole corrected JSON, with every paragraph."
    )
