"""The commentary pilot (docs/feature_commentary_translation.md §6): the units in
seed/commentary-pilot.txt translated by two models, each into its own folder
under .translate-work/commentary/pilot/{model}/, compared blind on the same
review page as the dictionary pilot (`translate commentary review`), then one
model's drafts adopted into the bible-commentaries repository.

The functions the review page needs (ids, models, load, draft, problems,
ratings, status, ROOT, RATINGS) mirror pilot.py.
"""

from __future__ import annotations

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import client, commentary, translate
from .pilot import PRICES

LIST = Path(__file__).resolve().parents[2] / "seed" / "commentary-pilot.txt"
ROOT = commentary.WORK / "pilot"
RATINGS = ROOT / "ratings.jsonl"


def ids() -> list[str]:
    return [l.split("#")[0].strip() for l in LIST.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def folder(model: str) -> Path:
    return ROOT / model


def models() -> list[str]:
    return sorted(p.name for p in ROOT.iterdir() if p.is_dir()) if ROOT.exists() else []


def use_folder(model: str | None) -> None:
    """Point drafts, the report and saved replies at this model's pilot folder
    (None: back to the repository and the usual work folder)."""
    if model is None:
        commentary.DRAFTS_ROOT = None
        commentary.REPORT = commentary.WORK / "report.jsonl"
        commentary.FLAGGED = commentary.WORK / "flagged"
        return
    f = folder(model)
    f.mkdir(parents=True, exist_ok=True)
    commentary.DRAFTS_ROOT = f / "drafts"
    commentary.REPORT = f / "report.jsonl"
    commentary.FLAGGED = f / "flagged"


def _shown(p: dict, text: str, anchor: str | None) -> str:
    """One paragraph as the review page shows it: its anchor, footnote or verse first."""
    lead = []
    if p.get("verse"):
        lead.append(f"[{p['verse']}]")
    if p.get("footnote"):
        lead.append(f"(footnote {p.get('label', '')})")
    if p.get("author"):
        lead.append(f"{p['author']}:")
    if anchor:
        lead.append(f"«{anchor}» —")
    return " ".join([*lead, text])


def load(unit_id: str) -> dict:
    """The unit as the review page shows it: a title and one line per paragraph."""
    u = commentary.load_unit(unit_id)
    title = f"{commentary.label(u)}{' · ' + u['title'] if u.get('title') else ''}"
    return {"id": u["id"], "title": title, "unit": u,
            "paragraphs": [{"id": p["id"], "text": _shown(p, p["text"], p.get("anchor")), "heading": p.get("heading", False)}
                           for p in u["paragraphs"]]}


def draft(model: str, shown: dict) -> dict | None:
    """This model's pilot draft of the unit, in the same shape as load()."""
    u = shown["unit"]
    saved = commentary.DRAFTS_ROOT
    commentary.DRAFTS_ROOT = folder(model) / "drafts"
    try:
        d = commentary.load_draft(u)
    finally:
        commentary.DRAFTS_ROOT = saved
    if d is None:
        return None
    en = {p["id"]: p for p in u["paragraphs"]}
    return {"title": d.get("title", ""),
            "paragraphs": [{"id": p["id"], "text": _shown(en.get(p["id"], {}), p["text"], p.get("anchor"))}
                           for p in d["paragraphs"]]}


def problems(model: str) -> dict[str, list[str]]:
    p = folder(model) / "report.jsonl"
    out: dict[str, list[str]] = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["id"]] = r["problems"]
    return out


def ratings() -> dict[str, dict]:
    out = {}
    if RATINGS.exists():
        for line in RATINGS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["id"]] = r
    return out


def usage(model: str) -> dict:
    cids = {translate.custom_id(i, k) for i in ids() for k in range(1, 20)}
    cids |= {c + "-r" for c in cids}
    tok = Counter({k: 0 for k in ("input", "cache_read", "cache_write", "output")})
    n = 0
    if client.USAGE_LOG.exists():
        for line in client.USAGE_LOG.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["model"].startswith(model) and r["id"] in cids and r["kind"] == "direct":
                n += 1
                for k in tok:
                    tok[k] += r[k]
    pin, pout = PRICES.get(model, (0.0, 0.0))
    cost = (tok["input"] + 1.25 * tok["cache_write"] + 0.1 * tok["cache_read"]) * pin / 1e6 + tok["output"] * pout / 1e6
    return {"requests": n, **tok, "cost": cost}


def run(model: str, effort: str, workers: int, force: bool = False) -> list[translate.Outcome]:
    use_folder(model)
    try:
        ctx = commentary.Context(model=model, effort=effort)
        units = [commentary.load_unit(i) for i in ids()]
        units = [u for u in units if force or not commentary.is_current(u)]
        print(f"{len(units)} pilot units with {model} at effort {effort}, {workers} at a time → {folder(model)}", flush=True)
        client.client()
        outcomes = []
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {pool.submit(commentary.translate_direct, u, ctx): u for u in units}
            for n, fut in enumerate(as_completed(futures), 1):
                o = fut.result()
                print(f"[{n}/{len(units)}] {o.article_id}: {'written' if o.written else 'NOT written'}"
                      + (f", {len(o.problems)} problem(s)" if o.problems else ""), flush=True)
                outcomes.append(o)
        return outcomes
    finally:
        use_folder(None)


