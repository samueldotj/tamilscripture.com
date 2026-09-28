"""Tamil drafts of the Bible commentaries (docs/feature_commentary_translation.md).

The English is in the bible-commentaries repository, next to this one:
en/{source}/{BOOK}/{chapter}.json, one file per chapter, each a list of units
(one comment on a verse or range, a chapter's introduction, or a book's).
A unit is translated like a dictionary article: the same client, glossary,
names, IRV verses, repair turn and Message Batches, with its own prompt and
checks. Drafts are written beside the English, one file per chapter:
ta/{source}/{BOOK}/{chapter}.json (ta-ecf/ for the Early Church Fathers, whose
terms are narrower than the public domain).
"""

from __future__ import annotations

import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from functools import cache
from pathlib import Path

from . import checks, client, prompts, repo, translate
from .checks import Problem
from .client import Reply
from .repo import Name, Term

ROOT = Path(os.environ.get("TRANSLATE_COMMENTARIES") or repo.ROOT.parent / "bible-commentaries")
WORK = repo.WORK / "commentary"
# Where drafts are written: the repository (ta/, ta-ecf/), or a pilot folder.
DRAFTS_ROOT: Path | None = None
REPORT = WORK / "report.jsonl"
FLAGGED = WORK / "flagged"
_WRITE_LOCK = threading.Lock()  # units of one chapter share a draft file

PROMPT_VERSION = "c1"

SOURCES = {
    "geneva": "the Geneva Bible notes (1599): short marginal notes on words of a verse, each with its "
              "letter or number; its anchor runs from the note's mark in the verse to the next mark or "
              "punctuation, so the note may explain only the first word or words of it: give as the Tamil "
              "anchor the IRV words the note actually explains",
    "henry": "Matthew Henry, Commentary on the Whole Bible (1708-1710): long devotional and practical "
             "exposition, organised with outline numbers (I., 1., (1.))",
    "calvin": "John Calvin's commentaries, in the English of the Calvin Translation Society (1840s-1850s), "
              "translated from Calvin's Latin and French; footnotes by those editors",
    "poole": "Matthew Poole, Annotations upon the Holy Bible (1683-1685): notes on the words of each verse, "
             "each opening with the words it explains (anchor)",
    "trapp": "John Trapp, A Commentary upon the Old and New Testaments (1647-1656): pithy, witty notes on the "
             "words of each verse, full of proverbs, Latin tags and allusions; footnotes give his Latin and Greek sources",
    "ecf": "quotations from the church fathers (1st to 10th century) on each verse, each with the father's name "
           "and the work quoted, in 19th-century and later English translations",
}

