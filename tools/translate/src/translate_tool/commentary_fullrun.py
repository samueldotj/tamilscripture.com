"""`translate commentary-full-run`: translate whole commentaries without
supervision, as `full-run` does for the dictionaries
(docs/feature_commentary_translation.md §6).

1. Submit every unit of the chosen commentaries still without a current draft,
   as Message Batches of at most BATCH_UNITS units (half price).
2. Check every POLL seconds. When a translation batch ends, write its drafts
   (commentary.finish, no repair) and submit one repair batch for the parts the
   checks flagged: the first answer plus the list of problems.
3. When a repair batch ends, write those units again with the repaired parts.

State is kept in .translate-work/commentary/full-run.json, so the command can
be stopped and started again: it picks up the batches already submitted and
never submits a unit twice. While it runs it asks Windows not to sleep.
"""

from __future__ import annotations

import json
import time
from datetime import datetime

from . import client, commentary, translate
from .client import Reply
from .fullrun import keep_awake, say

STATE = commentary.WORK / "full-run.json"
BATCH_UNITS = 2000
POLL = 300


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"batches": []}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")


def pending(state: dict, sources: list[str]) -> dict[str, list[dict]]:
    """Per commentary, the units without a current draft that no batch of this run has taken."""
    taken = {uid for b in state["batches"] if b["kind"] == "translate" for uid in b["units"].values()}
    out: dict[str, list[dict]] = {}
    for s in sources:
        out[s] = [u for u in commentary.units(s) if u["id"] not in taken and not commentary.is_current(u)]
    return out


def plan(sources: list[str]) -> str:
    """What is left, and roughly what it costs; no API call."""
    lines = []
    state = load_state()
    for s, units in pending(state, sources).items():
        words = sum(commentary.english_words(u) for u in units)
        reqs = sum(len(commentary.chunks(u)) for u in units)
        lines.append(f"{s}: {len(units):,} units without a current draft, {words:,} English words, {reqs:,} requests; "
                     f"about ${words * 107 / 1e6:,.0f} as batches before repairs (pilot rate)")
    open_ = [b for b in state["batches"] if b["status"] == "submitted"]
    if open_:
        lines.append(f"{len(open_)} batch(es) of an earlier run still open: {', '.join(b['id'] for b in open_)}")
    return "\n".join(lines)


def submit_translations(state: dict, ctx: commentary.Context, sources: list[str]) -> None:
    for source, units in pending(state, sources).items():
        for k in range(0, len(units), BATCH_UNITS):
            chunk = units[k : k + BATCH_UNITS]
            reqs = [r for u in chunk for r in commentary.requests_for(u, ctx)]
            bid = client.submit_batch(reqs, note=f"commentary full-run {source} {ctx.model} {len(chunk)} units")
            prefixes = {translate.custom_id(u["id"], 1).rsplit("-", 1)[0]: u["id"] for u in chunk}
            state["batches"].append({"id": bid, "kind": "translate", "source": source, "status": "submitted",
                                     "units": prefixes, "requests": len(reqs),
                                     "at": datetime.now().isoformat(timespec="seconds")})
            save_state(state)
            say(f"submitted {bid}: {source}, {len(chunk)} units in {len(reqs)} requests")


def flagged_replies(unit_id: str) -> list[Reply] | None:
    path = commentary.FLAGGED / (unit_id.replace("/", "__") + ".json")
    if not path.exists():
        return None
    out = []
    for text in json.loads(path.read_text(encoding="utf-8")):
        try:
            out.append(Reply(json.loads(text), None, text))
        except json.JSONDecodeError:
            out.append(Reply(None, "invalid JSON", text))
    return out


def collect_translation(b: dict, ctx: commentary.Context) -> list[str]:
    replies = dict(client.batch_results(b["id"]))
    flagged, written = [], 0
    for prefix, uid in b["units"].items():
        u = commentary.load_unit(uid)
        n = len(commentary.chunks(u))
        parts = [replies.get(f"{prefix}-{k}", Reply(None, "missing from batch", "")) for k in range(1, n + 1)]
        o = commentary.finish(u, parts, ctx, allow_repair=False)
        written += o.written
        if o.problems:
            flagged.append(uid)
    say(f"collected {b['id']} ({b['source']}): {written}/{len(b['units'])} drafts written, {len(flagged)} with problems")
    return flagged


