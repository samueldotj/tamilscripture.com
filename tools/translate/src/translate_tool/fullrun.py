"""`translate full-run`: translate every dictionary article without supervision
(docs/feature_dictionary_translation.md §6, step 3).

1. Submit every article still without a current draft, all three sources at
   once, as Message Batches of at most BATCH_ARTICLES articles (half price;
   the batches are processed side by side).
2. Check every POLL seconds. When a translation batch ends, write its drafts
   (translate.finish, no repair) and submit one repair batch for the parts
   the checks flagged: the first answer plus the list of problems, as the
   direct repair turn does, but at half price.
3. When a repair batch ends, write those articles again with the repaired
   parts.

State is kept in .translate-work/full-run.json, so the command can be stopped
and started again: it picks up the batches already submitted and never
submits an article twice. While it runs it asks Windows not to sleep.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime

from . import checks, client, prompts, repo, translate

STATE = repo.WORK / "full-run.json"
BATCH_ARTICLES = 1000
POLL = 300
SOURCES = ("eastons", "smiths", "aquifer")


def say(msg: str) -> None:
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}", flush=True)


def keep_awake() -> None:
    """Ask Windows to keep the system (not the screen) awake while this
    process runs; the request ends with the process."""
    if sys.platform == "win32":
        import ctypes

        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        say("keeping the computer awake while the run lasts")


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"batches": []}


def save_state(state: dict) -> None:
    repo.WORK.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")


def pending_articles(state: dict) -> dict[str, list[dict]]:
    """Per source, the articles without a current draft that no batch of this
    run has taken yet."""
    taken = {a for b in state["batches"] if b["kind"] == "translate" for a in b["articles"].values()}
    out: dict[str, list[dict]] = {s: [] for s in SOURCES}
    for x in repo.articles_index():
        if x["source"] in out and x["id"] not in taken:
            art = repo.load_article(x["id"])
            if not translate.is_current(art):
                out[x["source"]].append(art)
    return out


def submit_translations(state: dict, ctx: translate.Context) -> None:
    for source, arts in pending_articles(state).items():
        for k in range(0, len(arts), BATCH_ARTICLES):
            chunk = arts[k : k + BATCH_ARTICLES]
            reqs = [r for art in chunk for r in translate.requests_for(art, ctx)]
            bid = client.submit_batch(reqs, note=f"full-run {source} {ctx.model} {len(chunk)} articles")
            prefixes = {translate.custom_id(a["id"], 1).rsplit("-", 1)[0]: a["id"] for a in chunk}
            state["batches"].append({"id": bid, "kind": "translate", "source": source, "status": "submitted",
                                     "articles": prefixes, "requests": len(reqs),
                                     "at": datetime.now().isoformat(timespec="seconds")})
            save_state(state)
            say(f"submitted {bid}: {source}, {len(chunk)} articles in {len(reqs)} requests")


def collect_translation(b: dict, ctx: translate.Context) -> list[str]:
    """Write the drafts of an ended translation batch; return the articles
    with problems (for the repair batch)."""
    replies = dict(client.batch_results(b["id"]))
    flagged = []
    written = 0
    for prefix, article_id in b["articles"].items():
        art = repo.load_article(article_id)
        n = len(prompts.chunks(art))
        parts = [replies.get(f"{prefix}-{k}", client.Reply(None, "missing from batch", "")) for k in range(1, n + 1)]
        o = translate.finish(art, parts, ctx, allow_repair=False)
        written += o.written
        if o.problems:
            flagged.append(article_id)
    say(f"collected {b['id']} ({b['source']}): {written}/{len(b['articles'])} drafts written, "
        f"{len(flagged)} with problems")
    return flagged


def repair_requests(article_ids: list[str], ctx: translate.Context) -> tuple[list, dict]:
    """(requests, {article id: [part numbers repaired]}) for the flagged parts
    of these articles: the original request, Claude's answer, the problems."""
    reqs, plan = [], {}
    for aid in article_ids:
        art = repo.load_article(aid)
        replies = translate.flagged_replies(aid)
        parts = prompts.chunks(art)
        if replies is None or len(replies) != len(parts):
            continue
        originals = translate.requests_for(art, ctx)
        for k, (paras, reply) in enumerate(zip(parts, replies)):
            ps = translate.part_problems(art, paras, reply, ctx)
            if not ps:
                continue
            cid, req = originals[k]
            if reply.text:
                req = {**req, "messages": req["messages"] + [
                    {"role": "assistant", "content": reply.text},
                    {"role": "user", "content": prompts.repair_message(ps)},
                ]}
            reqs.append((cid + "-r", req))
            plan.setdefault(aid, []).append(k + 1)
    return reqs, plan


def submit_repairs(state: dict, b: dict, article_ids: list[str], ctx: translate.Context) -> None:
    reqs, plan = repair_requests(article_ids, ctx)
    if not reqs:
        return
    bid = client.submit_batch(reqs, note=f"full-run repair {b['source']} {len(plan)} articles")
    state["batches"].append({"id": bid, "kind": "repair", "source": b["source"], "status": "submitted",
                             "plan": plan, "requests": len(reqs), "for": b["id"],
                             "at": datetime.now().isoformat(timespec="seconds")})
    say(f"submitted repair batch {bid}: {len(plan)} {b['source']} articles, {len(reqs)} parts")


def collect_repairs(b: dict, ctx: translate.Context) -> None:
    replies = dict(client.batch_results(b["id"]))
    fixed = still = 0
    for aid, part_numbers in b["plan"].items():
        art = repo.load_article(aid)
        parts = translate.flagged_replies(aid)
        if parts is None:
            continue
        for k in part_numbers:
            r = replies.get(f"{translate.custom_id(aid, k)}-r")
            if r is not None and r.data is not None:
                parts[k - 1] = r
        o = translate.finish(art, parts, ctx, allow_repair=False)
        if o.problems:
            still += 1
        else:
            fixed += 1
    say(f"collected repair batch {b['id']} ({b['source']}): {fixed} articles now clean, "
        f"{still} still flagged for a human")


def run(model: str, effort: str, poll: int = POLL) -> int:
    keep_awake()
    ctx = translate.Context(model=model, effort=effort)
    state = load_state()
    submit_translations(state, ctx)
    while True:
        open_batches = [b for b in state["batches"] if b["status"] == "submitted"]
        if not open_batches:
            break
        for b in open_batches:
            st = client.batch_status(b["id"])
            if st.processing_status != "ended":
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
    say("all batches collected. " + summary())
    return 0


def summary() -> str:
    idx = repo.articles_index()
    have = sum(1 for x in idx if repo.load_draft(repo.load_article(x["id"])))
    flagged = len(list(translate.FLAGGED.glob("*.json"))) if translate.FLAGGED.exists() else 0
    return (f"{have}/{len(idx)} articles have a Tamil draft; {flagged} flagged for a human "
            f"(.translate-work/flagged, report.jsonl). Run `pnpm content`, then commit data/entities/drafts.")