STYLE = """\
You translate Bible commentaries written in English between the 16th and 19th centuries into Tamil for tamilscripture.com, a Tamil Bible study site whose readers are Tamil Protestant Christians in the Reformed tradition. The site's Bible is the Indian Revised Version (IRV, 2019), and the Tamil must read as though written for readers of the IRV. The site shows each comment beside the IRV text of the verses it explains.

The commentaries:
{sources}

How to translate:
- Translate faithfully and completely. Do not summarise, explain, soften, modernise the theology, add to, or correct what the commentator says, even where you would put it differently, and including his polemics. Keep his reasoning, his order, and his outline numbering (I., 1., (1.)).
- Write formal written Tamil in the register of the IRV and of Tamil Protestant teaching, not colloquial Tamil and not Sanskritised or Hindu religious vocabulary where the IRV uses another word. The English is old: translate what it means ("prevent" = go before, "conversation" = conduct, "let" = hinder), in present-day formal Tamil; do not imitate its archaic style.
- The verses explained: their IRV text is supplied. Where the commentator quotes or paraphrases the words of the verse, use the IRV's wording. Where his point rests on the wording of his own English Bible or his own translation and the IRV differs, translate his words so his point still stands.
- Anchors: a paragraph may have "anchor", the words of the verse it explains, in old English. Give "anchor" in Tamil as the IRV's words for that phrase in the verse; if the IRV has no matching words, translate the anchor.
- Theological terms: use the Tamil given in the glossary with each unit whenever the English term or one of its forms occurs, inflecting it as the sentence needs. Never use a rendering listed under "avoid". For a theological term not in the glossary, use the word the IRV uses in the verses where that idea occurs; if the IRV has none, choose the term established in Tamil Protestant (Reformed) teaching.
- Names of people and places: use the Tamil names given with each unit. Otherwise use the spelling the IRV uses; transliterate only a name the IRV does not contain.
- The divine name: follow the IRV.
- Scripture references: each paragraph lists its references ("refs"), with the verse id of each (JHN.3.16 = John 3:16). Write every reference with the book's Tamil name from the list below and chapter:verse in Arabic numerals, whatever form the English uses ("Mal. ii. 7" → மல்கியா 2:7, "Ro 3:31" → ரோமர் 3:31). A reference to a verse of the chapter being explained may stay as a verse number ("ver. 22-36" → 22-36 வசனங்கள்). Keep every reference.
- Latin, Greek and Hebrew: keep quotations and words as written, in their own script. Where the English gives no translation of a Latin or Greek quotation, add a Tamil rendering in brackets after it. Keep the marker [Hebrew] as it is.
- Footnote markers such as {{a}} or {{55}} stay in the text exactly where they are. Footnotes (marked "footnote": true) are translated like the rest.
- Headings (marked "heading": true) and titles are translated as short headings.
- Produce plain text only: no HTML, Markdown or notes of your own.

Output: JSON with the unit's title in Tamil (an empty string when the unit has none) and one Tamil paragraph for every English paragraph, with the same "id" values in the same order, and "anchor" in Tamil for every paragraph that has one."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "paragraphs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "text": {"type": "string"}, "anchor": {"type": "string"}},
                "required": ["id", "text"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "paragraphs"],
    "additionalProperties": False,
}

MAX_EXPLAINED = 60  # IRV verses of the unit itself
MAX_CITED = 40  # IRV verses cited elsewhere in the part


# ---- the English ----


def book_order() -> dict[str, int]:
    return {b.code: b.order for b in repo.books()}


def chapter_files(source: str) -> list[Path]:
    """en/{source}/{BOOK}/{intro,N}.json in Bible order."""
    order = book_order()
    files = list((ROOT / "en" / source).glob("*/*.json"))

    def key(p: Path):
        return (order.get(p.parent.name, 99), 0 if p.stem == "intro" else int(p.stem))

    return sorted(files, key=key)


def read_chapter(path: Path) -> list[dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return [{**u, "source": doc["source"], "book": doc["book"], "chapter": doc["chapter"]} for u in doc["units"]]


def units(source: str):
    for path in chapter_files(source):
        yield from read_chapter(path)


def parse_range(rid: str) -> tuple[str, int, int, int]:
    """`JHN.3.1-21` → (JHN, 3, 1, 21); `JHN.3` → (JHN, 3, 0, 0); `JHN` → (JHN, 0, 0, 0).
    A range into the next chapter keeps only its first verse."""
    m = re.fullmatch(r"([1-4A-Z]{3})(?:\.(\d+)(?:\.(\d+)(?:-(\d+)(?:\.(\d+))?)?)?)?", rid)
    if not m:
        raise ValueError(f"not a verse range: {rid}")
    book, ch, v1, v2, v3 = m[1], int(m[2] or 0), int(m[3] or 0), m[4], m[5]
    end = v1 if v2 is None or v3 is not None else int(v2)
    return book, ch, v1, max(end, v1)


def load_unit(unit_id: str) -> dict:
    """`henry/JHN.3.1-21` → the unit, with its source, book and chapter."""
    source, rid = unit_id.split("/", 1)
    book, ch, _, _ = parse_range(rid)
    path = ROOT / "en" / source / book / ("intro.json" if ch == 0 else f"{ch}.json")
    if not path.exists():
        raise SystemExit(f"no {path}")
    for u in read_chapter(path):
        if u["id"] == unit_id:
            return u
    raise SystemExit(f"no unit {unit_id} in {path}")


def english_words(u: dict) -> int:
    return len(" ".join([u.get("title") or "", *(p["text"] for p in u["paragraphs"]),
                         *(p.get("anchor", "") for p in u["paragraphs"])]).split())


# ---- drafts ----


def draft_folder(source: str) -> str:
    return "ta-ecf" if source == "ecf" else "ta"


def draft_path(u: dict) -> Path:
    ch = u["chapter"]
    base = DRAFTS_ROOT or ROOT
    return base / draft_folder(u["source"]) / u["source"] / u["book"] / ("intro.json" if ch == 0 else f"{ch}.json")


def load_draft(u: dict) -> dict | None:
    p = draft_path(u)
    if not p.exists():
        return None
    return next((d for d in json.loads(p.read_text(encoding="utf-8"))["units"] if d["id"] == u["id"]), None)


def write_draft(u: dict, draft: dict) -> Path:
    """Put this unit's draft in its chapter file, in the English order."""
    p = draft_path(u)
    with _WRITE_LOCK:
        doc = (json.loads(p.read_text(encoding="utf-8")) if p.exists()
               else {"source": u["source"], "book": u["book"], "chapter": u["chapter"], "lang": "ta", "units": []})
        others = [d for d in doc["units"] if d["id"] != u["id"]]
        en_path = ROOT / "en" / u["source"] / u["book"] / p.name
        order = {x["id"]: k for k, x in enumerate(read_chapter(en_path))} if en_path.exists() else {}
        doc["units"] = sorted([*others, draft], key=lambda d: order.get(d["id"], 1 << 30))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return p


