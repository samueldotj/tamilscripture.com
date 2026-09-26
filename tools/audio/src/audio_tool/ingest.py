"""`audio ingest`: zips -> mapped chapters -> encoded MP3s -> chapters.tsv."""

from __future__ import annotations

import os
import sys
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath

from . import encode, repo
from .sources import Matcher, Mapping, Member, scan


def _fmt_ms(ms: int) -> str:
    s = ms // 1000
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def report_mapping(m: Mapping, books: list[repo.Book], rec: dict) -> list[str]:
    """Print what was found; return the problems that stop an ingest."""
    whole, partial = m.missing(books)
    print(f"mapped {len(m.chapters)} chapter files", end="")
    print(f" (filesets {', '.join(sorted(m.fileset))})" if m.fileset else "")
    want = {f.upper() for f in rec.get("fileset", [])}
    if want and m.fileset and m.fileset != want:
        print(f"  note: recording.toml lists filesets {sorted(want)}, the files carry {sorted(m.fileset)}")
    if whole:
        print(f"  books with no audio ({len(whole)}): {' '.join(whole)}")
    for label, items in (("skipped (not audio)", m.skipped), ("chapter 0 / introductions, ignored", m.intros)):
        if items:
            print(f"  {label}: {len(items)}")
    problems = []
    for label, items in (("unmatched", m.unmatched), ("duplicates", m.duplicates), ("impossible", m.bad)):
        if items:
            problems.append(f"{label}: {len(items)}")
            print(f"  {label} ({len(items)}):")
            for x in items[:15]:
                print(f"    {x}")
            if len(items) > 15:
                print(f"    … and {len(items) - 15} more")
    if partial:
        problems.append(f"{len(partial)} books with missing chapters")
        print("  books with missing chapters:")
        for code, chs in partial.items():
            print(f"    {code}: {', '.join(map(str, chs[:20]))}{' …' if len(chs) > 20 else ''}")
    return problems


def print_table(m: Mapping, books: list[repo.Book]) -> None:
    print("\nbook  chapters  files  first file")
    for b in books:
        have = [(c, m.chapters[(b.code, c)]) for c in range(1, b.chapters + 1) if (b.code, c) in m.chapters]
        first = PurePosixPath(have[0][1].name).name if have else "-"
        print(f"{b.code:4}  {b.chapters:8}  {len(have):5}  {first}")


def extract(members: list[Member], dest: Path) -> dict[str, Path]:
    """Extract members that aren't already there at the right size; return their paths."""
    out: dict[str, Path] = {}
    by_zip: dict[str, list[Member]] = {}
    for mem in members:
        by_zip.setdefault(mem.zip, []).append(mem)
    for z, mems in by_zip.items():
        base = dest / Path(z).stem
        with zipfile.ZipFile(z) as zf:
            for mem in mems:
                target = base / PurePosixPath(mem.name)
                out[f"{z}:{mem.name}"] = target
                if target.exists() and target.stat().st_size == mem.size:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp = target.with_name(target.name + ".part")
                with zf.open(mem.name) as src, open(tmp, "wb") as dst:
                    while chunk := src.read(1 << 20):
                        dst.write(chunk)
                tmp.replace(target)
    return out


def run(version: str, recording: str, zips: list[str], dry_run: bool, allow_gaps: bool, jobs: int) -> int:
    books = repo.load_books()
    ver = repo.load_version(version)
    rec = repo.load_recording(version, recording)
    state = repo.State(version, recording)
    if not zips:
        zips = [z["path"] for z in state.data["zips"].values()]
    if not zips:
        raise SystemExit("no --zip given and none remembered from an earlier ingest")
    for z in zips:
        if not Path(z).is_file():
            raise SystemExit(f"{z} is not a file")

    matcher = Matcher(rec.get("source", {}), books)
    m = scan(zips, matcher)
    problems = report_mapping(m, books, rec)
    blocking = [p for p in problems if not (allow_gaps and "missing" in p)]
    if dry_run:
        print_table(m, books)
        return 1 if blocking else 0
    if blocking:
        print(f"\nstopped: {'; '.join(blocking)}. Fix recording.toml [source], or use --allow-gaps for missing chapters.")
        return 1

    encode.require_ffmpeg()
    work = repo.work_dir(version, recording)
    for z in zips:
        state.data["zips"][Path(z).name] = {"path": str(Path(z).resolve()), "size": Path(z).stat().st_size}
    print("extracting…", flush=True)
    paths = extract(list(m.chapters.values()) + m.extras, work / "source")
    state.save()

    s = encode.settings(rec.get("encode", {}))
    lang = ver.get("lang", "en")
    names = {b.code: (b.name_ta if lang == "ta" else b.name_en) for b in books}
    order = {b.code: b.order for b in books}
    todo = []
    for (code, ch), mem in sorted(m.chapters.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        entry = state.chapter(code, ch)
        ident = f"{Path(mem.zip).name}:{mem.name}:{mem.size}:{mem.crc:08x}"
        dst = work / "mp3" / code / f"{code}_{ch:03d}.mp3"
        if entry.get("source") == ident and entry.get("settings") == s and "sha256" in entry and dst.exists():
            continue
        todo.append((code, ch, ident, paths[f"{mem.zip}:{mem.name}"], dst))

    print(f"encoding {len(todo)} of {len(m.chapters)} chapters with {jobs} workers", flush=True)
    lock = threading.Lock()
    done = 0
    failed: list[str] = []
    start = time.monotonic()

    def one(code, ch, ident, src, dst):
        tags = {
            "title": f"{names[code]} {ch}",
            "artist": rec.get("narrator") or rec.get("publisher", ""),
            "album": ver.get("name", version),
            "track": str(ch),
            "comment": rec.get("attribution", ""),
        }
        encode.encode(src, dst, s, tags)
        return code, ch, ident, encode.probe(dst)

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [pool.submit(one, *t) for t in todo]
        for fut in as_completed(futures):
            try:
                code, ch, ident, (ms, size, sha) = fut.result()
            except Exception as e:  # keep going; report at the end
                failed.append(str(e))
                continue
            with lock:
                entry = state.chapter(code, ch)
                entry.clear()
                entry.update(source=ident, settings=s, ms=ms, bytes=size, sha256=sha)
                done += 1
                if done % 25 == 0 or done == len(todo):
                    state.save()
                    rate = (time.monotonic() - start) / done
                    left = rate * (len(todo) - done)
                    print(f"  {done}/{len(todo)}  last {code} {ch} ({_fmt_ms(ms)})  ~{_fmt_ms(int(left * 1000))} left", flush=True)
    state.save()

    rows = []
    for (code, ch) in m.chapters:
        e = state.chapter(code, ch)
        if "sha256" in e:
            rows.append(repo.ChapterRow(code, ch, e["ms"], e["bytes"], e["sha256"]))
    path = repo.write_chapters(version, recording, rows, books)
    total = sum(r.ms for r in rows)
    size = sum(r.bytes for r in rows)
    print(f"\nwrote {path.relative_to(repo.ROOT)}: {len(rows)} chapters, {_fmt_ms(total)}, {size / 1e9:.2f} GB")
    if failed:
        print(f"{len(failed)} chapters failed to encode:", file=sys.stderr)
        for f in failed[:10]:
            print(f"  {f}", file=sys.stderr)
        return 1
    return 0


def default_jobs() -> int:
    return max(1, (os.cpu_count() or 2) - 1)
