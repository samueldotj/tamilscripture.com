"""English and Tamil verses side by side for one word, so a reviewer can see
how the IRV renders it (`translate verses`).

A word is looked up three ways:
- a person or place name: the verses the build lists for it (TIPNR, OpenBible);
- a Strong's number (G1344, H7225): the BSB verses tagged with it;
- anything else: the English verses that contain it as a whole word.

The Tamil words that recur across those verses and are rare elsewhere in the
IRV are offered as candidates, the same idea as entity-ingest's name aligner.
"""

from __future__ import annotations

import html
import json
import math
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from dataclasses import dataclass
from functools import cache

from . import repo

TAMIL_WORD = re.compile(r"[஀-௿]+")
# A name of one Tamil word, or several separated by spaces (பரிசுத்த ஸ்தலம்).
TAMIL_NAME = re.compile(r"[஀-௿]+(?: [஀-௿]+)*")
PREFIX = 4  # code points: about two Tamil letters, enough to group inflections


@cache
def corpus(version: str) -> dict[str, str]:
    """Verse id → text for a whole version of the built reader JSON."""
    out: dict[str, str] = {}
    root = repo.build_dir() / version
    for path in sorted(root.glob("*/*.json")):
        book, ch = path.parent.name, path.stem
        if ch.isdigit():
            out.update(repo.chapter_verses(version, book, int(ch)))
    return out


@cache
def prefix_df(version: str) -> tuple[Counter, int]:
    """Word prefix → number of verses containing a word with that prefix."""
    df: Counter = Counter()
    verses = corpus(version)
    for text in verses.values():
        df.update({w[:PREFIX] for w in TAMIL_WORD.findall(text)})
    return df, len(verses)


@cache
def name_verses() -> dict[str, set[str]]:
    """English name → verse ids, from the built person and place files (the
    same verses entity-ingest drafts and validates names against)."""
    return {name: verses for name, (verses, _) in _entities().items()}


@cache
def name_briefs() -> dict[str, list[str]]:
    """English name → one line per person or place of that name ("person:
    Paralyzed man in Lydda healed by Peter")."""
    return {name: briefs for name, (_, briefs) in _entities().items()}


@cache
def _entities() -> dict[str, tuple[set[str], list[str]]]:
    out: dict[str, tuple[set[str], list[str]]] = {}
    for kind in ("person", "place"):
        for path in sorted((repo.build_dir() / "entities" / kind).glob("*.json")):
            e = json.loads(path.read_text(encoding="utf-8"))
            if not e.get("name_en"):
                continue
            verses, briefs = out.setdefault(e["name_en"], (set(), []))
            verses.update(e.get("verses", []))
            what = e.get("brief") or e.get("short") or e.get("place_type") or ""
            briefs.append(f"{kind}: {what}".rstrip(": ") + f" ({len(e.get('verses', []))} verses)")
    return out


def verse_order(vid: str) -> tuple[int, int, int]:
    book, ch, v = vid.split(".")
    order = {b.code: b.order for b in repo.books()}
    return order.get(book, 99), int(ch), int(v)


@dataclass
class Lookup:
    query: str
    kind: str  # name | strongs | word
    verses: list[str]
    english_terms: list[str]  # what to highlight in the English


def find(query: str, english: str) -> Lookup:
    names = name_verses()
    if query in names:
        return Lookup(query, "name", sorted(names[query], key=verse_order), [query])
    if re.fullmatch(r"[GHgh]\d{1,5}[a-zA-Z]?", query):
        rows = repo.strongs_index().verses(query)
        # the tagged English words, less short function words the BSB tags loosely
        words = sorted({w for _, ws in rows for w in ws.split() if len(w) > 3}, key=len, reverse=True)
        return Lookup(repo.normalise_strongs(query), "strongs", [v for v, _ in rows], words)
    flags = 0 if query[:1].isupper() else re.IGNORECASE
    pat = re.compile(rf"\b{re.escape(query)}\b", flags)
    hits = [vid for vid, t in corpus(english).items() if pat.search(t)]
    return Lookup(query, "word", sorted(hits, key=verse_order), [query])