def is_current(u: dict, force: bool = False) -> bool:
    if force:
        return False
    d = load_draft(u)
    return bool(d and d.get("source_hash") == u["hash"] and d.get("generator", {}).get("prompt_version") == PROMPT_VERSION)


# ---- the request ----


@cache
def books_block() -> str:
    return "Book ids and Tamil book names (IRV):\n" + "\n".join(
        f"- {b.code} {b.name_en} → {b.name_ta}" for b in repo.books()
    )


def system_blocks() -> list[dict]:
    sources = "\n".join(f"- {k}: {v}" for k, v in SOURCES.items())
    text = "\n\n".join([STYLE.format(sources=sources), books_block()])
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


@dataclass
class Context:
    model: str = client.DEFAULT_MODEL
    effort: str = client.DEFAULT_EFFORT
    terms: dict = field(default_factory=repo.reviewed_terms)
    names: dict = field(default_factory=repo.reviewed_names)
    system: list = field(init=False)

    def __post_init__(self):
        self.system = system_blocks()


def verse_ids(rid: str, cap: int = 30) -> list[str]:
    """The verses of a range, at most `cap`; a whole chapter or book gives none."""
    book, ch, v1, v2 = parse_range(rid)
    if not v1:
        return []
    return [f"{book}.{ch}.{v}" for v in range(v1, min(v2, v1 + cap - 1) + 1)]


def explained_verses(u: dict) -> list[str]:
    return verse_ids(u["range"], MAX_EXPLAINED) if u["kind"] == "passage" else []


def cited_verses(u: dict, paragraphs: list[dict]) -> list[str]:
    own = set(explained_verses(u))
    out: list[str] = []
    for p in paragraphs:
        for r in p.get("refs", []):
            try:
                ids = verse_ids(r["ref"], 6)
            except ValueError:
                continue
            for vid in ids:
                if vid not in own and vid not in out:
                    out.append(vid)
    return out[:MAX_CITED]


def label(u: dict) -> str:
    book, ch, v1, v2 = parse_range(u["range"])
    name = next((b.name_en for b in repo.books() if b.code == book), book)
    if not ch:
        return f"{name}: the book's introduction"
    if not v1:
        return f"{name} {ch}: the chapter's introduction"
    return f"{name} {ch}:{v1}" + (f"-{v2}" if v2 > v1 else "")


def chunks(u: dict) -> list[list[dict]]:
    """Paragraph groups of at most prompts.CHUNK_WORDS words; a footnote stays
    with the paragraph before it."""
    out: list[list[dict]] = [[]]
    words = 0
    for p in u["paragraphs"]:
        n = len(p["text"].split())
        if out[-1] and words + n > prompts.CHUNK_WORDS and not p.get("footnote"):
            out.append([])
            words = 0
        out[-1].append(p)
        words += n
    return out


