#!/usr/bin/env python3
"""Download one published commentary version for pack-build (app commentary packs).

    fetch-commentary.py <version> <out-dir> [--skip ecf] [--base URL]

Writes <out-dir>/index.json and <out-dir>/{source}/{BOOK}/{chapter|intro}.json, the
layout the bible-commentaries repository publishes. Files are immutable per version,
so the deploy workflow only calls this when the version changes.
"""
import argparse
import json
import pathlib
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def get(url: str) -> bytes:
    for attempt in range(4):
        try:
            # Cloudflare turns away Python's default user agent.
            req = urllib.request.Request(url, headers={"User-Agent": "tamilscripture-pack-build"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:
            if attempt == 3:
                raise
    raise AssertionError


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    ap.add_argument("out")
    ap.add_argument("--skip", default="ecf")
    ap.add_argument("--base", default="https://stream.tamilaudiobible.com/commentary")
    a = ap.parse_args()
    base = f"{a.base.rstrip('/')}/{a.version}"
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    index_bytes = get(f"{base}/index.json")
    (out / "index.json").write_bytes(index_bytes)
    index = json.loads(index_bytes)
    skip = {s for s in a.skip.split(",") if s}
    jobs = [
        (src, book, ch)
        for src, books in index["chapters"].items()
        if src not in skip
        for book, chapters in books.items()
        for ch in chapters
    ]

    def fetch(job):
        src, book, ch = job
        name = "intro" if ch == 0 else str(ch)
        path = out / src / book / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(get(f"{base}/{src}/{book}/{name}.json"))

    with ThreadPoolExecutor(32) as pool:
        list(pool.map(fetch, jobs))
    print(f"commentary {a.version}: {len(jobs)} files", file=sys.stderr)


if __name__ == "__main__":
    main()