@dataclass
class Candidate:
    prefix: str
    covered: int  # verses of the lookup containing it
    score: float
    words: list[tuple[str, int]]  # full spellings, most frequent first
    sounds: float = 0.0  # 0–1: how close the consonants are to the English name


# Consonant skeletons, so அபக்தா and Abagtha both read "pkt". Tamil writes one
# letter for voiced and voiceless stops, and h is often dropped, so both sides
# fold b→p, g→k, d→t, z/sh→s and drop h and the vowels; a Hebrew j is ய
# in Tamil (John யோவான், Joseph யோசேப்பு), so j→y.
_TA_CONS = dict(zip("கஙசஞடணதநபமயரலவழளறனஜஷஸஹ", "knsntnt" "npmyrlvllrnsss" + "h"))
_EN_FOLD = [("ph", "p"), ("th", "t"), ("sh", "s"), ("ch", "k"), ("ck", "k"), ("qu", "kv"),
            ("b", "p"), ("g", "k"), ("d", "t"), ("c", "k"), ("q", "k"), ("j", "y"), ("z", "s"),
            ("x", "ks"), ("f", "p"), ("w", "v")]


def skeleton_ta(word: str) -> str:
    return "".join(_TA_CONS.get(ch, "") for ch in word).replace("h", "")


def skeleton_en(name: str) -> str:
    s = name.lower()
    for a, b in _EN_FOLD:
        s = s.replace(a, b)
    return "".join(ch for ch in s if ch in "kmnprstvly")


# Full romanisations with vowels (long and short alike), for names too short
# for consonants to decide: Esek "esek" is not ஈசாக் "isak" (Isaac).
_TA_VOWELS = {"அ": "a", "ஆ": "a", "இ": "i", "ஈ": "i", "உ": "u", "ஊ": "u", "எ": "e", "ஏ": "e", "ஐ": "ai",
              "ஒ": "o", "ஓ": "o", "ஔ": "au"}
_TA_SIGNS = {"ா": "a", "ி": "i", "ீ": "i", "ு": "u", "ூ": "u", "ெ": "e",
             "ே": "e", "ை": "ai", "ொ": "o", "ோ": "o", "ௌ": "au"}


def _collapse(s: str) -> str:
    return re.sub(r"(.)\1+", r"\1", s)


def roman_ta(word: str) -> str:
    out = []
    for i, ch in enumerate(word):
        if ch in _TA_VOWELS:
            out.append(_TA_VOWELS[ch])
        elif ch in _TA_CONS:
            out.append(_TA_CONS[ch])
            nxt = word[i + 1 : i + 2]
            if nxt != "்" and nxt not in _TA_SIGNS:
                out.append("a")  # inherent vowel
        elif ch in _TA_SIGNS:
            out.append(_TA_SIGNS[ch])
    return _collapse("".join(out).replace("h", ""))


def roman_en(name: str) -> str:
    s = name.lower()
    for a, b in _EN_FOLD:
        s = s.replace(a, b)
    s = s.replace("h", "").replace("y", "i") if not s.startswith("y") else "y" + s[1:].replace("h", "").replace("y", "i")
    return _collapse("".join(ch for ch in s if ch.isalpha()))


def full_match(tamil: str, english: str) -> float:
    """Similarity of the romanisations, vowels included, 0–1."""
    return SequenceMatcher(None, roman_ta(tamil), roman_en(english)).ratio()


