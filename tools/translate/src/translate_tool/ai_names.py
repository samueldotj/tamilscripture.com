"""`translate ai-names`: ask Claude for the Tamil of the names still in
review, the ones the aligner and the sound match could not settle: names the
IRV translates ("City of David" → தாவீதின் நகரம்), names in verses where the
IRV moved the clause, spellings the heuristics miss.

Names are asked about in groups: names that occur close together in the text
(Esther's seven chamberlains) go in one request, and each verse is sent once
for the group. Groups go through the Message Batches API at half price, or
one request at a time for a quick first run.

Every form Claude reports is checked against the IRV and TCV verses (and the
verse either side) before anything is written. An answer is accepted outright
only when Claude found the name in the IRV, is sure, and the text bears it
out. Anything else becomes the entry's draft, still marked for review, and the
review page offers Claude's answer first (`review-names --web --ai`).
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from . import client, repo, review
from .session import Item, queue, suggest

PROMPT_VERSION = "names-2"
LOG = repo.WORK / "ai-names.jsonl"
VERSES_PER_NAME = 6  # verses sent for a name (its first ones)
GROUP_NAMES = 10  # names per request
GROUP_VERSES = 45  # and at most this many distinct verses

SYSTEM = """\
You help build the list of Tamil names of biblical people and places for tamilscripture.com, a Tamil Bible site whose Bible is the Indian Revised Version (IRV, Tamil, 2019). You are given several English names, each with who or what it is, the ids of the verses where it occurs, and what an automatic aligner guessed; then the verses themselves in English (KJV) and in the IRV. Answer for every name, in the order given, using the name exactly as written.

Give each name as the IRV writes it.