def status() -> str:
    all_ids = ids()
    units = {i: commentary.load_unit(i) for i in all_ids}
    words = sum(commentary.english_words(u) for u in units.values())
    lines = [f"{len(all_ids)} pilot units, {words:,} English words"]
    for m in models():
        done = sum(draft(m, load(i)) is not None for i in all_ids)
        probs = problems(m)
        flagged = sum(1 for i in all_ids if probs.get(i))
        kinds = Counter(p.split(": ", 1)[1].split(":")[0].split(" ")[0] for i in all_ids for p in probs.get(i, []))
        u = usage(m)
        lines.append(f"\n{m}: {done}/{len(all_ids)} drafts written, {flagged} with problems left "
                     f"({', '.join(f'{k} {v}' for k, v in kinds.most_common(6)) or 'none'})")
        lines.append(f"  {u['requests']} requests, {u['input'] + u['cache_read'] + u['cache_write']:,} input and "
                     f"{u['output']:,} output tokens, about ${u['cost']:.2f} direct (${u['cost'] / max(1, words) * 1e6:,.0f} per million English words)")
    r = ratings()
    if r:
        c = Counter(x["winner"] for x in r.values())
        lines.append(f"\nratings ({len(r)} units): " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
    return "\n".join(lines)


def report_html(model: str) -> Path:
    """One page to read a model's pilot drafts: English beside Tamil for each
    unit, with the problems the checks still find. Written to the model's folder."""
    import html

    from . import repo

    terms, names = repo.reviewed_terms(), repo.reviewed_names()
    esc = html.escape
    parts = []
    for i in ids():
        u = commentary.load_unit(i)
        commentary.DRAFTS_ROOT = folder(model) / "drafts"
        d = commentary.load_draft(u)
        commentary.DRAFTS_ROOT = None
        if d is None:
            continue
        ta = {x["id"]: x for x in d["paragraphs"]}
        probs = [q for q in commentary.check_unit(u, d.get("title", ""), d["paragraphs"], terms, names)
                 if not q.what.startswith("ids differ")]
        rows = []
        for p in u["paragraphs"]:
            x = ta.get(p["id"], {})
            lead_en = _shown(p, "", p.get("anchor")).strip()
            lead_ta = _shown(p, "", x.get("anchor")).strip()
            rows.append(f'<tr><td class="en">{"<b>" + esc(lead_en) + "</b> " if lead_en else ""}{esc(p["text"])}</td>'
                        f'<td class="ta" lang="ta">{"<b>" + esc(lead_ta) + "</b> " if lead_ta else ""}{esc(x.get("text", "—"))}</td></tr>')
        flag = "".join(f"<li>{esc(str(q))}</li>" for q in probs)
        title = esc(commentary.label(u)) + (f" · {esc(u['title'])}" if u.get("title") else "")
        title_ta = f' · <span lang="ta">{esc(d["title"])}</span>' if d.get("title") else ""
        parts.append(f'<section id="{esc(i)}"><h2><span class="src">{esc(u["source"])}</span> {title}{title_ta}</h2>'
                     + (f'<ul class="probs">{flag}</ul>' if flag else "")
                     + f'<table>{"".join(rows)}</table></section>')
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Commentary pilot · {esc(model)}</title>
<style>
body {{ font-family: 'Noto Sans', system-ui, sans-serif; margin: 0 auto; max-width: 1200px; padding: 1.5rem 1rem 4rem; color: #1f1b16; background: #fbf7f0; }}
h1 {{ font-size: 1.4rem; }} h2 {{ font-size: 1.05rem; margin: 2.2rem 0 0.6rem; }}
.src {{ font-size: 0.75rem; background: #b9862c; color: #fff; border-radius: 6px; padding: 0.1rem 0.45rem; margin-right: 0.3rem; }}
table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
td {{ vertical-align: top; padding: 0.6rem 0.8rem; border-top: 1px solid #e3dccf; line-height: 1.6; }}
td.en {{ font-family: Georgia, serif; font-size: 0.95rem; color: #3d352c; }}
td.ta, [lang=ta] {{ font-family: 'Mukta Malar', 'Noto Sans Tamil', 'Nirmala UI', sans-serif; font-size: 1.02rem; }}
.probs {{ background: #fff4e0; border-left: 3px solid #d98b1a; margin: 0 0 0.5rem; padding: 0.5rem 1.6rem; font-size: 0.85rem; }}
@media (max-width: 720px) {{ td {{ display: block; }} td.ta {{ border-top: 0; background: #f3ede2; }} }}
</style></head><body><h1>Commentary pilot · {esc(model)}</h1><pre>{esc(status())}</pre>{"".join(parts)}</body></html>"""
    out = folder(model) / "review.html"
    out.write_text(page, encoding="utf-8", newline="\n")
    return out


def adopt(model: str, keep_problems: bool = True) -> tuple[int, int]:
    """Copy this model's pilot drafts into the bible-commentaries repository (ta/, ta-ecf/)."""
    copied = skipped = 0
    probs = problems(model)
    for i in ids():
        u = commentary.load_unit(i)
        commentary.DRAFTS_ROOT = folder(model) / "drafts"
        d = commentary.load_draft(u)
        commentary.DRAFTS_ROOT = None
        if d is None or (not keep_problems and probs.get(i)):
            skipped += 1
            continue
        commentary.write_draft(u, d)
        copied += 1
    return copied, skipped