# Case endings after a name ending in a vowel (the v/y glide is part of the
# ending: தமஸ்கு-வை, வஸ்தி-யின்) and after one ending in a consonant, where
# the ending replaces the virama (ஆரோன் → ஆரோனை, எருசலேம் → எருசலேமில்).
VOWEL_ENDINGS = ["வுக்குப்", "வுக்குக்", "வுக்குச்", "வுக்குத்", "வுக்கு", "விலிருந்து", "வினுடைய", "விடம்", "வோடு", "வின்", "வில்", "வும்", "வை",
                 "யுக்குப்", "யுக்குக்", "யுக்கு", "யிலிருந்து", "யினுடைய", "யிடம்", "யோடு", "யின்", "யில்", "யும்", "யை",
                 "வையும்", "வுக்கும்", "விலும்", "வினால்", "வால்", "விலே", "வுடன்", "வோடே",
                 "யையும்", "யுக்கும்", "யிலும்", "யினால்", "யால்", "யிலே", "யுடன்", "யோடே",
                 "வைவிட்டு", "விலுள்ள", "வின்மேல்", "யைவிட்டு", "யிலுள்ள", "யின்மேல்",
                 "வைக்", "வைச்", "வைத்", "வைப்", "யைக்", "யைச்", "யைத்", "யைப்", "வோடும்", "யோடும்"]
# After a name ending in இ or ஐ the dative doubles க with no glide (அம்சி-க்கு).
DIRECT_ENDINGS = ["க்குப்", "க்குக்", "க்குச்", "க்குத்", "க்கும்", "க்கு"]
DIRECT_AFTER = set("ிீை")  # ி ீ ை
CONSONANT_ENDINGS = ["ுக்குப்", "ுக்குக்", "ுக்குச்", "ுக்குத்", "ுக்கு", "ிலிருந்து", "ினுடைய", "ுடைய", "ிடம்", "ோடு", "ின்", "ில்", "ும்", "ை",
                     "ையும்", "ுக்கும்", "ிலும்", "ினால்", "ால்", "ிலே", "ுடன்", "ோடே",
                     "ைவிட்டு", "ிலுள்ள", "ின்மேல்", "ுக்குள்", "ிலிருந்த",
                     "ைக்", "ைச்", "ைத்", "ைப்", "ோடும்"]
CONSONANTS = set("கஙசஞடணதநபமயரலவழளறனஜஷஸஹ")
VIRAMA = "்"


# The glide Tamil puts between a vowel-final name and an ending: ய after
# இ ஈ எ ஏ ஐ (வஸ்தி-யின்), வ after the others (அப்தா-வின்). A ய after ா is
# the name's own letter (அம்மிஷதாய் → அம்மிஷதாயின்), and so is a வ after இ.
Y_GLIDE_AFTER = set("ிீெேை")  # ி ீ ெ ே ை


def base_of(word: str) -> str:
    """The uninflected name for an inflected form, by the longest common
    ending that fits (ஆரோன்-ையும் before ஆரோனை-யும்)."""
    fits = [(len(e), "v", e) for e in VOWEL_ENDINGS if word.endswith(e) and len(word) - len(e) >= 2]
    fits += [(len(e), "d", e) for e in DIRECT_ENDINGS
             if word.endswith(e) and len(word) - len(e) >= 2 and word[-len(e) - 1] in DIRECT_AFTER]
    fits += [(len(e), "c", e) for e in CONSONANT_ENDINGS
             if word.endswith(e) and len(word) > len(e) + 1 and word[-len(e) - 1] in CONSONANTS]
    if not fits:
        return word
    _, kind, end = max(fits)
    stem = word[: -len(end)]
    if kind == "d":
        return stem
    if kind == "v":
        glide_ok = (stem[-1] in Y_GLIDE_AFTER) == end.startswith("ய")
        return stem if glide_ok else stem + end[0] + VIRAMA
    base = stem + VIRAMA
    # A short name doubles its last consonant before an ending
    # (நேபாத் → நேபாத்தின்): undo it.
    if len(base) >= 5 and base[-4] == base[-2] and base[-3] == VIRAMA:
        base = base[:-2]
    return base


def consonant_match(tamil: str, english: str) -> float:
    """Consonant-skeleton similarity, 0–1."""
    a, b = skeleton_ta(tamil), skeleton_en(english)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def same_start(tamil: str, english: str) -> bool:
    """Both start with a vowel, or both with a consonant. An English initial H
    before a vowel counts as a vowel: the IRV drops it (Habor ஆபோர்)."""
    e = english.lower()
    if e[:1] == "h" and e[1:2] in "aeiou":
        e = e[1:]
    return (tamil[:1] in "அஆஇஈஉஊஎஏஐஒஓஔ") == (e[:1] in "aeiou")


