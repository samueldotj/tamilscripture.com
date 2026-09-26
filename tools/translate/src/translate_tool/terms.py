"""The theological glossary, data/entities/glossary-theology-ta.toml
(docs/feature_dictionary_translation.md §3): seed terms, the IRV evidence for
each, Claude's proposal (`translate ai-terms`), and the file the translator
reads. Every entry stays `review = true` until the owner approves it on the
review page (`translate review-terms --web`); only approved entries reach the
translator.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from functools import cache
from pathlib import Path

from . import checks, client, repo, review

SEED = Path(__file__).resolve().parents[2] / "seed" / "terms.toml"
LOG = repo.WORK / "ai-terms.jsonl"
PROMPT_VERSION = "terms-1"  # bump when SYSTEM or the message layout changes
VERSES_PER_TERM = 6
GROUP_TERMS = 8
GROUP_VERSES = 40


# ---- seed terms and their evidence ----


@dataclass
class Seed:
    en: str
    also: list[str]
    group: str
    curated: bool  # no single Bible word expected (Trinity, sacrament)

    @property
    def key(self) -> str:
        return repo.glossary_key(self.en)

    @property
    def forms_en(self) -> list[str]:
        return [self.en, *self.also]


def load_seed(path: Path | None = None) -> list[Seed]:
    with open(path or SEED, "rb") as f:
        raw = tomllib.load(f)
    out = []
    for group, g in raw.items():
        for line in g.get("terms", []):
            en, _, rest = line.partition("|")
            also = [a.strip() for a in rest.split(",") if a.strip()]
            out.append(Seed(en.strip(), also, group, bool(g.get("curated"))))
    return out


def _word_key(w: str) -> str:
    """Lowercase, except words in capitals (LORD, the BSB's YHWH), kept apart."""
    w = w.strip(".,;:'’\"")
    return w if w.isupper() and len(w) > 1 else w.lower()


@cache
def _word_numbers() -> dict[str, Counter]:
    """English word (see _word_key) → Counter of the Strong's numbers the BSB tags it with."""
    out: dict[str, Counter] = {}
    for num, rows in repo.strongs_index().by_number.items():
        for _, words in rows:
            for w in words.split():
                out.setdefault(_word_key(w), Counter())[num] += 1
    return out


def strongs_for(seed: Seed) -> list[str]:
    """The Strong's numbers the BSB mostly uses for the term's single-word
    forms: each with at least 2 hits and a quarter of the best one's."""
    counts: Counter = Counter()
    for form in seed.forms_en:
        if " " not in form:
            counts.update(_word_numbers().get(_word_key(form), Counter()))
    if not counts:
        return []
    top = counts.most_common(1)[0][1]
    return [n for n, c in counts.most_common(6) if c >= max(2, top / 4)]


def _spread(ids: list[str], k: int) -> list[str]:
    """k verse ids spread across the list (so not all from one book)."""
    ids = sorted(dict.fromkeys(ids), key=review.verse_order)
    if len(ids) <= k:
        return ids
    step = len(ids) / k
    return [ids[int(i * step)] for i in range(k)]


def verses_for(seed: Seed, numbers: list[str]) -> list[str]:
    """Verses showing how the IRV renders the term: those where the BSB tags
    one of its numbers on one of its words, or, for a phrase, the KJV verses
    that contain it."""
    forms = {_word_key(f) for f in seed.forms_en if " " not in f}
    ids = []
    for n in numbers:
        for vid, words in repo.strongs_index().verses(n):
            if forms & {_word_key(w) for w in words.split()}:
                ids.append(vid)
    if not ids:
        kjv = review.corpus("KJV")
        ids = [vid for vid, t in kjv.items() if any(checks.mentions(t, f) for f in seed.forms_en)]
    return _spread(ids, VERSES_PER_TERM)


@cache
def _articles() -> list[tuple[str, str, str]]:
    """(article id, English text, the text lowercased) for every dictionary article."""
    out = []
    for x in repo.articles_index():
        a = repo.load_article(x["id"])
        text = " ".join(p["text"] for p in a["paragraphs"]).replace("’", "'")
        out.append((a["id"], text, text.lower()))
    return out


def in_articles(seed: Seed) -> tuple[int, str]:
    """How many articles use the term, and one sentence that does."""
    return _in_articles(tuple(seed.forms_en))


@cache
def _in_articles(forms: tuple[str, ...]) -> tuple[int, str]:
    n, example = 0, ""
    quick = [f.lower().replace("’", "'") for f in forms]
    for _, text, low in _articles():
        if not any(q in low for q in quick):
            continue
        if any(checks.mentions(text, f) for f in forms):
            n += 1
            if not example:
                for sentence in re.split(r"(?<=[.;])\s+", text):
                    if any(checks.mentions(sentence, f) for f in forms) and 40 < len(sentence) < 300:
                        example = sentence
                        break
    return n, example


@dataclass
class Evidence:
    seed: Seed
    strongs: list[str]
    verses: list[str]
    articles: int
    example: str
    entry: dict = field(default_factory=dict)  # the glossary entry now, if any


def evidence(seeds: list[Seed]) -> list[Evidence]:
    glossary = load_file()
    out = []
    for s in seeds:
        nums = strongs_for(s)
        n, ex = in_articles(s)
        out.append(Evidence(s, nums, verses_for(s, nums), n, ex, glossary.get(s.key, {})))
    return out


# ---- the glossary file ----


def load_file(path: Path | None = None) -> dict[str, dict]:
    """Glossary key → the raw entry (with its English as `en`)."""
    path = path or repo.GLOSSARY
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    return {repo.glossary_key(en): {**e, "en": en} for en, e in raw.items() if isinstance(e, dict)}


HEADER = """\
# Theological glossary for the Tamil dictionary drafts (docs/feature_dictionary_translation.md §3).
# English term → the Tamil the translator must use. `forms` are inflections that
# count as using it; `avoid` lists renderings a draft must not use; `source` is
# "irv" (the IRV's own word, see `verses` and `strongs`) or "curated" (no single
# Bible word; the owner's choice). Proposed by `translate ai-terms`, approved on
# `translate review-terms --web`; entries with `review = true` are not used yet.
# Licence: CC BY 4.0 (tamilscripture.com contributors).
"""

_ORDER = ["ta", "forms", "also", "avoid", "source", "strongs", "verses", "group", "note", "status", "review"]


def _value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "[" + ", ".join(repo.toml_str(str(x)) for x in v) + "]"
    return repo.toml_str(str(v))


def save_file(entries: dict[str, dict], path: Path | None = None) -> None:
    """Write every entry, sorted, one table per term."""
    path = path or repo.GLOSSARY
    parts = [HEADER]
    for key in sorted(entries, key=str.lower):
        e = entries[key]
        lines = [f"[{repo.toml_str(e['en'])}]"]
        for k in _ORDER:
            v = e.get(k)
            if v in (None, "", []) or (k == "review" and not v):
                continue
            lines.append(f"{k} = {_value(v)}")
        parts.append("\n".join(lines))
    path.write_text("\n\n".join(parts) + "\n", encoding="utf-8", newline="\n")


def save_entry(key: str, entry: dict, path: Path | None = None) -> None:
    entries = load_file(path)
    entries[key] = entry
    save_file(entries, path)


# ---- asking Claude ----

SYSTEM = """\
You help build the theological glossary for translating English Bible dictionary articles (Easton's, Smith's, the Aquifer Open Bible Dictionary) into Tamil for tamilscripture.com. The site's Bible is the Indian Revised Version (IRV, Tamil, 2019), and its readers are Tamil Protestant Christians in the Reformed tradition. The glossary fixes one Tamil rendering per English term so every article uses the same word.

For each English term you are given its other English forms, how many dictionary articles use it and one sentence that does, the Strong's numbers the BSB tags on it, and verses in English (KJV) and in the IRV. The verse before and after each is included: the IRV often moves a clause into the neighbouring verse, so look there when a verse seems to lack the word.

- If the IRV has a word or phrase for the term in these verses, give it as `ta` in its base form (the uninflected noun, or for a verb the form a Tamil dictionary would list), copied from the IRV's spelling; set `source` to "irv". In `forms` list the inflected spellings of it that appear in the IRV verses given, copied exactly.
- The dictionary sense decides: pick the IRV word that renders the term in its theological sense, not a word for a different sense in the same verse.
- If the IRV renders the term differently in different places, choose the rendering that fits the dictionaries' theological use, and say in `note` which other renderings the IRV uses.
- For a term with no single Bible word (Trinity, sacrament, total depravity, Calvinism), give the Tamil established in Tamil Protestant, and specifically Reformed, teaching; set `source` to "curated", `forms` to its likely inflections or empty.
- `avoid`: Tamil renderings a translator might reach for that are wrong here: the TCV's or Roman Catholic usage where it differs, Hindu or Sanskrit religious words the IRV does not use for this, or a word for a different sense. Leave it empty when there is none.
- Answer for every term, in the order given, with the term exactly as written.

`confidence` is "high" only when the IRV's word is plain in the verses (or, for a curated term, the Tamil is well established). Use `note` for one or two short sentences a reviewer should know (in English)."""

SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "ta": {"type": "string"},
                    "forms": {"type": "array", "items": {"type": "string"}},
                    "avoid": {"type": "array", "items": {"type": "string"}},
                    "source": {"type": "string", "enum": ["irv", "curated"]},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "note": {"type": "string"},
                },
                "required": ["term", "ta", "forms", "avoid", "source", "confidence", "note"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["answers"],
    "additionalProperties": False,
}


