"""Command line: translate <command> [options].

    show       print the request for an article; no API call
    verses     English and IRV verses for a name, Strong's number or word; --accept sets a name
    review-names  go through unreviewed names one by one: accept, correct or reject
    auto-accept-names  accept suggestion 1 where it sounds like the name and the draft was fairly sure
    flag-names  send unchecked names whose Tamil does not sound like the name back to review
    ai-names   ask Claude for the Tamil of the names still in review
    ai-terms   ask Claude to propose the Tamil for the theological glossary
    review-terms  approve the glossary in the browser
    run        translate articles now, one request at a time (pilot, small sets)
    repair     retry flagged articles from their saved replies, with the problems listed
    check      re-check committed drafts against the current glossary and names
    batch      submit | status | collect: bulk runs through the Message Batches API

See docs/feature_dictionary_translation.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import checks, client, prompts, repo, review, session, translate


def select(a) -> list[dict]:
    """Articles named by --ids / positional ids, or by --source with --limit,
    skipping those with a current draft unless --force."""
    ids = list(getattr(a, "ids", None) or [])
    if getattr(a, "ids_file", None):
        with open(a.ids_file, encoding="utf-8") as f:
            ids += [line.strip() for line in f if line.strip() and not line.startswith("#")]
    if not ids and getattr(a, "source", None):
        ids = [x["id"] for x in repo.articles_index() if x["source"] == a.source]
    if not ids:
        raise SystemExit("name articles (eastons/damascus …), --ids-file, or --source")
    out = []
    for i in ids:
        art = repo.load_article(i)
        if translate.is_current(art, getattr(a, "force", False)):
            continue
        out.append(art)
        if getattr(a, "limit", None) and len(out) >= a.limit:
            break
    return out


def ctx_from(a) -> translate.Context:
    return translate.Context(model=a.model, effort=a.effort)


def cmd_show(a) -> int:
    ctx = ctx_from(a)
    art = repo.load_article(a.id)
    reqs = translate.requests_for(art, ctx)
    if a.system:
        print(ctx.system[0]["text"])
        print("\n" + "=" * 72 + "\n")
    print(f"system prompt: {len(ctx.system[0]['text'])} characters "
          f"({len(ctx.terms)} glossary terms); {len(reqs)} request(s)\n")
    for cid, req in reqs:
        print(f"--- {cid}")
        print(req["messages"][0]["content"])
    return 0


def cmd_verses(a) -> int:
    query = " ".join(a.query)
    lk = review.find(query, a.english)
    if not lk.verses:
        raise SystemExit(f"no verses for {query!r} (a name as on the person/place page, a Strong's number, or an English word)")
    if a.accept:
        if lk.kind != "name":
            raise SystemExit("--accept sets a name in names-ta.toml; this is not a person or place name")
        try:
            e = review.accept_name(query, a.accept, lk.verses, a.forms.split(",") if a.forms else None)
        except ValueError as err:
            raise SystemExit(str(err))
        print(f"names-ta.toml: {query} = {e['label']} (reviewed); forms {', '.join(e['forms'])}")
        print("check with `pnpm content`: every form must occur in the name's verses")
        return 0
    if a.html is not None:
        path = Path(a.html) if a.html else repo.WORK / f"verses-{re.sub(r'[^A-Za-z0-9]+', '-', query)}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(review.html_page(lk, a.english, a.limit, a.tcv), encoding="utf-8", newline="\n")
        print(path)
        return 0
    print(review.terminal(lk, a.english, a.limit, a.tcv, color=sys.stdout.isatty() and not a.plain))
    return 0


def cmd_ai_names(a) -> int:
    from . import ai_names

    if a.action == "collect":
        if not a.batch_id:
            raise SystemExit("collect needs a batch id (translate batch status lists them)")
        rows = ai_names.collect(a.batch_id, a.dry_run)
        return ai_report(rows)
    todo = ai_names.items(a.names, a.limit, a.again)
    if not todo:
        print("no names to ask about")
        return 0
    groups = ai_names.groups(todo)
    if a.action == "show":
        print(ai_names.SYSTEM)
        print("\n" + "=" * 72 + "\n")
        print(ai_names.group_message(groups[0]))
        return 0
    if a.action == "plan":
        chars = sum(len(ai_names.group_message(g)) for g in groups)
        print(f"{len(todo)} names in {len(groups)} requests (up to {ai_names.GROUP_NAMES} names each), "
              f"about {chars:,} characters in all, sent with {a.model}. No API call made.\n"
              f"`translate ai-names submit` sends them as a batch at half price; "
              f"`translate ai-names run --limit 20` asks about 20 now.")
        return 0
    if a.action == "submit":
        bid, n = ai_names.submit(todo, a.model, a.effort)
        print(f"submitted {bid}: {len(todo)} names in {n} requests. "
              f"`translate batch status` shows progress; `translate ai-names collect {bid}` when it has ended.")
        return 0
    return ai_report(ai_names.run_direct(todo, a.model, a.effort, a.dry_run, a.workers))


def ai_report(rows: list[dict]) -> int:
    from collections import Counter

    c = Counter(r["action"] for r in rows)
    print(f"\n{c['accept']} accepted, {c['draft']} written as drafts for review, {c['skip']} skipped"
          " (see .translate-work/ai-names.jsonl). Run `pnpm content` to check.")
    return 0


def cmd_ai_terms(a) -> int:
    from . import terms

    if a.action == "collect":
        if not a.batch_id:
            raise SystemExit("collect needs a batch id (translate batch status lists them)")
        return terms_report(terms.collect(a.batch_id, a.dry_run))
    print("gathering the Bible and dictionary evidence for each term…", flush=True)
    items = terms.todo(a.terms, a.again)
    if a.limit:
        items = items[: a.limit]
    if not items:
        print("no terms to ask about (every seed term has an entry; --again asks again)")
        return 0
    groups = terms.groups(items)
    if a.action == "show":
        print(terms.SYSTEM)
        print("\n" + "=" * 72 + "\n")
        print(terms.group_message(groups[0]))
        return 0
    if a.action == "plan":
        chars = sum(len(terms.group_message(g)) for g in groups)
        no_verses = [ev.seed.en for ev in items if not ev.verses]
        print(f"{len(items)} terms in {len(groups)} requests (up to {terms.GROUP_TERMS} terms each), "
              f"about {chars:,} characters in all, sent with {a.model}. No API call made.")
        print(f"{len(no_verses)} have no Bible verses (curated terms): {', '.join(no_verses[:20])}"
              + (" …" if len(no_verses) > 20 else ""))
        print("`translate ai-terms submit` sends them as a batch at half price; "
              "`translate ai-terms run --limit 8` asks about 8 now.")
        return 0
    if a.action == "submit":
        bid, n = terms.submit(items, a.model, a.effort)
        print(f"submitted {bid}: {len(items)} terms in {n} requests. "
              f"`translate batch status` shows progress; `translate ai-terms collect {bid}` when it has ended.")
        return 0
    return terms_report(terms.run_direct(items, a.model, a.effort, a.dry_run, a.workers))


def terms_report(rows: list[dict]) -> int:
    from collections import Counter

    c = Counter(r["action"] for r in rows)
    print(f"\n{c['draft']} proposals written to data/entities/glossary-theology-ta.toml for review, {c['skip']} skipped. "
          "Approve them with `translate review-terms --web`.")
    return 0


def cmd_review_terms(a) -> int:
    from . import termweb

    keys = termweb.queue(a.all, a.include_rejected)
    termweb.serve(termweb.TermSession(keys), port=a.port, open_browser=not a.no_open)
    return 0


def cmd_flag_names(a) -> int:
    rows = session.flag_unlikely(a.below, a.dry_run)
    verb = "would flag" if a.dry_run else "flagged for review"
    print(f"{len(rows)} names {verb}: their Tamil does not sound like the English name (below {a.below})")
    for r in sorted(rows, key=lambda r: r["name"]):
        print(f"  {r['name']:<14} {r['label']}   (sounds {r['sounds']:.2f})")
    if rows and not a.dry_run:
        print(f"Logged in {session.FLAG_LOG.relative_to(repo.ROOT)}. They are back in `translate review-names`.")
    return 0


def cmd_auto_accept(a) -> int:
    if a.names_file:
        repo.NAMES = Path(a.names_file).resolve()
    if a.revert:
        n = session.auto_revert()
        print(f"{n} names put back as they were before auto-accept")
        return 0
    confidence = a.confidence if a.confidence is not None or a.unique_above is not None or a.ai else 0.7
    rows = session.auto_accept(a.sounds, confidence, a.dry_run, a.unique_above, a.ai)
    changed = [r for r in rows if r["label"] != r["before"]["label"]]
    errors = [r for r in rows if "error" in r]
    verb = "would accept" if a.dry_run else "accepted"
    rule = ("Claude's answer, " if a.ai else "") + f"sounds > {a.sounds}"
    if a.unique_above is not None:
        rule += f", no other suggestion > {a.unique_above}"
    if confidence is not None:
        rule += f", confidence > {confidence}"
    print(f"{len(rows)} names {verb} ({rule}); "
          f"{len(rows) - len(changed)} keep their label, {len(changed)} get a new one")
    if a.ai:
        # The drafts already carry Claude's answer: list them all, and say
        # which ones Claude composed (not in the IRV verses).
        changed = rows
    for r in changed[: a.show]:
        if a.ai:
            tag = "   composed: not in the IRV verses" if r.get("source") == "composed" else ""
            print(f"  {r['name']:<20} {r['label']}   (sounds {r['sounds']:.2f}){tag}")
        else:
            print(f"  {r['name']:<20} {r['before']['label']}  →  {r['label']}   (sounds {r['sounds']:.2f})")
    if len(changed) > a.show:
        print(f"  … {len(changed) - a.show} more")
    for r in errors:
        print(f"  not saved: {r['name']}: {r['error']}")
    if not a.dry_run and rows:
        print(f"Logged in {session.AUTO_LOG.relative_to(repo.ROOT)}; `translate auto-accept-names --revert` undoes it. "
              "Run `pnpm content` to check the forms.")
    return 0


def cmd_review_names(a) -> int:
    if a.names_file:
        repo.NAMES = Path(a.names_file).resolve()
    only = None
    if a.ai or a.ai_accepted:
        from . import ai_names

        # --ai: the names Claude answered that still need review;
        # --ai-accepted: the ones its answer settled, to spot-check.
        only = ai_names.accepted() if a.ai_accepted else set(ai_names.answers()) - ai_names.accepted()
        a.all = a.all or a.ai_accepted
    if a.web:
        from . import web

        items = session.queue(a.order, a.start, a.include_rejected, a.all, a.below, only)
        web.serve(session.Session(items), english=a.english, port=a.port, open_browser=not a.no_open)
        return 0
    session.run(order=a.order, start=a.start, include_rejected=a.include_rejected, everything=a.all,
                english=a.english, shown=a.show, color=False if a.plain else None, below=a.below, only=only)
    return 0


def report(outcomes: list[translate.Outcome]) -> int:
    written = sum(o.written for o in outcomes)
    flagged = [o for o in outcomes if o.problems]
    print(f"\n{written}/{len(outcomes)} drafts written; {len(flagged)} with problems "
          f"(listed in {translate.REPORT.relative_to(repo.ROOT)})")
    for o in flagged[:20]:
        print(f"  {o.article_id}{'' if o.written else ' (not written)'}")
        for p in o.problems[:4]:
            print(f"    {p}")
    return 0 if written == len(outcomes) else 1


def cmd_run(a) -> int:
    ctx = ctx_from(a)
    arts = select(a)
    print(f"{len(arts)} article(s) with {ctx.model} at effort {ctx.effort}, {a.workers} at a time")
    from concurrent.futures import ThreadPoolExecutor, as_completed

    client.client()  # one client, shared by the threads
    outcomes = []
    # Each article is its own requests, repair and draft file, so articles run
    # side by side; the report file is locked in translate.record.
    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as pool:
        futures = {pool.submit(translate.translate_direct, art, ctx): art for art in arts}
        for n, f in enumerate(as_completed(futures), 1):
            o = f.result()
            print(f"[{n}/{len(arts)}] {o.article_id}: {'written' if o.written else 'not written'}"
                  + (f", {len(o.problems)} problem(s)" if o.problems else ""), flush=True)
            outcomes.append(o)
    return report(outcomes)


def cmd_repair(a) -> int:
    ctx = ctx_from(a)
    ids = a.ids or [p.stem.replace("__", "/") for p in sorted(translate.FLAGGED.glob("*.json"))]
    outcomes = []
    for i in ids[: a.limit] if a.limit else ids:
        art = repo.load_article(i)
        replies = translate.flagged_replies(i)
        if replies is None or len(replies) != len(prompts.chunks(art)):
            print(f"{i}: no saved replies; translating again", flush=True)
            outcomes.append(translate.translate_direct(art, ctx))
            continue
        print(i, flush=True)
        outcomes.append(translate.finish(art, replies, ctx, allow_repair=True))
    return report(outcomes)


def cmd_check(a) -> int:
    terms, names = repo.reviewed_terms(), repo.reviewed_names()
    bad = total = 0
    for x in repo.articles_index():
        if a.source and x["source"] != a.source:
            continue
        art = repo.load_article(x["id"])
        d = repo.load_draft(art)
        if not d:
            continue
        total += 1
        ps = checks.check_draft(art, d.get("title", ""), d.get("paragraphs", []), terms, names)
        if d.get("source_hash") != art["hash"]:
            ps.insert(0, checks.Problem("draft", "stale: the English article changed"))
        if ps:
            bad += 1
            print(x["id"])
            for p in ps:
                print(f"  {p}")
    print(f"\n{total} drafts checked; {bad} with problems")
    return 0 if bad == 0 else 1


def cmd_batch(a) -> int:
    if a.action == "submit":
        ctx = ctx_from(a)
        arts = select(a)
        reqs = [r for art in arts for r in translate.requests_for(art, ctx)]
        if not reqs:
            print("nothing to translate")
            return 0
        ids = {translate.custom_id(art["id"], 1).rsplit("-", 1)[0]: art["id"] for art in arts}
        if a.dry_run:
            print(f"would submit {len(reqs)} request(s) for {len(arts)} article(s) with {ctx.model}")
            return 0
        bid = client.submit_batch(reqs, note=f"{ctx.model} {ctx.effort} {len(arts)} articles")
        (repo.WORK / f"{bid}.json").write_text(json.dumps({"model": ctx.model, "effort": ctx.effort, "articles": ids}),
                                                encoding="utf-8", newline="\n")
        print(f"submitted {bid}: {len(reqs)} request(s) for {len(arts)} article(s)")
        return 0

    batches = [a.batch_id] if a.batch_id else [b["id"] for b in client.recorded_batches()]
    if a.action == "cancel":
        if not a.batch_id:
            raise SystemExit("cancel needs a batch id (translate batch status lists them)")
        b = client.cancel_batch(a.batch_id)
        print(f"{a.batch_id}: {b.processing_status}. Requests already finished stay done and are billed; "
              "the rest are cancelled. Collect it once it has ended to keep what finished.")
        return 0
    if a.action == "status":
        from datetime import datetime, timezone

        notes = {b["id"]: b.get("note", "") for b in client.recorded_batches()}
        for bid in batches:
            b = client.batch_status(bid)
            c = b.request_counts
            end = b.ended_at or datetime.now(timezone.utc)
            mins = int((end - b.created_at).total_seconds() // 60)
            took = f"took {mins} min" if b.ended_at else f"running {mins} min"
            print(f"{bid}  {b.processing_status} ({took})  processing {c.processing}, succeeded {c.succeeded}, "
                  f"errored {c.errored}, canceled {c.canceled}, expired {c.expired}"
                  + (f"  · {notes[bid]}" if notes.get(bid) else ""))
        return 0

    # collect
    if not a.batch_id:
        raise SystemExit("collect needs a batch id (translate batch status lists them)")
    meta_path = repo.WORK / f"{a.batch_id}.json"
    if not meta_path.exists():
        raise SystemExit(f"{meta_path} is missing: this batch was not submitted from here")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if client.batch_status(a.batch_id).processing_status != "ended":
        raise SystemExit("the batch has not ended yet")
    replies: dict[str, client.Reply] = dict(client.batch_results(a.batch_id))
    ctx = translate.Context(model=meta["model"], effort=meta["effort"])
    outcomes = []
    for prefix, article_id in meta["articles"].items():
        art = repo.load_article(article_id)
        n = len(prompts.chunks(art))
        parts = [replies.get(f"{prefix}-{k}", client.Reply(None, "missing from batch", "")) for k in range(1, n + 1)]
        outcomes.append(translate.finish(art, parts, ctx, allow_repair=False))
    return report(outcomes)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="translate", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def model_opts(p):
        p.add_argument("--model", default=client.DEFAULT_MODEL)
        p.add_argument("--effort", default=client.DEFAULT_EFFORT, choices=["low", "medium", "high", "xhigh", "max"])
        p.add_argument("--workers", type=int, default=client.DEFAULT_WORKERS,
                       help=f"direct runs: requests at a time (default {client.DEFAULT_WORKERS})")

    def select_opts(p, positional=True):
        if positional:
            p.add_argument("ids", nargs="*", help="article ids, e.g. eastons/justification")
        p.add_argument("--ids-file", help="file with one article id per line")
        p.add_argument("--source", choices=["eastons", "smiths", "aquifer"])
        p.add_argument("--limit", type=int)
        p.add_argument("--force", action="store_true", help="redo articles that already have a current draft")

    p = sub.add_parser("show", help="print the request for one article")
    p.add_argument("id")
    p.add_argument("--system", action="store_true", help="print the system prompt too")
    model_opts(p)
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("verses", help="English and IRV verses for a name, Strong's number or word")
    p.add_argument("query", nargs="+", help="Abagtha | G1344 | justified")
    p.add_argument("--english", default="KJV", choices=["KJV", "BSB", "WEB"])
    p.add_argument("--limit", type=int, default=25, help="verses to show")
    p.add_argument("--tcv", action="store_true", help="show the TCV verse too")
    p.add_argument("--html", nargs="?", const="", help="write a page instead (default .translate-work/verses-NAME.html)")
    p.add_argument("--plain", action="store_true", help="mark words with [ ] instead of colour")
    p.add_argument("--accept", metavar="LABEL", help="set this Tamil name in names-ta.toml as reviewed")
    p.add_argument("--forms", help="with --accept: comma-separated forms (default: words in the verses starting like LABEL)")
    p.set_defaults(fn=cmd_verses)

    p = sub.add_parser("review-names", help="review unreviewed names one by one")
    p.add_argument("--order", default="verses", choices=["verses", "alpha"], help="most verses first (default) or A–Z")
    p.add_argument("--start", help="begin at this name")
    p.add_argument("--english", default="KJV", choices=["KJV", "BSB", "WEB"])
    p.add_argument("--show", type=int, default=4, help="verses shown per name (m shows more)")
    p.add_argument("--include-rejected", action="store_true", help="also names rejected in an earlier session")
    p.add_argument("--all", action="store_true", help="also names already reviewed")
    p.add_argument("--below", type=float, metavar="CONFIDENCE", help="only names whose confidence is under this, e.g. 0.6")
    p.add_argument("--plain", action="store_true", help="no colour")
    p.add_argument("--web", action="store_true", help="review in the browser instead of the terminal")
    p.add_argument("--port", type=int, default=8765, help="with --web")
    p.add_argument("--no-open", action="store_true", help="with --web: do not open the browser")
    p.add_argument("--names-file", help="review another copy of names-ta.toml (for trying it out)")
    p.add_argument("--ai", action="store_true", help="only names Claude answered that still need review")
    p.add_argument("--ai-accepted", action="store_true", help="only names whose Claude answer was accepted, to spot-check")
    p.set_defaults(fn=cmd_review_names)

    p = sub.add_parser("ai-names", help="ask Claude for the Tamil of the names still in review")
    p.add_argument("action", nargs="?", default="plan", choices=["plan", "show", "run", "submit", "collect"],
                   help="plan (default): count, no API call; show: print the first request; run: ask now; "
                        "submit/collect: as a batch at half price")
    p.add_argument("batch_id", nargs="?")
    p.add_argument("--names", nargs="+", help="only these names (also reviewed ones)")
    p.add_argument("--limit", type=int)
    p.add_argument("--again", action="store_true", help="also names Claude has answered before")
    p.add_argument("--dry-run", action="store_true", help="ask, but write nothing")
    model_opts(p)
    p.set_defaults(fn=cmd_ai_names)

    p = sub.add_parser("ai-terms", help="ask Claude to propose the Tamil for the theological glossary")
    p.add_argument("action", nargs="?", default="plan", choices=["plan", "show", "run", "submit", "collect"],
                   help="plan (default): count, no API call; show: print the first request; run: ask now; "
                        "submit/collect: as a batch at half price")
    p.add_argument("batch_id", nargs="?")
    p.add_argument("--terms", nargs="+", help="only these seed terms (asks again)")
    p.add_argument("--limit", type=int)
    p.add_argument("--again", action="store_true", help="also terms that already have an entry")
    p.add_argument("--dry-run", action="store_true", help="ask, but write nothing")
    model_opts(p)
    p.set_defaults(fn=cmd_ai_terms)

    p = sub.add_parser("review-terms", help="approve the glossary in the browser")
    p.add_argument("--web", action="store_true", help="(the default: the review is always in the browser)")
    p.add_argument("--port", type=int, default=8766)
    p.add_argument("--no-open", action="store_true")
    p.add_argument("--all", action="store_true", help="also terms already approved")
    p.add_argument("--include-rejected", action="store_true")
    p.set_defaults(fn=cmd_review_terms)

    p = sub.add_parser("flag-names", help="send unchecked names whose Tamil does not sound like the name back to review")
    p.add_argument("--below", type=float, default=0.5, help="flag when the Tamil sounds like the name below this")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_flag_names)

    p = sub.add_parser("auto-accept-names", help="accept suggestion 1 where it clearly matches")
    p.add_argument("--sounds", type=float, default=0.9, help="suggestion 1 must sound like the English name above this")
    p.add_argument("--confidence", type=float, help="the drafted entry's confidence must be above this (default 0.7; none with --unique-above)")
    p.add_argument("--ai", action="store_true", help="accept Claude's answer (translate ai-names) where it sounds above --sounds")
    p.add_argument("--unique-above", type=float, metavar="SOUNDS", help="accept the one suggestion above --sounds when no other suggestion sounds above this")
    p.add_argument("--dry-run", action="store_true", help="list what would change; write nothing")
    p.add_argument("--revert", action="store_true", help="undo the logged auto-accepts")
    p.add_argument("--show", type=int, default=40, help="changed names to list")
    p.add_argument("--names-file", help="work on another copy of names-ta.toml")
    p.set_defaults(fn=cmd_auto_accept)

    p = sub.add_parser("run", help="translate now")
    select_opts(p)
    model_opts(p)
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("repair", help="retry flagged articles")
    p.add_argument("ids", nargs="*")
    p.add_argument("--limit", type=int)
    model_opts(p)
    p.set_defaults(fn=cmd_repair)

    p = sub.add_parser("check", help="re-check committed drafts")
    p.add_argument("--source", choices=["eastons", "smiths", "aquifer"])
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("batch", help="bulk runs")
    p.add_argument("action", choices=["submit", "status", "collect", "cancel"],
                   help="cancel: stop a batch still running (any batch: articles, names or terms)")
    p.add_argument("batch_id", nargs="?")
    select_opts(p, positional=False)
    model_opts(p)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_batch)

    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return a.fn(a)