def sounds_like(tamil: str, english: str) -> float:
    """`consonant_match` plus 0.1 when both start alike (Abagtha அபக்தா, not
    Bigtha பிக்தா); used for ranking."""
    m = consonant_match(tamil, english)
    return m + (0.1 if m and same_start(tamil, english) else 0.0)


def neighbours(vid: str) -> tuple[str | None, str]:
    """The verse before and after, as entity-ingest's `with_neighbours`:
    Tamil often moves a clause across the verse boundary (Esther 1:10–11)."""
    chapter, v = vid.rsplit(".", 1)
    n = int(v)
    return (f"{chapter}.{n - 1}" if n > 1 else None), f"{chapter}.{n + 1}"


def window(vid: str, version: str) -> str:
    before, after = neighbours(vid)
    c = corpus(version)
    return " ".join(t for x in (before, vid, after) if x and (t := c.get(x)))


def candidates(verse_ids: list[str], version: str = repo.TAMIL_VERSION, top: int = 6,
               name: str | None = None) -> list[Candidate]:
    """Tamil word prefixes that recur across the verses (each with the verse
    either side) and are rare elsewhere in the version. For a name, a word
    whose consonants match the English name ranks higher: with one or two
    verses every word in them recurs equally."""
    texts = [t for v in verse_ids if (t := window(v, version))]
    if not texts:
        return []
    df, n_all = prefix_df(version)
    covered: Counter = Counter()
    spellings: dict[str, Counter] = {}
    for t in texts:
        words = TAMIL_WORD.findall(t)
        covered.update({w[:PREFIX] for w in words})
        for w in words:
            spellings.setdefault(w[:PREFIX], Counter())[w] += 1
    out = []
    for p, c in covered.items():
        idf = min(1.0, max(0.0, math.log(n_all / max(1, df[p]))) / 6)
        words = spellings[p].most_common(6)
        score = c / len(texts) * idf
        sounds = max((sounds_like(base_of(w), name) for w, _ in words), default=0.0) if name else 0.0
        if name:
            score *= 0.4 + sounds
        out.append(Candidate(p, c, score, words, sounds))
    out.sort(key=lambda x: (-x.score, -x.covered, x.prefix))
    return out[:top]


# ---- output ----

ANSI = {"en": "\033[1;33m", "cand": "\033[1;36m", "known": "\033[1;32m", "dim": "\033[2m", "off": "\033[0m"}


def _wrap(word: str, style: str, color: bool) -> str:
    return f"{ANSI[style]}{word}{ANSI['off']}" if color else f"[{word}]"


def mark_english(text: str, words: list[str], color: bool) -> str:
    if not words:
        return text
    alts = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.sub(rf"\b(?:{alts})\b", lambda m: _wrap(m[0], "en", color), text, flags=re.IGNORECASE)


def tamil_style(known: set[str], top: str | None):
    """Word → "known" (in names-ta.toml), "cand" (best candidate) or None."""

    def style(word: str) -> str | None:
        if word in known:
            return "known"
        if top and word.startswith(top):
            return "cand"
        return None

    return style


def mark_tamil(text: str, style, color: bool) -> str:
    return TAMIL_WORD.sub(lambda m: _wrap(m[0], s, color) if (s := style(m[0])) else m[0], text)


def tamil_rows(vid: str, version: str, style, always: bool = False) -> list[tuple[str, str]]:
    """(label, text): the verse, plus the verse either side when only that one
    holds a marked word, or always (a name with few verses)."""
    c = corpus(version)
    text = c.get(vid, "")
    rows = [("", text or "(no text)")]
    if always or not any(style(w) for w in TAMIL_WORD.findall(text)):
        before, after = neighbours(vid)
        for label, x in (("−1", before), ("+1", after)):
            t = c.get(x) if x else None
            if t and (always or any(style(w) for w in TAMIL_WORD.findall(t))):
                rows.append((f"{label} {x}", t))
    return rows


