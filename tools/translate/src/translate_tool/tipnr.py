"""`translate tipnr`: Tamil for the short descriptions of people that STEP
Bible's TIPNR gives (CC BY 4.0): the one-line `brief` under a name on the
dictionary card ("Apostle of Jesus, leader in the early church") and the
one- or two-sentence `short` on the person page.

Many people share a line ("Son of Aaron"), so each distinct English text is
translated once. Lines go in groups, with the Tamil names and glossary terms
they use, through the Message Batches API at half price, or one request at a
time for a quick first run. A line is written to the drafts file only when it
passes the same checks as the dictionary articles (Tamil script, no English
left, names and glossary terms as given, references kept); the rest are
logged with their problems and asked again with `--repair`.

The drafts file `data/entities/drafts/ta/tipnr.json` maps the English text to
its Tamil; the build looks each person's `brief` and `short` up in it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from . import checks, client, prompts, repo

PROMPT_VERSION = "tipnr-1"
DRAFTS = repo.DRAFTS / "ta" / "tipnr.json"
LOG = repo.WORK / "tipnr.jsonl"
GROUP_ITEMS = 40  # lines per request
GROUP_CHARS = 3500  # and at most this many English characters

SYSTEM = """\
You translate short descriptions of people in the Bible from English into Tamil for tamilscripture.com, a Tamil Bible study site whose readers are Tamil Protestant Christians in the Reformed tradition. The site's Bible is the Indian Revised Version (IRV, 2019), and the Tamil must read as though written for readers of the IRV. The descriptions come from STEP Bible's list of biblical names (TIPNR).

There are two kinds of line:
- "brief": a label shown under a person's name, usually a phrase with no verb ("Son of Aaron", "Apostle of Jesus, leader in the early church"). Translate it as a short Tamil phrase of the same kind, not a sentence: ஆரோனின் மகன்.
- "short": one or two sentences about the person. Translate them as full Tamil sentences.

How to translate:
- Translate faithfully and completely. Do not summarise, explain, add to or correct the line.
- `about` names the person the line describes; it is there so you know who is meant. Do not add the name to a line that does not have it.
- Write formal written Tamil in the register of the IRV and of Tamil Protestant teaching, not colloquial Tamil and not Sanskritised or Hindu religious vocabulary where the IRV uses another word.
- Theological terms: use the Tamil given in the glossary with the lines whenever the English term or one of its forms occurs, inflecting it as the sentence needs. Never use a rendering listed under "avoid".
- Names of people and places: use the Tamil names given with the lines, inflected as the sentence needs. Otherwise use the spelling the IRV uses; transliterate only a name the IRV does not contain.
- References written with dots, such as Exo.6.23 or 2Sa.23.8, are links on the site: copy them exactly as they are, in Latin letters, with any brackets around them. A book named in words (Proverbs 30, the genealogies of Genesis) is written with the Tamil book name below, keeping the numbers.
- Numbers keep their values and stay in digits.
- Produce plain text only: no HTML, Markdown or notes of your own.
- A line may carry `previous` and `problems`: an earlier translation and what a check found wrong with it. Translate the line again, fixing those problems.

Output: JSON with one item for every line given, with the same "id" values in the same order."""

SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
                "required": ["id", "text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

OSIS_REF = re.compile(r"\b[1-4]?[A-Z][a-z]{1,2}\.\d+\.\d+(?:-\d+(?:\.\d+)*)?")
NUMBER = re.compile(r"\d[\d,]*")


@dataclass
class Line:
    en: str
    kind: str  # brief | short
    about: list[str] = field(default_factory=list)  # names of the people it describes
    previous: str | None = None  # an earlier translation that failed the checks (--repair)
    problems: list[str] = field(default_factory=list)


# ---- what to translate ----


def lines() -> dict[str, Line]:
    """English text → line, for every person's brief and short in the build."""
    out: dict[str, Line] = {}
    for path in sorted((repo.build_dir() / "entities" / "person").glob("*.json")):
        p = json.loads(path.read_text(encoding="utf-8"))
        for kind in ("brief", "short"):
            text = " ".join((p.get(kind) or "").split())
            if not text:
                continue
            line = out.setdefault(text, Line(text, kind))
            if p["name_en"] not in line.about:
                line.about.append(p["name_en"])
    return out


def load_drafts() -> dict:
    if not DRAFTS.exists():
        return {"lang": "ta", "source": "TIPNR, STEP Bible / Tyndale House Cambridge", "licence": "CC BY 4.0",
                "generator": {}, "texts": {}}
    return json.loads(DRAFTS.read_text(encoding="utf-8"))


def save_drafts(d: dict) -> None:
    d["texts"] = dict(sorted(d["texts"].items()))
    DRAFTS.parent.mkdir(parents=True, exist_ok=True)
    DRAFTS.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def failures() -> dict[str, dict]:
    """English text → its last logged result, when that result failed."""
    last: dict[str, dict] = {}
    if LOG.exists():
        for l in LOG.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                last[r["en"]] = r
    return {en: r for en, r in last.items() if r.get("problems")}


