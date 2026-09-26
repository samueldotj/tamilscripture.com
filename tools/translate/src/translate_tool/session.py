"""`translate review-names`: go through the unreviewed names in
data/entities/names-ta.toml one at a time, show the English and IRV verses,
and accept, correct or reject each. Every answer is written to the file at
once, so the session can stop anywhere and resume later.

`Session` holds the queue and the answers; the terminal loop here and the
browser page in web.py are two front ends to it.

Reject keeps the entry for review but sets its confidence to 0, which hides
the wrong Tamil on the site (entity-ingest shows an unreviewed name only when
it is well attested) and keeps it out of later sessions.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from dataclasses import dataclass, field

from . import repo, review
from .review import ANSI, TAMIL_WORD, base_of


def guess_label(words: list[tuple[str, int]]) -> str:
    """The base form a group of spellings share: a spelling that is itself a
    base of the others wins; otherwise the commonest derived base."""
    spelled = dict(words)
    bases: Counter = Counter()
    for w, n in words:
        bases[base_of(w)] += n
    attested = [b for b in bases if b in spelled]
    pool = attested or list(bases)
    return max(pool, key=lambda b: (bases[b], -len(b)))


@dataclass
class Item:
    name: str
    entry: dict
    verses: list[str]


@dataclass
class Suggestion:
    label: str
    covered: int
    sounds: float
    words: list[tuple[str, int]]
    ai: bool = False  # Claude's answer (translate ai-names)


def queue(order: str, start: str | None, include_rejected: bool, everything: bool,
          below: float | None = None, only: set[str] | None = None) -> list[Item]:
    """Names to review; with `below`, only those whose confidence is under it;
    with `only`, only those names."""
    names = repo.load_names()
    verses = review.name_verses()
    items = []
    for name, e in names.items():
        if only is not None and name not in only:
            continue
        if not everything and not e.get("review"):
            continue
        if not include_rejected and e.get("review") and e.get("confidence", 1) == 0:
            continue
        if below is not None and e.get("confidence", 1) >= below:
            continue
        vs = sorted(verses.get(name, ()), key=review.verse_order)
        if vs:
            items.append(Item(name, e, vs))
    if order == "verses":
        items.sort(key=lambda i: (-len(i.verses), i.name))
    if start:
        if order == "verses":
            idx = next((k for k, i in enumerate(items) if i.name == start), 0)
        else:
            idx = next((k for k, i in enumerate(items) if i.name.lower() >= start.lower()), len(items))
        items = items[idx:]
    return items


def suggest(item: Item, with_ai: bool = True) -> tuple[list[review.Candidate], list[Suggestion]]:
    """The candidates and up to five distinct base-form suggestions; Claude's
    answer first when there is one (translate ai-names)."""
    cands = review.candidates(item.verses, name=item.name, top=8)
    out: list[Suggestion] = []
    if with_ai:
        from . import ai_names

        if (ai := ai_names.answers().get(item.name)) and review.TAMIL_NAME.fullmatch(ai.get("label") or "-"):
            forms = [(f, 1) for f in ai.get("forms", [])] or [(ai["label"], 0)]
            out.append(Suggestion(ai["label"], 0, round(review.sounds_like(ai["label"], item.name), 2), forms, ai=True))
    for c in cands:
        label = guess_label(c.words)
        if all(s.label != label for s in out):
            out.append(Suggestion(label, c.covered, c.sounds, c.words))
    return cands, out[:5]


def state_of(entry: dict) -> str:
    if entry.get("review") and entry.get("confidence", 1) == 0:
        return "rejected"
    return "needs review" if entry.get("review") else "reviewed"


@dataclass
class Session:
    items: list[Item]
    i: int = 0
    counts: Counter = field(default_factory=Counter)
    history: list[tuple[str, dict, int, str]] = field(default_factory=list)  # (name, entry before, index, what)

    @property
    def current(self) -> Item | None:
        return self.items[self.i] if self.i < len(self.items) else None

    def accept(self, label: str, forms: list[str] | None = None) -> dict:
        """Save `label` (and the forms, or those found in the verses) as the
        reviewed name. Raises ValueError when it cannot be saved."""
        item = self.current
        if item is None:
            raise ValueError("no name left in this session")
        label = " ".join(label.split())
        before = dict(item.entry)
        after = review.accept_name(item.name, label, item.verses, forms)
        self._done(item, before, after, "accepted")
        return after

    def keep(self) -> dict:
        item = self.current
        return self.accept(item.entry["label"], list(item.entry["forms"])) if item else {}

    def reject(self) -> dict:
        item = self.current
        if item is None:
            raise ValueError("no name left in this session")
        before = dict(item.entry)
        after = {**item.entry, "confidence": 0.0, "review": True}
        repo.save_name(item.name, after)
        self._done(item, before, after, "rejected")
        return after

    def skip(self) -> None:
        if self.current is not None:
            self.counts["skipped"] += 1
            self.i += 1

    def undo(self) -> str | None:
        """Restore the last saved answer and go back to that name."""
        if not self.history:
            return None
        name, before, i, what = self.history.pop()
        repo.save_name(name, before)
        self.items[i].entry = before
        self.i = i
        self.counts[what] -= 1
        self.counts["undone"] += 1
        return name

    def _done(self, item: Item, before: dict, after: dict, what: str) -> None:
        self.history.append((item.name, before, self.i, what))
        item.entry = after
        self.counts[what] += 1
        self.i += 1

    def summary(self) -> str:
        c = self.counts
        undone = f", {c['undone']} undone" if c["undone"] else ""
        return (f"{c['accepted']} accepted, {c['rejected']} rejected, {c['skipped']} skipped{undone}; "
                f"{len(self.items) - self.i} left in this list.")


AUTO_LOG = repo.WORK / "auto-accepted.jsonl"


def auto_accept(min_sounds: float, min_confidence: float | None, dry_run: bool = False,
                unique_above: float | None = None, ai: bool = False) -> list[dict]:
    """Accept a suggestion for every unreviewed name where it clearly matches.

    Default rule: suggestion 1 sounds like the English name (consonant match
    > min_sounds) and the drafted entry was fairly sure (confidence >
    min_confidence).

    With `unique_above`: the one suggestion that sounds (as the review page
    shows it) > min_sounds, when no other suggestion sounds > unique_above;
    confidence is not considered unless min_confidence is given.

    With `ai`: Claude's answer (translate ai-names) for the names it could not
    settle, when it sounds (as the review page shows it) > min_sounds. Names
    of several words are allowed, since Claude gave the whole name.

    Each change is logged with the entry it replaced, and the file is backed
    up first, so a run can be undone with `auto_revert`."""
    done = []
    ai_answers: dict = {}
    if ai:
        from . import ai_names

        ai_answers = ai_names.answers()
        items = queue("verses", None, False, False, only=set(ai_answers) - ai_names.accepted())
    else:
        items = queue("verses", None, False, False)
    if min_confidence is not None:
        items = [i for i in items if i.entry.get("confidence", 1) > min_confidence]
    if not dry_run and items:
        repo.WORK.mkdir(exist_ok=True)
        backup = repo.WORK / f"names-ta.before-auto-{datetime.now():%Y%m%d-%H%M%S}.toml"
        backup.write_text(repo.NAMES.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    for item in items:
        # Compound and descriptive names (Hamath-zobah, Valley of Rephaim) are
        # several Tamil words; one suggested word is never the whole name.
        if not ai and ("-" in item.name or " " in item.name):
            continue
        # One consonant (Haroeh "r", Evi "v") matches too many words to trust.
        if len(review.skeleton_en(item.name)) < 2:
            continue
        if ai:
            answer = ai_answers.get(item.name, {})
            label = " ".join((answer.get("label") or "").split())
            if not review.TAMIL_NAME.fullmatch(label or "-"):
                continue
            pick = Suggestion(label, 0, review.sounds_like(label, item.name), [], ai=True)
            sounds = pick.sounds
            if sounds <= min_sounds:
                continue
            suggestions = [pick]
        else:
            _, suggestions = suggest(item, with_ai=False)
        if not suggestions:
            continue
        if ai:
            pass
        elif unique_above is None:
            pick = suggestions[0]
            # Judge the label itself, not the spellings it came from, so a
            # label that kept an ending (ஏலிமைவிட்டு) does not pass; and on
            # consonants alone, without the ranking's same-first-letter bonus,
            # so a neighbour's name (Peruda → சொபெரேத்) does not either.
            sounds = review.consonant_match(pick.label, item.name)
            if min(pick.sounds, sounds) <= min_sounds:
                continue
        else:
            # The page's "sounds", taken on the label too so a kept ending
            # does not count; exactly one suggestion may come near.
            scored = [(min(g.sounds, review.sounds_like(g.label, item.name)), g) for g in suggestions]
            near = [(v, g) for v, g in scored if v > unique_above]
            if len(near) != 1 or near[0][0] <= min_sounds:
                continue
            sounds, pick = near[0]
        if not review.same_start(pick.label, item.name):
            continue
        # Two consonants or fewer cannot tell neighbours apart (Esek "sk" is
        # also ஈசாக், Isaac): the vowels must agree too, and somewhat for
        # every name (Sallai is not சல்லு, Sallu).
        full = review.full_match(pick.label, item.name)
        if full < 0.72 or (len(review.skeleton_en(item.name)) <= 2 and full <= 0.8):
            continue
        # Tamil drops a final ு before an ending, so a base made by removing
        # one can be a letter short: Greek names in -us end in ு (குவர்த்து,
        # not குவர்த்), and no Tamil word ends in a nasal and a bare stop
        # (கிலேமெந்து, not கிலேமெந்த்).
        if item.name.lower().endswith("us") and not pick.label.endswith("ு"):
            continue
        if re.search("[ஙஞணநமன]்[கசடதபற]்$", pick.label):
            continue
        # A name ending in a vowel does not end in a bare consonant in Tamil;
        # such a label lost its last letter to the ending rules (Rhoda ரோத்).
        # Women's names take ாள் (Susanna சூசன்னாள்), which is right.
        if (item.name.lower().rstrip("h")[-1:] in "aeiou" and pick.label.endswith("்")
                and not pick.label.endswith("ாள்")):
            continue
        # A label ending in ே is usually the vocative ("Woe to you,
        # Chorazin!" கோராசீனே) unless the name itself ends so (Gethsemane).
        if pick.label.endswith("ே") and not item.name.lower().endswith("e"):
            continue
        row = {"name": item.name, "before": item.entry, "label": pick.label, "sounds": round(sounds, 2),
               "confidence": item.entry.get("confidence", 1), "full": full, "_verses": item.verses}
        if ai:
            row["source"] = ai_answers[item.name].get("source")
        done.append(row)

    # One Tamil name for two English names means one of them took a
    # neighbour's (Jabal and Jubal, Genesis 4:20–21, both யாபால்): keep a name
    # only when it matches clearly better than every other name with that
    # label, including names already reviewed.
    reviewed = {e["label"]: n for n, e in repo.load_names().items() if not e.get("review")}
    by_label: dict[str, list[dict]] = {}
    for row in done:
        by_label.setdefault(row["label"], []).append(row)
    kept = []
    for label, rows in by_label.items():
        rivals = [(review.full_match(label, reviewed[label]), reviewed[label])] if label in reviewed else []
        for row in rows:
            others = [f for f, n in rivals if n != row["name"]] + [r["full"] for r in rows if r is not row]
            if all(row["full"] > f + 0.1 for f in others):
                kept.append(row)

    for row in kept:
        verses = row.pop("_verses")
        row.pop("full")
        if not dry_run:
            try:
                row["after"] = review.accept_name(row["name"], row["label"], verses)
            except ValueError as err:
                if ai:
                    # Claude composed it: nothing in the verses to find; the
                    # label stands alone, with no forms to underline.
                    row["after"] = review.accept_name(row["name"], row["label"], verses, forms=[])
                else:
                    row["error"] = str(err)
            with open(AUTO_LOG, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps({**row, "at": datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False) + "\n")
    return kept


def auto_revert() -> int:
    """Put back every entry the auto-accept log changed, newest first."""
    if not AUTO_LOG.exists():
        return 0
    rows = [json.loads(l) for l in AUTO_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    for row in reversed(rows):
        if "after" in row:
            repo.save_name(row["name"], row["before"])
    AUTO_LOG.rename(AUTO_LOG.with_suffix(f".reverted-{datetime.now():%Y%m%d-%H%M%S}.jsonl"))
    return sum("after" in r for r in rows)


FLAG_LOG = repo.WORK / "flagged-names.jsonl"


def flag_unlikely(below: float = 0.5, dry_run: bool = False) -> list[dict]:
    """Mark for review the names without `review = true` whose Tamil (label
    or any of its first forms) does not sound like the English name: the
    aligner was confident, but nobody checked (Moza பெற்றான், "begat").
    Auto-accepted names were matched on sound already and are left alone, as
    are compound and descriptive names, whose Tamil is a translation. The
    confidence is kept, so a flagged name is not treated as rejected."""
    auto = set()
    if AUTO_LOG.exists():
        auto = {json.loads(l)["name"] for l in AUTO_LOG.read_text(encoding="utf-8").splitlines() if l.strip()}
    rows = []
    for name, e in repo.load_names().items():
        if e.get("review") or name in auto or " " in name or "-" in name:
            continue
        sounds = max(review.sounds_like(review.base_of(f), name) for f in [e["label"], *e["forms"][:5]])
        if sounds < below:
            rows.append({"name": name, "label": e["label"], "sounds": round(sounds, 2), "before": e})
    if not dry_run:
        for r in rows:
            repo.save_name(r["name"], {**r["before"], "review": True})
            with open(FLAG_LOG, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps({**r, "at": datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False) + "\n")
    return rows


# ---- terminal ----


def paint(text: str, style: str, color: bool) -> str:
    return f"{ANSI[style]}{text}{ANSI['off']}" if color else text


def show(item: Item, pos: str, english: str, shown: int, tcv: bool, color: bool) -> list[str]:
    """Print the name and its verses; return the numbered label suggestions."""
    cands, suggestions = suggest(item)
    few = len(item.verses) <= 3
    style = review.tamil_style({item.entry["label"], *item.entry["forms"]}, cands[0].prefix if cands else None)

    out = sys.stdout
    out.write("\n" + "─" * 72 + "\n")
    out.write(f"{pos}  {paint(item.name, 'en', color)}  ·  {len(item.verses)} verses  ·  now: {item.entry['label']} ({state_of(item.entry)}, confidence {item.entry.get('confidence', 1.0):.2f})\n")
    for b in review.name_briefs().get(item.name, [])[:4]:
        out.write(f"  {paint(b, 'dim', color)}\n")
    from . import ai_names

    if ai := ai_names.notes().get(item.name):
        where = "found in the IRV" if ai["source"] == "irv" else "composed"
        extra = f" · {ai['note']}" if ai["note"] else ""
        out.write(f"  Claude: {ai['label']} ({where}, {ai['confidence']}){extra}\n")
    for vid in item.verses[:shown]:
        out.write(f"{vid}\n")
        out.write(f"  EN  {review.mark_english(repo.verse_text(vid, english) or '(no text)', [item.name], color)}\n")
        for version, tag in [(repo.TAMIL_VERSION, "TA "), *([("TCV", "TCV")] if tcv else [])]:
            for label, t in review.tamil_rows(vid, version, style, few):
                out.write(f"  {tag} {'(' + label + ') ' if label else ''}{review.mark_tamil(t, style, color)}\n")
    if len(item.verses) > shown:
        out.write(paint(f"  … {len(item.verses) - shown} more verses (m)\n", "dim", color))
    out.write("Suggestions:\n")
    for k, s in enumerate(suggestions, 1):
        seen = ", ".join(f"{w}×{n}" for w, n in s.words[:4])
        where = "Claude" if s.ai else f"{s.covered}/{len(item.verses)} verses"
        out.write(f"  {paint(str(k), 'cand', color)}  {s.label:<18} {where} · sounds {s.sounds:.2f} · {seen}\n")
    return [s.label for s in suggestions]


HELP = "Enter/1-5 accept · c keep current · e type a name · r reject · s skip · m more · t TCV · u undo · q quit"


def run(order: str = "verses", start: str | None = None, include_rejected: bool = False, everything: bool = False,
        english: str = "KJV", shown: int = 4, color: bool | None = None, read=input, below: float | None = None,
        only: set[str] | None = None) -> dict:
    """The terminal review loop. `read` is the prompt function (tests pass their own)."""
    if color is None:
        color = sys.stdout.isatty()
    s = Session(queue(order, start, include_rejected, everything, below, only))
    tcv = False
    extra = 0
    print(f"{len(s.items)} names to review ({'most verses first' if order == 'verses' else 'A–Z'}). {HELP}")
    while (item := s.current) is not None:
        suggestions = show(item, f"[{s.i + 1}/{len(s.items)}]", english, shown + extra, tcv, color)
        try:
            answer = read(f"{HELP}\n> ").strip()
        except EOFError:
            break
        cmd = answer.lower()
        if cmd == "q":
            break
        if cmd == "m":
            extra += 10
            continue
        if cmd == "t":
            tcv = not tcv
            continue
        extra = 0
        if cmd == "u":
            if s.undo() is None:
                print("nothing to undo")
            continue
        if cmd == "s":
            s.skip()
            continue
        try:
            if cmd == "r":
                s.reject()
                continue
            forms = None
            if cmd == "c":
                after = s.keep()
            else:
                if cmd == "e":
                    label = read("Tamil name (base form): ").strip()
                    typed = read("Forms, comma-separated (Enter: find them in the verses): ").strip()
                    forms = [f.strip() for f in typed.split(",") if f.strip()] or None
                elif cmd == "" and suggestions:
                    label = suggestions[0]
                elif cmd.isdigit() and 1 <= int(cmd) <= len(suggestions):
                    label = suggestions[int(cmd) - 1]
                elif review.TAMIL_NAME.fullmatch(" ".join(answer.split())):
                    label = answer  # typed the Tamil name straight away
                else:
                    print(f"? {answer!r}")
                    continue
                after = s.accept(label, forms)
            print(paint(f"✓ {item.name} = {after['label']}  ({', '.join(after['forms'][:6])})", "known", color))
        except ValueError as err:
            print(f"not saved: {err}")

    print("\n" + s.summary())
    if s.counts["accepted"]:
        print("Run `pnpm content` to check the accepted forms against the text.")
    return dict(s.counts)