def terminal(lk: Lookup, english: str, limit: int, tcv: bool, color: bool) -> str:
    entry = repo.load_names().get(lk.query) if lk.kind == "name" else None
    cands = candidates(lk.verses, name=lk.query if lk.kind == "name" else None)
    few = lk.kind == "name" and len(lk.verses) <= 3
    style = tamil_style(set([entry["label"], *entry["forms"]]) if entry else set(), cands[0].prefix if cands else None)
    lines = [f"{lk.query} ({lk.kind}): {len(lk.verses)} verses; English {english}, Tamil {repo.TAMIL_VERSION}"
             + (" and TCV" if tcv else "")]
    if entry:
        state = "needs review" if entry.get("review") else "reviewed"
        lines.append(f"names-ta.toml: {entry['label']}  ({state}; forms {', '.join(entry['forms'][:8])})")
    if cands:
        lines.append("Tamil words shared by these verses (best first):")
        for c in cands:
            ws = ", ".join(f"{w}×{n}" for w, n in c.words)
            sounds = f"  sounds {c.sounds:.2f}" if lk.kind == "name" else ""
            lines.append(f"  {c.covered}/{len(lk.verses)} verses  score {c.score:.2f}{sounds}  {ws}")
    lines.append("")
    for vid in lk.verses[:limit]:
        en = repo.verse_text(vid, english) or "(no text)"
        lines.append(f"{vid}")
        lines.append(f"  EN  {mark_english(en, lk.english_terms, color)}")
        for version, tag in [(repo.TAMIL_VERSION, "TA "), *([("TCV", "TCV")] if tcv else [])]:
            for label, t in tamil_rows(vid, version, style, few):
                lines.append(f"  {tag} {'(' + label + ') ' if label else ''}{mark_tamil(t, style, color)}")
    if len(lk.verses) > limit:
        lines.append(f"… {len(lk.verses) - limit} more (--limit)")
    return "\n".join(lines)