def todo(kind: str | None = None, limit: int | None = None, repair: bool = False, force: bool = False,
         texts: list[str] | None = None) -> list[Line]:
    """Lines without a Tamil draft; with `repair`, only those whose last try
    failed, carrying that try and its problems."""
    every = lines()
    done = load_drafts()["texts"]
    failed = failures()
    out = []
    for en, line in every.items():
        if kind and line.kind != kind:
            continue
        if texts and not any(t.lower() in en.lower() for t in texts):
            continue
        if en in done and not force:
            continue
        if repair:
            if en not in failed:
                continue
            line.previous, line.problems = failed[en].get("ta") or None, failed[en]["problems"]
        out.append(line)
    out.sort(key=lambda x: (x.about[0].lower(), x.kind, x.en))
    return out[:limit] if limit else out


def groups(todo: list[Line]) -> list[list[Line]]:
    out: list[list[Line]] = []
    chars = 0
    for line in todo:
        if not out or len(out[-1]) >= GROUP_ITEMS or chars + len(line.en) > GROUP_CHARS:
            out.append([])
            chars = 0
        out[-1].append(line)
        chars += len(line.en)
    return out


# ---- the request ----


@dataclass
class Context:
    model: str = client.DEFAULT_MODEL
    effort: str = client.DEFAULT_EFFORT
    terms: dict = field(default_factory=repo.reviewed_terms)
    names: dict = field(default_factory=repo.reviewed_names)
    provisional: dict = field(default_factory=repo.load_names)  # every name, reviewed or not


def system_blocks() -> list[dict]:
    text = "\n\n".join([SYSTEM, prompts.books_block()])
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def message(group: list[Line], ctx: Context) -> str:
    english = "\n".join(line.en for line in group)
    sections = []
    if block := prompts.glossary_block(checks.terms_in(english, ctx.terms)):
        sections.append(block.replace("for this article", "for these lines"))
    found = {n.en: n for n in checks.names_in(english, ctx.names)}
    for line in group:
        for who in line.about:
            if who in ctx.names:
                found.setdefault(who, ctx.names[who])
    rows = [f"- {n.en} → {', '.join(dict.fromkeys([n.label, *n.forms[:4]]))}" for n in sorted(found.values(), key=lambda n: n.en)]
    # The person's own name when no one has reviewed it yet: better than a guess.
    for who in sorted({w for line in group for w in line.about} - set(found)):
        e = ctx.provisional.get(who)
        if e and e.get("label"):
            rows.append(f"- {who} → {e['label']} (not yet checked; use it unless the IRV plainly differs)")
    if rows:
        sections.append("Tamil names in the IRV for names in these lines:\n" + "\n".join(rows))
    items = []
    for k, line in enumerate(group, 1):
        item = {"id": str(k), "kind": line.kind, "about": ", ".join(line.about[:3]), "text": line.en}
        if line.problems:
            item["previous"] = line.previous or ""
            item["problems"] = line.problems
        items.append(item)
    sections.append("Lines:\n" + json.dumps(items, ensure_ascii=False, indent=1))
    return "\n\n".join(sections)


def params(group: list[Line], ctx: Context, system: list[dict]) -> dict:
    return {
        "model": ctx.model,
        "max_tokens": 32000,
        "system": system,
        "messages": [{"role": "user", "content": message(group, ctx)}],
        "output_config": {"effort": ctx.effort, "format": {"type": "json_schema", "schema": SCHEMA}},
    }


# ---- checking and writing ----


def numbers(s: str) -> set[str]:
    return {n.replace(",", "") for n in NUMBER.findall(s)}


def check(line: Line, ta: str, ctx: Context) -> list[str]:
    # Every line describes someone in words, so the articles' allowance for a
    # label with nothing to translate ("538") does not apply.
    if why := checks.check_text(ta):
        return [why]
    out = checks.check_paragraph(line.en, ta, ctx.terms, ctx.names)
    if out:
        return out
    if missing := sorted(set(OSIS_REF.findall(line.en)) - set(OSIS_REF.findall(ta))):
        out.append(f"references not copied exactly: {', '.join(missing)}")
    if missing := sorted(numbers(line.en) - numbers(ta)):
        out.append(f"numbers missing: {', '.join(missing)}")
    if line.kind == "brief" and len(ta) > 4 * len(line.en) + 40:
        out.append("much longer than the English: a brief is a short phrase")
    return out