def user_message(u: dict, paragraphs: list[dict], part: tuple[int, int], names: dict[str, Name],
                 terms: dict[str, Term] | None) -> str:
    english = " ".join([u.get("title") or "", *(p["text"] for p in paragraphs),
                        *(p.get("anchor", "") for p in paragraphs)])
    sections = [f"Commentary: {u['source']}. This unit: {label(u)}."]

    if terms and (block := prompts.glossary_block(checks.terms_in(english, terms))):
        sections.append(block)
    found = checks.names_in(english, names)
    if found:
        sections.append("Tamil names in the IRV for names in this unit:\n"
                        + "\n".join(f"- {n.en} → {', '.join(dict.fromkeys([n.label, *n.forms[:4]]))}" for n in found))

    own = [(vid, repo.verse_text(vid)) for vid in explained_verses(u)]
    own = [(vid, t) for vid, t in own if t]
    if own:
        sections.append("IRV text of the verses explained:\n" + "\n".join(f"- {vid}: {t}" for vid, t in own))
    cited = [(vid, repo.verse_text(vid)) for vid in cited_verses(u, paragraphs)]
    cited = [(vid, t) for vid, t in cited if t]
    if cited:
        sections.append("IRV text of other verses cited:\n" + "\n".join(f"- {vid}: {t}" for vid, t in cited))

    k, n = part
    if n > 1:
        sections.append(f"This is part {k} of {n} of a long unit; translate only these paragraphs. "
                        "Give the title every time.")

    keep = ("anchor", "verse", "heading", "footnote", "label", "refs")
    payload = {
        "id": u["id"],
        "title": u.get("title") or "",
        "paragraphs": [{"id": p["id"], "text": p["text"], **{k2: p[k2] for k2 in keep if p.get(k2)}} for p in paragraphs],
    }
    sections.append("Unit:\n" + json.dumps(payload, ensure_ascii=False, indent=1))
    return "\n\n".join(sections)


def requests_for(u: dict, ctx: Context) -> list[tuple[str, dict]]:
    parts = chunks(u)
    out = []
    for k, paras in enumerate(parts, 1):
        msg = user_message(u, paras, (k, len(parts)), ctx.names, ctx.terms)
        out.append((translate.custom_id(u["id"], k),
                    client.params(ctx.system, [{"role": "user", "content": msg}], ctx.model, ctx.effort, OUTPUT_SCHEMA)))
    return out


# ---- checks ----

# Common English words: an untranslated English sentence has several; Latin
# quotations, which are kept, have none or one ("in").
ENGLISH_WORDS = {"the", "and", "of", "to", "that", "is", "which", "was", "his", "with", "for", "not", "be", "he",
                 "they", "it", "as", "by", "are", "this", "from", "have", "their", "will", "shall", "unto", "him",
                 "them", "but", "who", "we", "our", "you", "your", "hath", "doth", "thou", "thee"}
FOOTNOTE_MARK = re.compile(r"\{\w{1,3}\}")


def english_left(tamil: str) -> str | None:
    for m in checks.ENGLISH_RUN.finditer(tamil):
        if sum(w.lower() in ENGLISH_WORDS for w in re.findall(r"[A-Za-z]+", m[0])) >= 2:
            return m[0]
    return None


def ref_token(ref: str, u: dict, english: str = "") -> str | None:
    """The least a Tamil paragraph must contain for this reference: the verse
    alone for a verse of the unit's own chapter, the chapter alone for a whole
    chapter (also when the English names only the chapter, "ch. xvi.", though
    the import gave it verse 1), else chapter:verse. `ref_found` accepts the
    fuller chapter:verse form too."""
    try:
        book, ch, v1, _ = parse_range(ref)
    except ValueError:
        return None
    if not ch:
        return None
    if not v1 or (english and not re.search(r"\d", english)):
        return str(ch)
    if book == u["book"] and ch == u["chapter"]:
        return str(v1)
    return f"{ch}:{v1}"


def ref_found(ref: str, u: dict, english: str, tamil: str) -> bool:
    tok = ref_token(ref, u, english)
    if tok is None:
        return True
    forms = [tok]
    try:
        _, ch, v1, _ = parse_range(ref)
    except ValueError:
        return True
    if v1:
        forms.append(f"{ch}:{v1}")
        # Written in the English as a continuation ("Romans 5:8, 10"): the verse alone.
        if f"{ch}:{v1}" not in english:
            forms.append(str(v1))
    if re.search(r"-\d+\.\d+$", ref):  # a range across chapters ("ch. xiv. and ch. xv. 1-14")
        forms.append(str(ch))
    return any(re.search(rf"(?<![\d:]){re.escape(f)}(?!\d)", tamil) for f in forms)


