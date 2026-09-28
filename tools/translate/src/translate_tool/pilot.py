"""The pilot (docs/feature_dictionary_translation.md §5): the same ~60 articles
(seed/pilot.txt) translated by two models, each into its own folder under
.translate-work/pilot/{model}/, compared blind on a review page
(`translate review-pilot --web`), then one model's drafts adopted into
data/entities/drafts/.
"""

from __future__ import annotations

import json
import shutil
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import client, repo, translate

LIST = Path(__file__).resolve().parents[2] / "seed" / "pilot.txt"
ROOT = repo.WORK / "pilot"
RATINGS = ROOT / "ratings.jsonl"

# Prices per million tokens (Claude API, first party), for the cost summary.
PRICES = {"claude-opus-5": (5.0, 25.0), "claude-sonnet-5": (2.0, 10.0), "claude-opus-5-5": (4.0, 20.0),
          "claude-haiku-4-5": (1.0, 5.0)}


def load(article_id: str) -> dict:
    """What the review page shows for one pilot item."""
    return repo.load_article(article_id)


def ids() -> list[str]:
    return [l.strip() for l in LIST.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


def folder(model: str) -> Path:
    return ROOT / model


def models() -> list[str]:
    return sorted(p.name for p in ROOT.iterdir() if p.is_dir()) if ROOT.exists() else []


def use_folder(model: str) -> None:
    """Point drafts, the report and saved replies at this model's pilot folder."""
    f = folder(model)
    repo.DRAFTS = f / "drafts"
    translate.REPORT = f / "report.jsonl"
    translate.FLAGGED = f / "flagged"
    f.mkdir(parents=True, exist_ok=True)


def run(model: str, effort: str, workers: int, force: bool = False) -> list[translate.Outcome]:
    use_folder(model)
    ctx = translate.Context(model=model, effort=effort)
    arts = [repo.load_article(i) for i in ids()]
    arts = [a for a in arts if force or not translate.is_current(a)]
    print(f"{len(arts)} pilot articles with {model} at effort {effort}, {workers} at a time "
          f"→ {folder(model)}", flush=True)
    client.client()
    outcomes = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(translate.translate_direct, a, ctx): a for a in arts}
        for n, fut in enumerate(as_completed(futures), 1):
            o = fut.result()
            print(f"[{n}/{len(arts)}] {o.article_id}: {'written' if o.written else 'NOT written'}"
                  + (f", {len(o.problems)} problem(s)" if o.problems else ""), flush=True)
            outcomes.append(o)
    return outcomes


def draft(model: str, article: dict) -> dict | None:
    sub = "ta-sa" if repo.is_sharealike(article) else "ta"
    source, slug = article["id"].split("/", 1)
    p = folder(model) / "drafts" / sub / source / f"{slug}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def problems(model: str) -> dict[str, list[str]]:
    """Article id → the problems left after the repair turn (last report line)."""
    p = folder(model) / "report.jsonl"
    out: dict[str, list[str]] = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["id"]] = r["problems"]
    return out


def usage(model: str) -> dict:
    """Tokens and cost of this model's pilot requests, from the usage log."""
    cids = {translate.custom_id(i, k) for i in ids() for k in range(1, 20)}
    cids |= {c + "-r" for c in cids}
    tok = Counter({k: 0 for k in ("input", "cache_read", "cache_write", "output")})
    n = 0
    if client.USAGE_LOG.exists():
        for line in client.USAGE_LOG.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["model"].startswith(model) and r["id"] in cids and r["kind"] == "direct":
                n += 1
                for k in ("input", "cache_read", "cache_write", "output"):
                    tok[k] += r[k]
    pin, pout = PRICES.get(model, (0.0, 0.0))
    cost = (tok["input"] + 1.25 * tok["cache_write"] + 0.1 * tok["cache_read"]) * pin / 1e6 + tok["output"] * pout / 1e6
    return {"requests": n, **tok, "cost": cost}


def ratings() -> dict[str, dict]:
    """Article id → the latest rating."""
    out = {}
    if RATINGS.exists():
        for line in RATINGS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["id"]] = r
    return out


def status() -> str:
    lines = []
    all_ids = ids()
    words = sum(sum(len(p["text"].split()) for p in repo.load_article(i)["paragraphs"]) for i in all_ids)
    lines.append(f"{len(all_ids)} pilot articles, {words:,} English words")
    for m in models():
        arts = {i: draft(m, repo.load_article(i)) for i in all_ids}
        done = sum(d is not None for d in arts.values())
        probs = problems(m)
        flagged = sum(1 for i in all_ids if probs.get(i))
        kinds = Counter(p.split(": ", 1)[1].split(":")[0].split(" ")[0] for i in all_ids for p in probs.get(i, []))
        u = usage(m)
        per = u["cost"] / done if done else 0
        lines.append(f"\n{m}: {done}/{len(all_ids)} drafts written, {flagged} with problems left "
                     f"({', '.join(f'{k} {v}' for k, v in kinds.most_common(5)) or 'none'})")
        lines.append(f"  {u['requests']} requests, {u['input'] + u['cache_read'] + u['cache_write']:,} input and "
                     f"{u['output']:,} output tokens, about ${u['cost']:.2f} (${per:.3f} per article, direct price)")
        if done:
            total_words = 1_895_000  # the three dictionaries, English words (§2)
            est = u["cost"] / words * total_words
            lines.append(f"  at this rate all 13,147 articles: about ${est:,.0f} direct, ${est / 2:,.0f} as batches")
    r = ratings()
    if r:
        c = Counter(x["winner"] for x in r.values())
        lines.append(f"\nratings ({len(r)} articles): " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
    return "\n".join(lines)


def adopt(model: str, keep_problems: bool = True) -> tuple[int, int]:
    """Copy this model's pilot drafts into data/entities/drafts/ (ta/ or ta-sa/)."""
    copied = skipped = 0
    probs = problems(model)
    for i in ids():
        art = repo.load_article(i)
        d = draft(model, art)
        if d is None or (not keep_problems and probs.get(i)):
            skipped += 1
            continue
        sub = "ta-sa" if repo.is_sharealike(art) else "ta"
        source, slug = i.split("/", 1)
        src = folder(model) / "drafts" / sub / source / f"{slug}.json"
        dst = repo.ENTITIES / "drafts" / sub / source / f"{slug}.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied += 1
    return copied, skipped