def apply_group(group: list[Line], reply: client.Reply, ctx: Context, drafts: dict, dry_run: bool) -> list[dict]:
    """Check each line's Tamil; write the good ones into `drafts` (saved by the
    caller) and log every result."""
    got = {str(i.get("id")): i.get("text", "") for i in (reply.data or {}).get("items", [])}
    rows = []
    for k, line in enumerate(group, 1):
        ta = " ".join(got.get(str(k), "").split())
        problems = [reply.error or "no reply"] if reply.data is None else (check(line, ta, ctx) if ta else ["no translation for this line"])
        rows.append({"en": line.en, "kind": line.kind, "ta": ta, "problems": problems, "model": ctx.model,
                     "prompt_version": PROMPT_VERSION, "at": datetime.now().isoformat(timespec="seconds")})
        if not problems and not dry_run:
            drafts["texts"][line.en] = ta
    if not dry_run:
        repo.WORK.mkdir(exist_ok=True)
        with open(LOG, "a", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows


def stamp(drafts: dict, ctx: Context) -> None:
    drafts["generator"] = {"name": "claude", "model": ctx.model, "prompt_version": PROMPT_VERSION,
                           "generated_at": date.today().isoformat()}


# ---- running ----


def run_direct(todo: list[Line], ctx: Context, dry_run: bool, workers: int = client.DEFAULT_WORKERS) -> list[dict]:
    gs = groups(todo)
    system = system_blocks()
    print(f"{len(todo)} lines in {len(gs)} requests, {workers} at a time", flush=True)
    jobs = [(f"tipnr-{k}", params(g, ctx, system)) for k, g in enumerate(gs, 1)]
    drafts = load_drafts()
    rows = []
    for done, (k, reply) in enumerate(client.run_many(jobs, workers), 1):
        got = apply_group(gs[k], reply, ctx, drafts, dry_run)
        bad = sum(1 for r in got if r["problems"])
        print(f"[{done}/{len(gs)}] {len(got)} lines, {bad} flagged", flush=True)
        rows += got
        if not dry_run:
            stamp(drafts, ctx)
            save_drafts(drafts)
    return rows


def custom_id(group: list[Line]) -> str:
    return hashlib.sha1("\n".join(line.en for line in group).encode()).hexdigest()[:24]


def submit(todo: list[Line], ctx: Context) -> tuple[str, int]:
    gs = groups(todo)
    system = system_blocks()
    reqs = [(custom_id(g), params(g, ctx, system)) for g in gs]
    bid = client.submit_batch(reqs, note=f"tipnr {ctx.model} {len(todo)} lines in {len(gs)} requests")
    meta = {"kind": "tipnr", "model": ctx.model, "effort": ctx.effort,
            "groups": {cid: [{"en": line.en, "kind": line.kind, "about": line.about, "previous": line.previous,
                              "problems": line.problems} for line in g] for (cid, _), g in zip(reqs, gs)}}
    (repo.WORK / f"{bid}.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8", newline="\n")
    return bid, len(gs)


def collect(batch_id: str, dry_run: bool) -> list[dict]:
    meta = json.loads((repo.WORK / f"{batch_id}.json").read_text(encoding="utf-8"))
    if client.batch_status(batch_id).processing_status != "ended":
        raise SystemExit("the batch has not ended yet (translate batch status)")
    ctx = Context(model=meta["model"], effort=meta["effort"])
    drafts = load_drafts()
    rows = []
    total = len(meta["groups"])
    print(f"downloading the results of {total} requests…", flush=True)
    for k, (cid, reply) in enumerate(client.batch_results(batch_id), 1):
        group = [Line(**x) for x in meta["groups"].get(cid, [])]
        got = apply_group(group, reply, ctx, drafts, dry_run)
        bad = sum(1 for r in got if r["problems"])
        print(f"[{k}/{total}] {len(got)} lines, {bad} flagged" + (f" ({reply.error})" if reply.error else ""), flush=True)
        rows += got
    if not dry_run:
        stamp(drafts, ctx)
        save_drafts(drafts)
    return rows


def recheck(dry_run: bool) -> list[dict]:
    """Check the flagged lines' last Tamil again with the current checks,
    names and glossary (after a fix to a check or a name); no API call. Lines
    that now pass are written."""
    ctx = Context()
    drafts = load_drafts()
    rows = []
    for en, r in failures().items():
        if r.get("rejected"):  # a reviewer's call, not a check's
            continue
        line = Line(en, r.get("kind", "short"))
        ta = r.get("ta") or ""
        problems = check(line, ta, ctx) if ta else ["no translation for this line"]
        rows.append({**r, "problems": problems, "rechecked": True, "at": datetime.now().isoformat(timespec="seconds")})
        if not problems and not dry_run:
            drafts["texts"][en] = ta
    if not dry_run:
        with open(LOG, "a", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        save_drafts(drafts)
    return rows


# ---- cost ----


def estimate(todo: list[Line], ctx: Context, batch: bool = True) -> dict:
    """Rough tokens and dollars, no API call: English about 4 characters a
    token, Tamil output about five times the English tokens (the dictionary
    run's ratio), the system prompt sent in full with every request."""
    from .pilot import PRICES

    gs = groups(todo)
    system = len(system_blocks()[0]["text"]) / 3.5
    tok_in = sum(system + len(message(g, ctx)) / 3.0 for g in gs)
    tok_out = sum(len(line.en) / 4 * 5 + 12 for line in todo)
    pin, pout = PRICES.get(ctx.model, (0.0, 0.0))
    cost = (tok_in * pin + tok_out * pout) / 1e6 * (0.5 if batch else 1.0)
    return {"lines": len(todo), "requests": len(gs), "input": int(tok_in), "output": int(tok_out), "cost": cost}