def check_unit(u: dict, title: str, paragraphs: list[dict], terms: dict[str, Term],
               names: dict[str, Name], english: list[dict] | None = None) -> list[Problem]:
    """Every problem with a draft of `u` (or of the paragraphs `english` of it)."""
    out: list[Problem] = []
    if u.get("title") and (why := checks.check_text(title)):
        out.append(Problem("title", why))

    en = {p["id"]: p for p in (english if english is not None else u["paragraphs"])}
    got = [p["id"] for p in paragraphs]
    if got != list(en):
        missing = [i for i in en if i not in got]
        extra = [i for i in got if i not in en]
        out.append(Problem("paragraphs", f"ids differ from the English (missing {missing}, unexpected {extra})"))

    for p in paragraphs:
        e = en.get(p["id"])
        if e is None:
            continue
        ta, where = p["text"], p["id"]
        if why := checks.check_text(ta):
            if not (why == "no Tamil script" and checks.untranslatable(e["text"])):
                out.append(Problem(where, why))
            continue
        if e.get("anchor"):
            anchor = (p.get("anchor") or "").strip()
            if not anchor:
                out.append(Problem(where, "anchor missing"))
            elif (why := checks.check_text(anchor)) and not checks.untranslatable(e["anchor"]):
                out.append(Problem(where, f"anchor {why}"))
        if left := english_left(ta):
            out.append(Problem(where, f"untranslated English: {left!r}"))
        missing = sorted(set(checks.VERSE_NUM.findall(e["text"])) - set(checks.VERSE_NUM.findall(ta)))
        if missing:
            out.append(Problem(where, f"verse references missing: {', '.join(missing)}"))
        lost = [r["text"] for r in e.get("refs", []) if not ref_found(r["ref"], u, r["text"], ta)]
        if lost:
            out.append(Problem(where, f"references missing: {', '.join(dict.fromkeys(lost))}"))
        marks = sorted(set(FOOTNOTE_MARK.findall(e["text"])) - set(FOOTNOTE_MARK.findall(ta)))
        if marks:
            out.append(Problem(where, f"footnote markers missing: {' '.join(marks)}"))
        if "[Hebrew]" in e["text"] and "[Hebrew]" not in ta:
            out.append(Problem(where, "marker [Hebrew] missing"))
        ratio = len(ta) / max(1, len(e["text"]))
        if len(e["text"]) > 80 and not e.get("footnote") and not 0.6 <= ratio <= 3.5:
            out.append(Problem(where, f"length {ratio:.1f}× the English; likely something left out or added"))
        for t in checks.terms_in(e["text"], terms):
            if not checks.uses_any(ta, t.forms):
                out.append(Problem(where, f"glossary: “{t.en}” should be {t.ta}"))
            for bad in checks.usable_avoid(t, terms):
                stem = bad[:-1] if bad.endswith("்") and len(bad) > 3 else bad
                if re.search(rf"(?<![஀-௿]){re.escape(stem)}", ta):
                    out.append(Problem(where, f"glossary: “{bad}” is not used for “{t.en}”; use {t.ta}"))
        for n in checks.names_in(e["text"], names):
            if not checks.uses_any(ta, n.forms):
                out.append(Problem(where, f"name: {n.en} is {n.label} in the IRV"))
    return out


# ---- running ----


def part_problems(u: dict, paras: list[dict], reply: Reply, ctx: Context) -> list[Problem]:
    if reply.data is None:
        return [Problem("response", reply.error or "no reply")]
    return check_unit(u, reply.data.get("title", ""), reply.data.get("paragraphs", []), ctx.terms, ctx.names, paras)


def repair_request(u: dict, paras: list[dict], reply: Reply, problems: list[Problem],
                   original: dict, ctx: Context) -> dict:
    """The repair turn for one part. When every problem is in a paragraph or
    the title, only the flagged paragraphs go back: their English with the
    glossary, names and verses they need, the earlier Tamil of them, and the
    problems; the answer holds those paragraphs alone (merge_repair puts them
    back). Otherwise (no answer, paragraph ids wrong) the whole part is asked
    again, or repaired with the first answer."""
    ids = {p["id"] for p in paras}
    where = {p.where for p in problems}
    if reply.data is None or not where <= ids | {"title"}:
        if not reply.text:
            return original
        return {**original, "messages": original["messages"] + [
            {"role": "assistant", "content": reply.text},
            {"role": "user", "content": prompts.repair_message(problems)},
        ]}
    bad = [p for p in paras if p["id"] in where]
    earlier = {"title": reply.data.get("title", ""),
               "paragraphs": [p for p in reply.data.get("paragraphs", []) if p.get("id") in where]}
    msg = "\n\n".join([
        user_message(u, bad, (1, 1), ctx.names, ctx.terms),
        "Your earlier Tamil of these paragraphs:\n" + json.dumps(earlier, ensure_ascii=False, indent=1),
        "It has these problems:\n" + "\n".join(f"- {p}" for p in problems),
        "Return the corrected JSON: the title and these paragraphs only, with the same ids.",
    ])
    return client.params(ctx.system, [{"role": "user", "content": msg}], ctx.model, ctx.effort, OUTPUT_SCHEMA)