def repair_requests(unit_ids: list[str], ctx: commentary.Context) -> tuple[list, dict]:
    reqs, plan_ = [], {}
    for uid in unit_ids:
        u = commentary.load_unit(uid)
        replies = flagged_replies(uid)
        parts = commentary.chunks(u)
        if replies is None or len(replies) != len(parts):
            continue
        originals = commentary.requests_for(u, ctx)
        for k, (paras, reply) in enumerate(zip(parts, replies)):
            ps = commentary.part_problems(u, paras, reply, ctx)
            if not ps:
                continue
            cid, req = originals[k]
            reqs.append((cid + "-r", commentary.repair_request(u, paras, reply, ps, req, ctx)))
            plan_.setdefault(uid, []).append(k + 1)
    return reqs, plan_


def submit_repairs(state: dict, b: dict, unit_ids: list[str], ctx: commentary.Context) -> None:
    reqs, plan_ = repair_requests(unit_ids, ctx)
    if not reqs:
        return
    bid = client.submit_batch(reqs, note=f"commentary full-run repair {b['source']} {len(plan_)} units")
    state["batches"].append({"id": bid, "kind": "repair", "source": b["source"], "status": "submitted",
                             "plan": plan_, "requests": len(reqs), "for": b["id"],
                             "at": datetime.now().isoformat(timespec="seconds")})
    say(f"submitted repair batch {bid}: {len(plan_)} {b['source']} units, {len(reqs)} parts")


def collect_repairs(b: dict, ctx: commentary.Context) -> None:
    replies = dict(client.batch_results(b["id"]))
    fixed = still = 0
    for uid, part_numbers in b["plan"].items():
        u = commentary.load_unit(uid)
        parts = flagged_replies(uid)
        if parts is None:
            continue
        for k in part_numbers:
            r = replies.get(f"{translate.custom_id(uid, k)}-r")
            if r is not None:
                parts[k - 1] = commentary.merge_repair(parts[k - 1], r)
        o = commentary.finish(u, parts, ctx, allow_repair=False)
        if o.problems:
            still += 1
        else:
            fixed += 1
    say(f"collected repair batch {b['id']} ({b['source']}): {fixed} units now clean, {still} still flagged for a human")


def run(model: str, effort: str, sources: list[str], poll: int = POLL) -> int:
    keep_awake()
    ctx = commentary.Context(model=model, effort=effort)
    state = load_state()
    submit_translations(state, ctx, sources)
    while True:
        open_batches = [b for b in state["batches"] if b["status"] == "submitted"]
        if not open_batches:
            break
        for b in open_batches:
            if client.batch_status(b["id"]).processing_status != "ended":
                continue
            if b["kind"] == "translate":
                flagged = collect_translation(b, ctx)
                b["status"] = "collected"
                save_state(state)
                submit_repairs(state, b, flagged, ctx)
            else:
                collect_repairs(b, ctx)
                b["status"] = "collected"
            save_state(state)
        still_open = [b for b in state["batches"] if b["status"] == "submitted"]
        if still_open:
            counts = []
            for b in still_open:
                c = client.batch_status(b["id"]).request_counts
                counts.append(f"{b['source']} {b['kind']} {c.succeeded + c.errored}/{b['requests']}")
            say("waiting: " + "; ".join(counts))
            time.sleep(poll)
    say("all batches collected.\n" + summary(sources))
    return 0


def summary(sources: list[str]) -> str:
    lines = []
    for s in sources:
        total = done = 0
        for u in commentary.units(s):
            total += 1
            done += commentary.is_current(u)
        lines.append(f"{s}: {done:,}/{total:,} units have a current Tamil draft")
    flagged = len(list(commentary.FLAGGED.glob("*.json"))) if commentary.FLAGGED.exists() else 0
    lines.append(f"{flagged} units flagged for a human (.translate-work/commentary/flagged, report.jsonl). "
                 "Commit ta/ in bible-commentaries, then publish.")
    return "\n".join(lines)
