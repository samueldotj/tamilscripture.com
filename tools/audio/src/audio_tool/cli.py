"""Command line: audio <command> --version CODE --recording ID [options].

    init     write data/audio/{VERSION}/{recording}/recording.toml
    ingest   unzip, map files to chapters, encode, write chapters.tsv
    align    find where each verse starts (needs the align extra and a GPU)
    upload   send the MP3s (and source zips) to R2; never overwrites
    verify   check every chapter through the public domain
    status   per-book progress

See docs/feature_audio_tool.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import encode, ingest, publish, repo
from .sources import Matcher, scan


def cmd_init(a) -> int:
    books = repo.load_books()
    ver = repo.load_version(a.version)
    path = repo.rec_dir(a.version, a.recording) / "recording.toml"
    if path.exists() and not a.force:
        raise SystemExit(f"{path} exists; pass --force to replace it")
    sources, filesets = [], set()
    for z in a.zip:
        print(f"hashing {z}…", flush=True)
        sources.append({"name": Path(z).name, "sha256": encode.sha256_file(Path(z))})
    if a.zip and a.preset != "custom":
        filesets = scan(a.zip, Matcher({"preset": a.preset}, books)).fileset
    v = repo.toml_value
    lines = [
        "# One recording of a version, for tools/audio and usfm-ingest (docs/feature_audio_tool.md §3).",
        f"# Text: {ver.get('attribution', '')}",
        f"version     = {v(a.version)}",
        f"recording   = {v(a.recording)}",
        f"fileset     = {v(sorted(filesets))}",
        f"narrator    = {v(a.narrator)}",
        f"publisher   = {v(a.publisher)}",
        f"licence     = {v(a.licence)}",
        f"attribution = {v(a.attribution)}",
        f"source_url  = {v(a.source_url)}",
        "sources     = [" + "".join(f"\n  {v(s)}," for s in sources) + ("\n]" if sources else "]"),
        "",
        f"drama       = {v(a.drama)}  # several voices with music under them (FCBH 2DA)",
        "",
        "[source]",
        f"preset = {v(a.preset)}",
    ]
    if a.preset == "custom":
        lines += ["pattern  = '(?P<book>\\d{2})_(?P<chapter>\\d{3})\\.mp3$'", 'book_key = "number"']
    lines += ["", "[encode]", "bitrate_kbps = 64", "sample_rate  = 44100", "loudness     = -16.0", "true_peak    = -3.0", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    audio_toml = repo.DATA_AUDIO / "audio.toml"
    if not audio_toml.exists():
        audio_toml.write_text(
            "# Where the MP3s are served from; usfm-ingest joins it with each object key.\n"
            f"base = {v(repo.DEFAULT_BASE)}\n",
            encoding="utf-8", newline="\n",
        )
    print(f"wrote {path.relative_to(repo.ROOT)}")
    return 0


def cmd_status(a) -> int:
    books = repo.load_books()
    rows = {(r.book, r.chapter): r for r in repo.read_chapters(a.version, a.recording)}
    state = repo.State(a.version, a.recording)
    tot = [0, 0, 0, 0, 0, 0, 0]
    print("book  chapters  encoded  in tsv  uploaded  verified  timed  low")
    for b in books:
        n = [b.chapters, 0, 0, 0, 0, 0, 0]
        timings = repo.read_timings(a.version, a.recording, b.code)
        n[5] = len({t.chapter for t in timings})
        n[6] = sum(t.flag == "low" for t in timings)
        for c in range(1, b.chapters + 1):
            e = state.data["chapters"].get(f"{b.code}.{c}", {})
            r = rows.get((b.code, c))
            n[1] += "sha256" in e
            n[2] += r is not None
            n[3] += bool(r and e.get("uploaded") == r.sha256)
            n[4] += bool(r and e.get("verified") == r.sha256)
        tot = [x + y for x, y in zip(tot, n)]
        if a.all or any(n[1:]):
            print(f"{b.code:4}  {n[0]:8}  {n[1]:7}  {n[2]:6}  {n[3]:8}  {n[4]:8}  {n[5]:5}  {n[6]:3}")
    print(f"{'all':4}  {tot[0]:8}  {tot[1]:7}  {tot[2]:6}  {tot[3]:8}  {tot[4]:8}  {tot[5]:5}  {tot[6]:3}")
    return 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="audio", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name: str, help: str):
        sp = sub.add_parser(name, help=help)
        sp.add_argument("--version", required=True, type=str.upper, help="version code, e.g. BSB")
        sp.add_argument("--recording", default="r1", help="recording id (default r1)")
        return sp

    sp = add("init", "write recording.toml")
    sp.add_argument("--preset", choices=["fcbh", "dbp", "custom"], required=True)
    sp.add_argument("--zip", action="append", default=[], help="source zip (repeat for OT and NT)")
    sp.add_argument("--narrator", default="")
    sp.add_argument("--publisher", default="")
    sp.add_argument("--licence", default="")
    sp.add_argument("--attribution", default="")
    sp.add_argument("--source-url", default="")
    sp.add_argument("--drama", action="store_true", help="several voices with music (FCBH 2DA)")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=cmd_init)

    sp = add("ingest", "unzip, map, encode, write chapters.tsv")
    sp.add_argument("--zip", action="append", default=[], help="source zip (repeat); remembered for re-runs")
    sp.add_argument("--dry-run", action="store_true", help="only show how files map to chapters")
    sp.add_argument("--allow-gaps", action="store_true", help="accept books with some chapters missing")
    sp.add_argument("--jobs", type=int, default=ingest.default_jobs())
    sp.set_defaults(fn=lambda a: ingest.run(a.version, a.recording, a.zip, a.dry_run, a.allow_gaps, a.jobs))

    sp = add("align", "find where each verse starts")
    sp.add_argument("--book", type=str.upper, help="only this book (USFM code)")
    sp.add_argument("--chapter", type=int, help="only this chapter (with --book)")
    sp.add_argument("--probe", action="store_true", help="only probe: which text, headings read or not")
    sp.add_argument("--force", action="store_true", help="redo chapters already aligned, and replace edited rows")
    sp.add_argument("--accept", action="store_true", help="go on even if the probe says the recording reads another text")

    def run_align(a):
        from . import align  # PyTorch loads only for this command
        return align.run(a.version, a.recording, a.book, a.chapter, a.force, a.probe, a.accept)
    sp.set_defaults(fn=run_align)

    sp = add("upload", "send MP3s and source zips to R2")
    sp.add_argument("--dry-run", action="store_true", help="check what would be sent, send nothing")
    sp.add_argument("--no-masters", action="store_true", help="skip the source zips")
    sp.add_argument("--jobs", type=int, default=8)
    sp.set_defaults(fn=lambda a: publish.upload(a.version, a.recording, a.dry_run, a.jobs, not a.no_masters))

    sp = add("verify", "check every chapter through the public domain")
    sp.add_argument("--jobs", type=int, default=16)
    sp.set_defaults(fn=lambda a: publish.verify(a.version, a.recording, a.jobs))

    sp = add("status", "per-book progress")
    sp.add_argument("--all", action="store_true", help="list books with nothing done too")
    sp.set_defaults(fn=cmd_status)

    a = p.parse_args(argv)
    return a.fn(a)