def merge_repair(reply: Reply, fixed: Reply) -> Reply:
    """The first answer with the repaired paragraphs (and title) in place."""
    if fixed.data is None:
        return reply
    if reply.data is None:
        return fixed
    new = {p.get("id"): p for p in fixed.data.get("paragraphs", [])}
    data = {**reply.data,
            "title": (fixed.data.get("title") or "").strip() or reply.data.get("title", ""),
            "paragraphs": [new.get(p.get("id"), p) for p in reply.data.get("paragraphs", [])]}
    return Reply(data, None, json.dumps(data, ensure_ascii=False))


def repair_direct(u: dict, paras: list[dict], reply: Reply, problems: list[Problem],
                  original: tuple[str, dict], ctx: Context) -> Reply:
    cid, req = original
    fixed = client.run_direct(repair_request(u, paras, reply, problems, req, ctx), cid + "-r")
    return merge_repair(reply, fixed)


def finish(u: dict, replies: list[Reply], ctx: Context, allow_repair: bool) -> translate.Outcome:
    """Check each part, repair once if allowed, and write the draft unless a
    problem the site would reject remains."""
    parts = chunks(u)
    reqs = requests_for(u, ctx) if allow_repair else []
    first = [part_problems(u, paras, r, ctx) for paras, r in zip(parts, replies)]
    final = list(replies)
    todo = [k for k, ps in enumerate(first) if ps and allow_repair]
    if todo:
        with ThreadPoolExecutor(max_workers=len(todo)) as pool:
            for k, r in zip(todo, pool.map(lambda k: repair_direct(u, parts[k], replies[k], first[k], reqs[k], ctx), todo)):
                final[k] = r
    problems: list[Problem] = []
    for k, paras in enumerate(parts):
        problems += part_problems(u, paras, final[k], ctx) if k in todo else first[k]

    written = not any(translate.is_hard(p) for p in problems)
    if written:
        title = next((r.data["title"].strip() for r in final if r.data and r.data.get("title")), "")
        paras = []
        for r in final:
            for p in r.data["paragraphs"]:
                if checks.check_text(p["text"]) is not None:
                    continue  # nothing to translate ("538"): the site shows the English
                d = {"id": p["id"], "text": p["text"].strip()}
                if (p.get("anchor") or "").strip():
                    d["anchor"] = p["anchor"].strip()
                paras.append(d)
        draft = {"id": u["id"], "source_hash": u["hash"],
                 "generator": {"name": "claude", "model": ctx.model, "prompt_version": PROMPT_VERSION,
                               "generated_at": date.today().isoformat()},
                 "paragraphs": paras}
        if u.get("title") and title:
            draft = {**draft, "title": title}
        write_draft(u, draft)
    record(u, written, problems, final)
    return translate.Outcome(u["id"], written, problems)


def record(u: dict, written: bool, problems: list[Problem], replies: list[Reply]) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    with translate._REPORT_LOCK, open(REPORT, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"id": u["id"], "written": written, "problems": [str(p) for p in problems]},
                           ensure_ascii=False) + "\n")
    path = FLAGGED / (u["id"].replace("/", "__") + ".json")
    if problems:
        FLAGGED.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([r.text for r in replies], ensure_ascii=False), encoding="utf-8", newline="\n")
    elif path.exists():
        path.unlink()


def translate_direct(u: dict, ctx: Context) -> translate.Outcome:
    reqs = requests_for(u, ctx)
    if len(reqs) == 1:
        replies = [client.run_direct(reqs[0][1], reqs[0][0])]
    else:
        with ThreadPoolExecutor(max_workers=len(reqs)) as pool:
            replies = list(pool.map(lambda r: client.run_direct(r[1], r[0]), reqs))
    return finish(u, replies, ctx, allow_repair=True)
