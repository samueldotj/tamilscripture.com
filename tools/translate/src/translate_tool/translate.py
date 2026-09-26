"""One article from English to a Tamil draft: requests, checks, one repair
turn, and the draft file in the shape feature_dictionary.md §5 fixes."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import date

from . import checks, client, prompts, repo
from .client import Reply

REPORT = repo.WORK / "report.jsonl"
_REPORT_LOCK = threading.Lock()  # articles run in parallel (translate run --workers)
FLAGGED = repo.WORK / "flagged"


@dataclass
class Context:
    """Everything shared by the articles of one run."""

    model: str = client.DEFAULT_MODEL
    effort: str = client.DEFAULT_EFFORT
    terms: dict = field(default_factory=repo.reviewed_terms)
    names: dict = field(default_factory=repo.reviewed_names)
    system: list = field(init=False)

    def __post_init__(self):
        self.system = prompts.system_blocks(self.terms)


def custom_id(article_id: str, part: int) -> str:
    """Batch ids allow [A-Za-z0-9_-]{1,64}; article ids have slashes."""
    return hashlib.sha1(article_id.encode()).hexdigest()[:20] + f"-{part}"


def is_current(article: dict, force: bool = False) -> bool:
    """A draft exists for this English text and this prompt version."""
    if force:
        return False
    d = repo.load_draft(article)
    return bool(
        d
        and d.get("source_hash") == article["hash"]
        and d.get("generator", {}).get("prompt_version") == prompts.PROMPT_VERSION
    )


def title_hint(article: dict) -> str | None:
    """The Tamil title a sibling article (same headword, other dictionary) already has."""
    for sib in article.get("also_in", []):
        try:
            d = repo.load_draft(repo.load_article(sib["id"]))
        except SystemExit:
            continue
        if d and d.get("title"):
            return d["title"]
    return None


def requests_for(article: dict, ctx: Context) -> list[tuple[str, dict]]:
    """(custom_id, params) for each part of the article."""
    parts = prompts.chunks(article)
    hint = title_hint(article)
    out = []
    for k, paras in enumerate(parts, 1):
        msg = prompts.user_message(article, paras, (k, len(parts)), ctx.names, hint)
        out.append((custom_id(article["id"], k), client.params(ctx.system, [{"role": "user", "content": msg}], ctx.model, ctx.effort)))
    return out


def part_problems(article: dict, paras: list[dict], reply: Reply, ctx: Context) -> list[checks.Problem]:
    if reply.data is None:
        return [checks.Problem("response", reply.error or "no reply")]
    sub = {**article, "paragraphs": paras}
    return checks.check_draft(sub, reply.data.get("title", ""), reply.data.get("paragraphs", []), ctx.terms, ctx.names)


HARD = ("empty", "no Tamil script", "contains HTML", "longer than", "ids differ", "no reply", "refused", "invalid JSON", "max_tokens", "errored", "gave up")


def is_hard(p: checks.Problem) -> bool:
    return any(h in p.what for h in HARD) or p.where == "response"


@dataclass
class Outcome:
    article_id: str
    written: bool
    problems: list[checks.Problem]


def repair(req: dict, reply: Reply, problems: list[checks.Problem], custom: str) -> Reply:
    """One more turn: the first answer and the list of problems."""
    if not reply.text:
        return client.run_direct(req, custom)  # nothing to repair: ask again
    messages = req["messages"] + [
        {"role": "assistant", "content": reply.text},
        {"role": "user", "content": prompts.repair_message(problems)},
    ]
    return client.run_direct({**req, "messages": messages}, custom + "-r")


def finish(article: dict, replies: list[Reply], ctx: Context, allow_repair: bool) -> Outcome:
    """Check each part, repair once if allowed, write the draft unless a part
    still has a problem the build would reject."""
    parts = prompts.chunks(article)
    reqs = requests_for(article, ctx) if allow_repair else []
    final: list[Reply] = []
    problems: list[checks.Problem] = []
    for k, (paras, reply) in enumerate(zip(parts, replies)):
        ps = part_problems(article, paras, reply, ctx)
        if ps and allow_repair:
            cid, req = reqs[k]
            print(f"  part {k + 1}: {len(ps)} problem(s); repairing", flush=True)
            reply = repair(req, reply, ps, cid)
            ps = part_problems(article, paras, reply, ctx)
        final.append(reply)
        problems += ps

    written = not any(is_hard(p) for p in problems)
    if written:
        title = next((r.data["title"].strip() for r in final if r.data and r.data.get("title")), "")
        paragraphs = [{"id": p["id"], "text": p["text"].strip()} for r in final for p in r.data["paragraphs"]]
        repo.write_draft(article, {
            "id": article["id"],
            "lang": "ta",
            "source_hash": article["hash"],
            "generator": {
                "name": "claude",
                "model": ctx.model,
                "prompt_version": prompts.PROMPT_VERSION,
                "generated_at": date.today().isoformat(),
            },
            "title": title,
            "paragraphs": paragraphs,
        })
    record(article, written, problems, final)
    return Outcome(article["id"], written, problems)


def record(article: dict, written: bool, problems: list[checks.Problem], replies: list[Reply]) -> None:
    """A report line per article; unwritten or flagged articles also keep
    their raw replies so `translate repair` can continue from them."""
    repo.WORK.mkdir(exist_ok=True)
    with _REPORT_LOCK, open(REPORT, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"id": article["id"], "written": written,
                            "problems": [str(p) for p in problems]}, ensure_ascii=False) + "\n")
    path = FLAGGED / (article["id"].replace("/", "__") + ".json")
    if problems:
        FLAGGED.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([r.text for r in replies], ensure_ascii=False), encoding="utf-8", newline="\n")
    elif path.exists():
        path.unlink()


def flagged_replies(article_id: str) -> list[Reply] | None:
    path = FLAGGED / (article_id.replace("/", "__") + ".json")
    if not path.exists():
        return None
    out = []
    for text in json.loads(path.read_text(encoding="utf-8")):
        try:
            out.append(Reply(json.loads(text), None, text))
        except json.JSONDecodeError:
            out.append(Reply(None, "invalid JSON", text))
    return out


def translate_direct(article: dict, ctx: Context) -> Outcome:
    replies = [client.run_direct(req, cid) for cid, req in requests_for(article, ctx)]
    return finish(article, replies, ctx, allow_repair=True)