def todo(only: list[str] | None, again: bool) -> list[Evidence]:
    """Seed terms to ask about: those without an entry (or all with `again`),
    or the terms named."""
    seeds = load_seed()
    if only:
        wanted = {repo.glossary_key(t) for t in only}
        seeds = [s for s in seeds if s.key in wanted]
    elif not again:
        have = load_file()
        seeds = [s for s in seeds if s.key not in have]
    return evidence(seeds)


def groups(items: list[Evidence]) -> list[list[Evidence]]:
    """Terms in seed order (related terms together), at most GROUP_TERMS terms
    and GROUP_VERSES distinct verses a request."""
    out: list[list[Evidence]] = []
    seen: set[str] = set()
    for ev in items:
        vs = set(ev.verses)
        if not out or len(out[-1]) >= GROUP_TERMS or len(seen | vs) > GROUP_VERSES:
            out.append([])
            seen = set()
        out[-1].append(ev)
        seen |= vs
    return out


def group_message(group: list[Evidence]) -> str:
    lines = ["Terms:"]
    for k, ev in enumerate(group, 1):
        s = ev.seed
        lines.append(f"{k}. {s.en}" + (f"  (also: {', '.join(s.also)})" if s.also else ""))
        lines.append(f"   topic: {s.group.replace('_', ' ')}" + ("; usually no single Bible word" if s.curated else ""))
        lines.append(f"   used in {ev.articles} dictionary articles" + (f", e.g.: {ev.example}" if ev.example else ""))
        if ev.strongs:
            lines.append(f"   Strong's numbers (BSB): {', '.join(ev.strongs)}")
        lines.append(f"   verses: {', '.join(ev.verses) if ev.verses else '(none found)'}")
    lines.append("")
    lines.append("Verses (with the verse before and after each, since the IRV often moves a clause across the boundary):")
    shown = set()
    for ev in group:
        for v in ev.verses:
            before, after = review.neighbours(v)
            shown |= {x for x in (before, v, after) if x and repo.verse_text(x)}
    for vid in sorted(shown, key=review.verse_order):
        lines.append(vid)
        lines.append(f"  KJV: {repo.verse_text(vid, 'KJV') or '(none)'}")
        lines.append(f"  IRV: {repo.verse_text(vid) or '(none)'}")
    return "\n".join(lines)