def html_page(lk: Lookup, english: str, limit: int, tcv: bool) -> str:
    entry = repo.load_names().get(lk.query) if lk.kind == "name" else None
    cands = candidates(lk.verses, name=lk.query if lk.kind == "name" else None)
    few = lk.kind == "name" and len(lk.verses) <= 3
    top = cands[0].prefix if cands else None

    alts = "|".join(re.escape(html.escape(w)) for w in sorted(lk.english_terms, key=len, reverse=True))

    def mark_en(t: str) -> str:
        t = html.escape(t)
        return re.sub(rf"\b(?:{alts})\b", lambda m: f"<mark class=en>{m[0]}</mark>", t, flags=re.IGNORECASE) if alts else t

    style = tamil_style(set([entry["label"], *entry["forms"]]) if entry else set(), top)

    def mark_ta(t: str) -> str:
        return TAMIL_WORD.sub(lambda m: f"<mark class={s}>{m[0]}</mark>" if (s := style(m[0])) else m[0], html.escape(t))

    def ta_cell(vid: str, version: str) -> str:
        parts = [f"<div{' class=near' if label else ''}>{f'<small>{label}</small> ' if label else ''}{mark_ta(t)}</div>"
                 for label, t in tamil_rows(vid, version, style, few)]
        return f"<td lang=ta>{''.join(parts)}</td>"

    rows = []
    for vid in lk.verses[:limit]:
        cells = [f"<td class=ref>{vid}</td>",
                 f"<td>{mark_en(repo.verse_text(vid, english) or '')}</td>",
                 ta_cell(vid, repo.TAMIL_VERSION)]
        if tcv:
            cells.append(ta_cell(vid, "TCV"))
        rows.append("<tr>" + "".join(cells) + "</tr>")
    cand_html = "".join(
        f"<li><b>{c.covered}/{len(lk.verses)}</b> {html.escape(', '.join(f'{w} ×{n}' for w, n in c.words))}</li>" for c in cands
    )
    entry_html = ""
    if entry:
        state = "needs review" if entry.get("review") else "reviewed"
        entry_html = f"<p>names-ta.toml: <b lang=ta>{html.escape(entry['label'])}</b> ({state})</p>"
    heads = f"<th></th><th>{english}</th><th>{repo.TAMIL_VERSION}</th>" + ("<th>TCV</th>" if tcv else "")
    return f"""<!doctype html><meta charset=utf-8><title>{html.escape(lk.query)} · verses</title>
<style>
:root {{ --bg:#fff; --fg:#1b1b1b; --muted:#666; --line:#ddd; --en:#fde68a; --cand:#a5f3fc; --known:#bbf7d0; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141414; --fg:#eee; --muted:#999; --line:#333; --en:#7c5a00; --cand:#155e75; --known:#166534; }} }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.55 system-ui, "Noto Sans Tamil", sans-serif; margin:0 auto; padding:16px; max-width:1200px; }}
table {{ border-collapse:collapse; width:100%; }} td, th {{ border-top:1px solid var(--line); padding:8px; vertical-align:top; text-align:left; }}
.near {{ margin-top:6px; color:var(--muted); }} td.ref {{ color:var(--muted); white-space:nowrap; font-size:13px; }}
mark {{ color:inherit; border-radius:3px; padding:0 2px; }} mark.en {{ background:var(--en); }} mark.cand {{ background:var(--cand); }} mark.known {{ background:var(--known); }}
</style>
<h1>{html.escape(lk.query)} <small>({lk.kind}, {len(lk.verses)} verses)</small></h1>
{entry_html}
<p>Tamil words shared by these verses: <mark class=cand>best candidate</mark>, <mark class=known>in names-ta.toml</mark></p>
<ol>{cand_html}</ol>
<table><tr>{heads}</tr>{''.join(rows)}</table>"""


def accept_name(name: str, label: str, verse_ids: list[str], forms: list[str] | None = None) -> dict:
    """Write a reviewed entry: the label and every word in the name's IRV and
    TCV verses that starts with the label less its last letter (or the forms
    given)."""
    label = " ".join(label.split())
    if not TAMIL_NAME.fullmatch(label):
        raise ValueError(f"{label!r} is not Tamil (one word, or words separated by spaces)")
    if forms is None:
        # Words (or, for a name of several words, phrases) in the verses that
        # start like the label less its last letter.
        stem = label[: max(3, len(label) - 1)]
        pat = re.compile(r"\s+".join(re.escape(w) for w in stem.split(" ")) + "[஀-௿]*")
        found: Counter = Counter()
        for version in (repo.TAMIL_VERSION, "TCV"):
            for v in verse_ids:
                text = window(v, version)
                found.update(" ".join(m[0].split()) for m in pat.finditer(text)
                             if m.start() == 0 or not TAMIL_WORD.match(text[m.start() - 1]))
        forms = [w for w, _ in found.most_common()]
        if not forms:
            raise ValueError(f"nothing in {name}'s verses (or the verse either side) starts with {stem}; give the forms")
    else:
        # Forms given by hand must be in the text, as the build requires:
        # say so now rather than fail `pnpm content` later.
        forms = [" ".join(unicodedata.normalize("NFC", f).split()) for f in forms if f.strip()]
        texts = [window(v, version) for version in (repo.TAMIL_VERSION, "TCV") for v in verse_ids]
        texts = [" ".join(unicodedata.normalize("NFC", t).split()) for t in texts]
        missing = [f for f in forms
                   if not any(re.search(rf"(?<![஀-௿]){re.escape(f)}(?![஀-௿])", t) for t in texts)]
        if missing:
            raise ValueError(f"not in {name}'s verses (or the verse either side): {', '.join(missing)}")
    entry = {"label": label, "forms": forms, "confidence": 1.0, "n": len(verse_ids)}
    repo.save_name(name, entry)
    return entry