- If the IRV verses contain the name, copy it from them letter for letter. `label` is the uninflected base form (remove case endings such as -இன், -உக்கு, -ஐ, -இல், -உம், -ஓடு, and the glides வ்/ய் before them; a name the IRV writes ending in -உ keeps it, e.g. தாவீது). `forms` lists every spelling of the name that appears in the IRV verses given, copied exactly, inflected or not.
- The IRV often carries a clause into the next verse: look in the verse before and after too.
- If the IRV translates the name rather than transliterating it (City of David, Salt Sea, Valley of Rephaim, East), give the IRV's Tamil phrase as `label`, and in `forms` the phrase as it appears in the verses. A name of several words keeps its spaces.
- A title or description the IRV uses instead of the name (Augustus as பேரரசன்) is not the name: give the transliteration the IRV uses elsewhere if you know it, else compose one.
- If the name is not in the IRV verses given (the IRV may word the verse differently), compose the Tamil following the IRV's spelling conventions for biblical names; set `source` to "composed" and leave `forms` empty.
- Never give a word of the verse that is not the name (a verb, a relationship like மகன், a title, another person's name). Two different names in the same verse are different words.

`confidence` is "high" only when the name is plainly there in the IRV verses and your label is its base form. Use `note` for one short sentence a reviewer should know (in English), or leave it empty."""

SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "label": {"type": "string"},
                    "forms": {"type": "array", "items": {"type": "string"}},
                    "source": {"type": "string", "enum": ["irv", "composed"]},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "note": {"type": "string"},
                },
                "required": ["name", "label", "forms", "source", "confidence", "note"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["answers"],
    "additionalProperties": False,
}


# ---- what to ask ----


def items(names: list[str] | None, limit: int | None, again: bool = False) -> list[Item]:
    """Names still in review (rejected ones too), or the names given; names
    already answered are left out unless `again` or named."""
    todo = queue("verses", None, include_rejected=True, everything=bool(names), only=set(names) if names else None)
    if not (names or again):
        done = answers()
        todo = [i for i in todo if i.name not in done]
    return todo[:limit] if limit else todo


def verses_for(item: Item) -> list[str]:
    """The verses sent for a name: its first few, with the verse either side
    when it has three or fewer."""
    out = []
    for v in item.verses[:VERSES_PER_NAME]:
        if len(item.verses) <= 3:
            before, after = review.neighbours(v)
            out += [x for x in (before, v, after) if x and repo.verse_text(x)]
        else:
            out.append(v)
    return list(dict.fromkeys(out))


def groups(todo: list[Item]) -> list[list[Item]]:
    """Names in text order (by first verse), cut into groups of at most
    GROUP_NAMES names and GROUP_VERSES distinct verses, so names that share
    verses share a request."""
    todo = sorted(todo, key=lambda i: (review.verse_order(i.verses[0]), i.name))
    out: list[list[Item]] = []
    seen: set[str] = set()
    for item in todo:
        vs = set(verses_for(item))
        if not out or len(out[-1]) >= GROUP_NAMES or len(seen | vs) > GROUP_VERSES:
            out.append([])
            seen = set()
        out[-1].append(item)
        seen |= vs
    return out


def group_message(group: list[Item]) -> str:
    lines = ["Names:"]
    for k, item in enumerate(group, 1):
        lines.append(f"{k}. {item.name}")
        for b in review.name_briefs().get(item.name, [])[:3]:
            lines.append(f"   who or what: {b}")
        shown = verses_for(item)
        more = f" (and {len(item.verses) - VERSES_PER_NAME} more)" if len(item.verses) > VERSES_PER_NAME else ""
        lines.append(f"   occurs in: {', '.join(v for v in item.verses[:VERSES_PER_NAME])}{more}")
        if len(shown) > len(item.verses[:VERSES_PER_NAME]):
            lines.append("   (the verse before and after each is also given)")
        lines.append(f"   aligner's guess (may be wrong): {item.entry['label']}")
        _, sugg = suggest(item, with_ai=False)
        if sugg:
            lines.append(f"   IRV words that sound like it: {', '.join(s.label for s in sugg)}")
    lines.append("")
    lines.append("Verses:")
    order = sorted({v for item in group for v in verses_for(item)}, key=review.verse_order)
    for vid in order:
        lines.append(f"{vid}")
        lines.append(f"  KJV: {repo.verse_text(vid, 'KJV') or '(none)'}")
        lines.append(f"  IRV: {repo.verse_text(vid) or '(none)'}")
    return "\n".join(lines)


def params(group: list[Item], model: str, effort: str) -> dict:
    return {
        "model": model,
        "max_tokens": 16000,
        "system": [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": group_message(group)}],
        "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
    }


# ---- checking and writing answers ----


def texts_for(item: Item) -> list[str]:
    """The IRV and TCV text of the name's verses and the verse either side,
    whitespace squashed, to check the forms Claude reports."""
    return [" ".join(review.window(v, version).split()) for version in (repo.TAMIL_VERSION, "TCV") for v in item.verses]


def occurs(form: str, texts: list[str]) -> bool:
    form = " ".join(form.split())
    pat = re.compile(rf"(?<![஀-௿]){re.escape(form)}(?![஀-௿])")
    return any(pat.search(t) for t in texts)


def decide(item: Item, answer: dict) -> dict:
    """What to write for one answer: the entry, whether it is accepted, and why."""
    label = " ".join(answer.get("label", "").split())
    if not review.TAMIL_NAME.fullmatch(label or "-"):
        return {"action": "skip", "why": f"not Tamil: {label!r}"}
    texts = texts_for(item)
    forms = [" ".join(f.split()) for f in answer.get("forms", [])]
    found = [f for f in dict.fromkeys(forms) if f and occurs(f, texts)]
    missing = [f for f in forms if f not in found]
    stem = label[: max(2, len(label) - 2)]
    consistent = any(f.startswith(stem) for f in found)
    accept = bool(answer.get("source") == "irv" and answer.get("confidence") == "high"
                  and found and consistent and not missing)
    entry = {"label": label, "forms": found, "confidence": 1.0 if accept else 0.5, "n": len(item.verses)}
    if not accept:
        entry["review"] = True
    why = [] if accept else [
        r for r, bad in [
            ("Claude composed it: not in the IRV verses", answer.get("source") != "irv"),
            (f"Claude's confidence is {answer.get('confidence')}", answer.get("confidence") != "high"),
            (f"not in the verses: {', '.join(missing)}", bool(missing)),
            ("no form found in the verses", not found),
            ("label does not match the forms", bool(found) and not consistent),
        ] if bad
    ]
    return {"action": "accept" if accept else "draft", "entry": entry, "why": "; ".join(why)}


def apply(item: Item, answer: dict, dry_run: bool) -> dict:
    d = decide(item, answer)
    row = {"name": item.name, "before": item.entry, "answer": answer, **d, "prompt_version": PROMPT_VERSION,
           "at": datetime.now().isoformat(timespec="seconds")}
    if not dry_run and d["action"] != "skip":
        # Re-read: the review page may have settled the name meanwhile.
        now = repo.load_names().get(item.name, {})
        if now.get("review") or item.entry == now:
            repo.save_name(item.name, d["entry"])
        else:
            row.update(action="skip", why="reviewed meanwhile; left as it is")
    if not dry_run:
        repo.WORK.mkdir(exist_ok=True)
        with open(LOG, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def apply_group(group: list[Item], data: dict | None, error: str | None, dry_run: bool) -> list[dict]:
    """Match a group's answers to its names (by name, then by position)."""
    got = (data or {}).get("answers", [])
    by_name = {a.get("name", "").strip().lower(): a for a in got}
    rows = []
    for k, item in enumerate(group):
        a = by_name.get(item.name.lower()) or (got[k] if k < len(got) and not got[k].get("name") else None)
        if a is None:
            rows.append({"name": item.name, "action": "skip", "why": error or "no answer for this name"})
        else:
            rows.append(apply(item, a, dry_run))
    return rows


def say(rows: list[dict]) -> None:
    for r in rows:
        label = f" {r['entry']['label']}" if "entry" in r else ""
        print(f"  {r['name']}: {r['action']}{label}" + (f"  ({r['why']})" if r.get("why") else ""), flush=True)


# ---- running ----


def run_direct(todo: list[Item], model: str, effort: str, dry_run: bool) -> list[dict]:
    rows = []
    gs = groups(todo)
    for k, g in enumerate(gs, 1):
        print(f"group {k}/{len(gs)}: {len(g)} names", flush=True)
        reply = client.run_direct(params(g, model, effort), f"names-{k}")
        got = apply_group(g, reply.data, reply.error, dry_run)
        say(got)
        rows += got
    return rows


def submit(todo: list[Item], model: str, effort: str) -> tuple[str, int]:
    gs = groups(todo)
    reqs = [(f"g{k:04d}", params(g, model, effort)) for k, g in enumerate(gs, 1)]
    bid = client.submit_batch(reqs, note=f"ai-names {model} {len(todo)} names in {len(gs)} groups")
    repo.WORK.mkdir(exist_ok=True)
    (repo.WORK / f"{bid}.json").write_text(
        json.dumps({"kind": "ai-names", "groups": {cid: [i.name for i in g] for (cid, _), g in zip(reqs, gs)}},
                   ensure_ascii=False),
        encoding="utf-8", newline="\n")
    return bid, len(gs)


def collect(batch_id: str, dry_run: bool) -> list[dict]:
    meta = json.loads((repo.WORK / f"{batch_id}.json").read_text(encoding="utf-8"))
    if client.batch_status(batch_id).processing_status != "ended":
        raise SystemExit("the batch has not ended yet (translate batch status)")
    by_name = {i.name: i for i in queue("verses", None, include_rejected=True, everything=True)}
    # Names already written by an earlier collect of this batch (one that
    # stopped halfway) are not written again.
    done = set(answers())
    rows = []
    for cid, reply in client.batch_results(batch_id):
        group = [by_name[n] for n in meta["groups"].get(cid, []) if n in by_name and n not in done]
        if group:
            rows += apply_group(group, reply.data, reply.error, dry_run)
    return rows


# ---- for the review page ----


def _log() -> list[dict]:
    if not LOG.exists():
        return []
    return [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]


def answers() -> dict[str, dict]:
    """Name → Claude's last answer, with the decision on it."""
    out = {}
    for r in _log():
        if "answer" in r:
            out[r["name"]] = {**r["answer"], "action": r.get("action"), "why": r.get("why", "")}
    return out


def notes() -> dict[str, dict]:
    return answers()


def accepted() -> set[str]:
    """Names whose Claude answer was accepted without review."""
    return {n for n, a in answers().items() if a.get("action") == "accept"}