def params(group: list[Evidence], model: str, effort: str) -> dict:
    return {
        "model": model,
        "max_tokens": 16000,
        "system": [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": group_message(group)}],
        "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
    }


# ---- answers ----


def irv_texts(verses: list[str]) -> list[str]:
    """The IRV text of each verse with the verse either side."""
    return [" ".join(review.window(v, repo.TAMIL_VERSION).split()) for v in verses]


def found_in(form: str, texts: list[str]) -> bool:
    form = " ".join(form.split())
    pat = re.compile(rf"(?<![஀-௿]){re.escape(form)}(?![஀-௿])")
    return any(pat.search(t) for t in texts)


def entry_from(ev: Evidence, answer: dict) -> dict:
    """The glossary entry for Claude's answer: forms it reports for an IRV
    word are kept only if they are in the IRV verses; always for review."""
    s = ev.seed
    ta = " ".join((answer.get("ta") or "").split())
    forms = [" ".join(f.split()) for f in answer.get("forms", []) if f.strip()]
    missing = []
    if answer.get("source") == "irv":
        texts = irv_texts(ev.verses)
        missing = [f for f in forms if not found_in(f, texts)]
        forms = [f for f in forms if f not in missing]
    note = answer.get("note", "")
    if missing:
        note = (note + " " if note else "") + f"[Not in the IRV verses, dropped: {', '.join(missing)}]"
    return {
        "en": s.en, "ta": ta, "forms": list(dict.fromkeys([ta, *forms])) if ta else forms, "also": s.also,
        "avoid": [a.strip() for a in answer.get("avoid", []) if a.strip()],
        "source": answer.get("source", ""), "strongs": ev.strongs, "verses": ev.verses, "group": s.group,
        "note": note, "confidence": answer.get("confidence", ""), "review": True,
    }


def apply_group(group: list[Evidence], data: dict | None, error: str | None, dry_run: bool) -> list[dict]:
    got = (data or {}).get("answers", [])
    by_term = {repo.glossary_key(a.get("term", "").strip()): a for a in got}
    rows = []
    current = load_file()
    for k, ev in enumerate(group):
        a = by_term.get(ev.seed.key) or (got[k] if k < len(got) and not got[k].get("term") else None)
        if a is None or not a.get("ta"):
            rows.append({"term": ev.seed.en, "action": "skip", "why": error or "no answer for this term"})
            continue
        now = current.get(ev.seed.key)
        if now and not now.get("review"):
            rows.append({"term": ev.seed.en, "action": "skip", "why": "approved meanwhile; left as it is"})
            continue
        entry = entry_from(ev, a)
        row = {"term": ev.seed.en, "action": "draft", "entry": entry, "answer": a, "prompt_version": PROMPT_VERSION,
               "at": datetime.now().isoformat(timespec="seconds")}
        if not dry_run:
            entry.pop("confidence", None)
            save_entry(ev.seed.key, {**entry, "note": _with_confidence(entry["note"], a.get("confidence"))})
            repo.WORK.mkdir(exist_ok=True)
            with open(LOG, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        rows.append(row)
    return rows


def _with_confidence(note: str, confidence: str | None) -> str:
    return f"[Claude: {confidence}] {note}".strip() if confidence else note


def run_direct(items: list[Evidence], model: str, effort: str, dry_run: bool,
               workers: int = client.DEFAULT_WORKERS) -> list[dict]:
    """Ask now, `workers` requests at a time; answers are written as they come."""
    rows = []
    gs = groups(items)
    print(f"{len(gs)} requests, {workers} at a time", flush=True)
    jobs = [(f"terms-{k}", params(g, model, effort)) for k, g in enumerate(gs, 1)]
    for done, (k, reply) in enumerate(client.run_many(jobs, workers), 1):
        g = gs[k]
        print(f"[{done}/{len(gs)}] {', '.join(ev.seed.en for ev in g)}", flush=True)
        got = apply_group(g, reply.data, reply.error, dry_run)
        for r in got:
            print(f"  {r['term']}: {r['action']}" + (f" {r['entry']['ta']}" if "entry" in r else "")
                  + (f"  ({r['why']})" if r.get("why") else ""), flush=True)
        rows += got
    return rows


def submit(items: list[Evidence], model: str, effort: str) -> tuple[str, int]:
    gs = groups(items)
    reqs = [(f"t{k:04d}", params(g, model, effort)) for k, g in enumerate(gs, 1)]
    bid = client.submit_batch(reqs, note=f"ai-terms {model} {len(items)} terms in {len(gs)} groups")
    repo.WORK.mkdir(exist_ok=True)
    (repo.WORK / f"{bid}.json").write_text(
        json.dumps({"kind": "ai-terms", "groups": {cid: [ev.seed.en for ev in g] for (cid, _), g in zip(reqs, gs)}},
                   ensure_ascii=False),
        encoding="utf-8", newline="\n")
    return bid, len(gs)


def collect(batch_id: str, dry_run: bool) -> list[dict]:
    meta = json.loads((repo.WORK / f"{batch_id}.json").read_text(encoding="utf-8"))
    if client.batch_status(batch_id).processing_status != "ended":
        raise SystemExit("the batch has not ended yet (translate batch status)")
    seeds = {s.en: s for s in load_seed()}
    rows = []
    for cid, reply in client.batch_results(batch_id):
        names = [n for n in meta["groups"].get(cid, []) if n in seeds]
        group = evidence([seeds[n] for n in names])
        rows += apply_group(group, reply.data, reply.error, dry_run)
    return rows
