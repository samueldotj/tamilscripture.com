"""`audio align`: verse start times by forced alignment (docs/feature_audio_tool.md §5).

Meta's MMS aligner (torchaudio.pipelines.MMS_FA, CC BY-NC 4.0 weights, accepted
for this non-commercial site) places each known word of the chapter in the
recording; verse starts fall in the pause before each verse's first word.
Needs the `[align]` extra: PyTorch with CUDA, torchaudio, uroman, num2words.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from . import repo, text

SR = 16000
LANG3 = {"ta": "tam", "en": "eng"}
# Probe chapters, spread across the canon; those a recording lacks are skipped.
PROBE = [("GEN", 1), ("EXO", 20), ("RUT", 1), ("PSA", 23), ("PSA", 119), ("ISA", 53), ("JER", 31),
         ("MAT", 5), ("MRK", 4), ("LUK", 15), ("JHN", 3), ("ACT", 2), ("ROM", 8), ("REV", 21)]
LOW = 0.45  # a verse under this mean word score is flagged
MISMATCH = 0.80  # a chapter under this mean word score gets no timings
TEXT_MIN = 0.85  # the probe's best text must reach this
HEADINGS_READ = 0.60  # mid-chapter heading words scoring this are being read
# Bump when the transcript or the boundary rule changes in a way that should redo every chapter.
ALIGN_VERSION = 2  # 2: number words left out of scores


class Model:
    """The acoustic model, tokenizer and aligner, loaded once."""

    def __init__(self):
        try:
            import torch
            import torchaudio
            import uroman
        except ImportError as e:
            raise SystemExit(f"{e.name} is missing: install the align extra (tools/audio/README.md)")
        self.torch = torch
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        bundle = torchaudio.pipelines.MMS_FA
        self.model = bundle.get_model(with_star=True).to(self.dev).eval()
        self.tok = bundle.get_tokenizer()
        self.aligner = bundle.get_aligner()
        self.vocab = set(bundle.get_dict(star=None)) - {"-"}
        self.uroman = uroman.Uroman()
        self.name = f"torchaudio MMS_FA (torch {torch.__version__}, torchaudio {torchaudio.__version__}, {self.dev})"
        self._rom: dict[tuple[str, str], str] = {}

    def romanizer(self, lang3: str):
        def rom(word: str) -> str:
            key = (word, lang3)
            if key not in self._rom:
                self._rom[key] = self.uroman.romanize_string(word, lcode=lang3)
            return self._rom[key]
        return rom

    def emission(self, samples):
        """Frame log-probabilities in 30 s windows with 2 s of context either side."""
        torch = self.torch
        wave = torch.from_numpy(samples)
        win, ctx = 30 * SR, 2 * SR
        parts = []
        with torch.inference_mode():
            for start in range(0, len(wave), win):
                a, b = max(0, start - ctx), min(len(wave), start + win + ctx)
                em, _ = self.model(wave[a:b].unsqueeze(0).to(self.dev))
                em = em[0]
                fps = em.shape[0] / ((b - a) / SR)
                lo = round((start - a) / SR * fps)
                hi = lo + round((min(start + win, len(wave)) - start) / SR * fps)
                parts.append(em[lo:hi])
        em = torch.cat(parts)
        return em, (len(wave) / SR) / em.shape[0]

    def align(self, em, words: list[str], spf: float) -> list[tuple[float, float, float]]:
        """(start s, end s, score) for each word, between wildcards at both ends."""
        if not words:
            return []
        spans = self.aligner(em, self.tok(["*"] + words + ["*"]))[1:-1]
        out = []
        for sp in spans:
            n = sum(len(x) for x in sp)
            out.append((sp[0].start * spf, sp[-1].end * spf, float(sum(x.score * len(x) for x in sp) / n)))
        return out


def decode(path: Path):
    import numpy as np

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


@dataclass
class ChapterResult:
    rows: list[repo.TimingRow]
    mean: float  # mean score of verse words
    heading_mean: float | None  # mean score of mid-chapter heading words, when headings were included
    first_word: float | None  # seconds to verse 1's first word
    words: list[dict] = field(default_factory=list)

    @property
    def low(self) -> int:
        return sum(r.flag == "low" for r in self.rows)


def align_chapter(m: Model, em, spf: float, duration: float, chapter: dict, lang3: str, headings: bool, drama: bool) -> ChapterResult:
    t = text.transcript(chapter, lang3, m.romanizer(lang3), m.vocab, headings)
    spans = m.align(em, [w.text for w in t.words], spf)
    first: dict[int, float] = {}
    last: dict[int, float] = {}
    scores: dict[int, list[float]] = {}
    chars: dict[int, int] = {}
    words = []
    heading_scores = []
    number_scores: dict[int, list[float]] = {}
    for w, (s, e, sc) in zip(t.words, spans):
        words.append({"w": w.text, "v": w.verse, "s": round(s, 3), "e": round(e, 3), "sc": round(sc, 3)})
        if w.heading:
            if w.mid:
                heading_scores.append(sc)
            continue
        first.setdefault(w.verse, s)
        last[w.verse] = e
        chars[w.verse] = chars.get(w.verse, 0) + len(w.text)
        if not w.number:
            scores.setdefault(w.verse, []).append(sc)
        else:
            number_scores.setdefault(w.verse, []).append(sc)
    # A verse of nothing but numbers is scored on them after all.
    for n, v in number_scores.items():
        scores.setdefault(n, v)
    se = text.verse_starts(first, last, t.verses, duration)
    verse_scores = [sc for v in scores.values() for sc in v]
    mean = statistics.fmean(verse_scores) if verse_scores else 0.0
    low = LOW - (0.1 if drama else 0.0)
    lo_rate, hi_rate = (0.33, 3.0) if drama else (0.4, 2.5)
    rates = {n: chars[n] / max(0.05, se[n][1] - se[n][0]) for n in se if n in chars}
    median_rate = statistics.median(rates.values()) if rates else 0
    rows = []
    for n in t.verses:
        if n not in se:
            continue
        start, end = se[n]
        sc = statistics.fmean(scores[n]) if n in scores else 0.0
        flag = "bridge" if n in t.bridges else ""
        rate_ok = n not in rates or not median_rate or lo_rate * median_rate <= rates[n] <= hi_rate * median_rate
        if n not in scores or sc < low or not rate_ok:
            flag = "low"
        rows.append(repo.TimingRow(chapter["chapter"], n, round(start * 1000), round(end * 1000), sc, flag))
    for a, b in zip(rows, rows[1:]):
        if b.start_ms < a.start_ms:
            raise RuntimeError(f"{chapter['book']} {chapter['chapter']}: verse {b.verse} starts before verse {a.verse}")
    return ChapterResult(rows, mean, statistics.fmean(heading_scores) if heading_scores else None,
                         first.get(t.verses[0]) if t.verses else None, words)


def text_hash(chapter: dict) -> str:
    return hashlib.sha256(json.dumps(chapter["blocks"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def prefetch(paths: list[Path], workers: int = 3):
    """Decode the next few chapters on CPU threads while the GPU aligns the current one."""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        queue: deque = deque()
        it = iter(paths)
        for p in it:
            queue.append(pool.submit(decode, p))
            if len(queue) >= workers + 1:
                break
        while queue:
            yield queue.popleft().result()
            nxt = next(it, None)
            if nxt is not None:
                queue.append(pool.submit(decode, nxt))


def _version_meta(manifest: dict, version: str) -> dict:
    for v in manifest["versions"]:
        if v["code"] == version:
            return v
    raise SystemExit(f"{version} is not in the built content; run `pnpm content`")


def probe(m: Model, version: str, recording: str, rec: dict, manifest: dict) -> dict:
    """Which text the recording reads, and whether it reads headings."""
    build = manifest["build"]
    lang = _version_meta(manifest, version)["lang"]
    lang3 = LANG3.get(lang, lang)
    have = {(r.book, r.chapter) for r in repo.read_chapters(version, recording)}
    chapters = [bc for bc in PROBE if bc in have]
    if not chapters:
        raise SystemExit("none of the probe chapters is encoded; run `audio ingest` first")
    texts = [v["code"] for v in manifest["versions"] if v["lang"] == lang]
    work = repo.work_dir(version, recording)
    scores: dict[str, list[float]] = {v: [] for v in texts}
    heading_scores: list[float] = []
    openings: list[float] = []
    print(f"probing {len(chapters)} chapters against {', '.join(texts)}", flush=True)
    paths = [work / "mp3" / b / f"{b}_{c:03d}.mp3" for b, c in chapters]
    for (b, c), samples in zip(chapters, prefetch(paths)):
        em, spf = m.emission(samples)
        dur = len(samples) / SR
        line = f"  {b} {c:>3}"
        for v in texts:
            try:
                ch = repo.load_chapter_json(build, v, b, c)
            except FileNotFoundError:
                continue
            res = align_chapter(m, em, spf, dur, ch, lang3, headings=(v == version), drama=bool(rec.get("drama")))
            scores[v].append(res.mean)
            line += f"  {v} {res.mean:.3f}"
            if v == version:
                if res.heading_mean is not None:
                    heading_scores.append(res.heading_mean)
                if res.first_word is not None:
                    openings.append(res.first_word)
        print(line, flush=True)
    means = {v: statistics.fmean(s) for v, s in scores.items() if s}
    ranked = sorted(means, key=means.get, reverse=True)
    best = ranked[0]
    values = {
        "reads_text": best,
        "text_score": round(means[best], 3),
        "other_texts": {v: round(means[v], 3) for v in ranked[1:]},
        "reads_headings": bool(heading_scores) and statistics.fmean(heading_scores) >= HEADINGS_READ,
        "heading_score": round(statistics.fmean(heading_scores), 3) if heading_scores else -1.0,
        "opening_s": round(statistics.median(openings), 1) if openings else 0.0,
        "probe_chapters": len(chapters),
        "model": m.name,
    }
    repo.set_align_section(version, recording, values)
    print(f"reads {best} ({means[best]:.3f})" + "".join(f", {v} {means[v]:.3f}" for v in ranked[1:])
          + f"; headings {'read' if values['reads_headings'] else 'not read'} ({values['heading_score']}); opening {values['opening_s']} s")
    return values


def run(version: str, recording: str, book: str | None, chapter: int | None, force: bool, probe_only: bool, accept: bool) -> int:
    rec = repo.load_recording(version, recording)
    manifest = repo.content_manifest()
    build = manifest["build"]
    lang = _version_meta(manifest, version)["lang"]
    lang3 = LANG3.get(lang, lang)
    books = {b.code: b for b in repo.load_books()}
    m = Model()
    print(f"model: {m.name}", flush=True)

    cfg = rec.get("align", {})
    if probe_only or "reads_text" not in cfg:
        cfg = probe(m, version, recording, rec, manifest)
        if probe_only:
            return 0
    if cfg["reads_text"] != version and not accept:
        print(f"stopped: this recording reads {cfg['reads_text']} ({cfg['text_score']}), not {version}. "
              f"Pass --accept to align it against {version} anyway.", file=sys.stderr)
        return 1
    if cfg["text_score"] < TEXT_MIN and not accept:
        print(f"stopped: the best text match is only {cfg['text_score']} (need {TEXT_MIN}); pass --accept to go on", file=sys.stderr)
        return 1
    headings = bool(cfg.get("reads_headings"))

    work = repo.work_dir(version, recording)
    state = repo.State(version, recording)
    todo = []
    for r in repo.read_chapters(version, recording):
        if (book and r.book != book) or (chapter and r.chapter != chapter):
            continue
        ch = repo.load_chapter_json(build, version, r.book, r.chapter)
        key = {"sha256": r.sha256, "text": text_hash(ch), "headings": headings, "v": ALIGN_VERSION}
        done = state.chapter(r.book, r.chapter).get("align", {})
        if not force and {k: done.get(k) for k in key} == key:
            continue
        todo.append((r, ch, key))
    print(f"aligning {len(todo)} chapters (headings {'in' if headings else 'out'})", flush=True)

    per_book: dict[str, dict[int, list[repo.TimingRow]]] = {}
    results = []
    t0 = time.monotonic()
    paths = [work / "mp3" / r.book / f"{r.book}_{r.chapter:03d}.mp3" for r, _, _ in todo]
    for i, ((r, ch, key), samples) in enumerate(zip(todo, prefetch(paths)), 1):
        em, spf = m.emission(samples)
        res = align_chapter(m, em, spf, len(samples) / SR, ch, lang3, headings, bool(rec.get("drama")))
        mismatch = res.mean < MISMATCH
        per_book.setdefault(r.book, {})[r.chapter] = [] if mismatch else res.rows
        (work / "align").mkdir(parents=True, exist_ok=True)
        (work / "align" / f"{r.book}_{r.chapter:03d}.json").write_text(json.dumps({"mean": res.mean, "words": res.words}, ensure_ascii=False), encoding="utf-8")
        state.chapter(r.book, r.chapter)["align"] = {**key, "mean": round(res.mean, 4), "low": res.low, "mismatch": mismatch}
        results.append((r.book, r.chapter, res, mismatch))
        if i % 25 == 0 or i == len(todo):
            state.save()
            rate = (time.monotonic() - t0) / i
            print(f"  {i}/{len(todo)}  {r.book} {r.chapter}  mean {res.mean:.3f}  ~{int(rate * (len(todo) - i))} s left", flush=True)

    for b, chapters in per_book.items():
        rows = repo.read_timings(version, recording, b)
        for c, new in chapters.items():
            rows = repo.merge_timings(rows, c, new, force)
        repo.write_timings(version, recording, b, rows)
    state.save()
    return report(version, recording, results, books, time.monotonic() - t0)


def report(version: str, recording: str, results, books, seconds: float) -> int:
    if not results:
        print("nothing to align")
        return 0
    order = {c: b.order for c, b in books.items()}
    lines = [f"# Alignment report: {version} {recording}", "", f"{len(results)} chapters in {seconds:.0f} s", "",
             "| Book | Chapters | Mean score | Low verses | Mismatch |", "|---|---|---|---|---|"]
    by_book: dict[str, list] = {}
    for b, c, res, mm in results:
        by_book.setdefault(b, []).append((c, res, mm))
    for b in sorted(by_book, key=order.get):
        items = by_book[b]
        mean = statistics.fmean(res.mean for _, res, _ in items)
        lines.append(f"| {b} | {len(items)} | {mean:.3f} | {sum(res.low for _, res, _ in items)} | {', '.join(str(c) for c, _, mm in items if mm) or '—'} |")
    verses = [(row.score, b, c, row.verse) for b, c, res, mm in results if not mm for row in res.rows]
    lines += ["", "Lowest-scoring verses:", ""] + [f"- {b} {c}:{v} — {s:.3f}" for s, b, c, v in sorted(verses)[:20]]
    path = repo.work_dir(version, recording) / "report-align.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    mism = [(b, c) for b, c, _, mm in results if mm]
    low = sum(res.low for _, _, res, mm in results if not mm)
    print(f"\n{len(results)} chapters, mean {statistics.fmean(r.mean for _, _, r, _ in results):.3f}, "
          f"{low} low verses, {len(mism)} mismatched chapters{': ' + ', '.join(f'{b} {c}' for b, c in mism[:10]) if mism else ''}")
    print(f"report: {path}")
    return 0
