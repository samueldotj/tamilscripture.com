"""`audio upload` and `audio verify`: R2 through its S3 API, then the public domain.

The R2 key is read from the environment, or from `.env.audio` at the repository
root (git-ignored by `.env*`), never from committed files:

    R2_ACCOUNT_ID=…
    R2_ACCESS_KEY_ID=…
    R2_SECRET_ACCESS_KEY=…
    # optional: R2_BUCKET=ts-audio  R2_MASTERS_BUCKET=ts-audio-masters
"""

from __future__ import annotations

import os
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import repo

CACHE_CONTROL = "public, max-age=31536000, immutable"
USER_AGENT = "tamilscripture-audio-tool/0.1"


def _env() -> dict[str, str]:
    env = {}
    dotenv = repo.ROOT / ".env.audio"
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if k.startswith("R2_")})
    missing = [k for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY") if not env.get(k)]
    if missing:
        raise SystemExit(f"set {', '.join(missing)} in the environment or in .env.audio at the repository root")
    return env


def _client(env: dict[str, str]):
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        raise SystemExit("boto3 is not installed; install the tool with its dependencies (see tools/audio/README.md)")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=env["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(retries={"max_attempts": 5, "mode": "standard"}, max_pool_connections=16),
    )


def _head(s3, bucket: str, key: str) -> dict | None:
    from botocore.exceptions import ClientError

    try:
        return s3.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def upload(version: str, recording: str, dry_run: bool, jobs: int, masters: bool) -> int:
    rows = repo.read_chapters(version, recording)
    if not rows:
        raise SystemExit("chapters.tsv is empty; run `audio ingest` first")
    env = _env()
    bucket = env.get("R2_BUCKET", "ts-audio")
    s3 = _client(env)
    state = repo.State(version, recording)
    work = repo.work_dir(version, recording)

    lock = threading.Lock()
    counts = {"uploaded": 0, "skipped": 0}
    conflicts: list[str] = []
    errors: list[str] = []

    def one(r: repo.ChapterRow):
        key = repo.object_key(version, recording, r.book, r.chapter)
        path = work / "mp3" / r.book / f"{r.book}_{r.chapter:03d}.mp3"
        if not path.exists() or path.stat().st_size != r.bytes:
            return "error", f"{key}: local file missing or not the size in chapters.tsv; re-run ingest"
        head = _head(s3, bucket, key)
        if head is not None:
            if head.get("Metadata", {}).get("sha256") == r.sha256:
                return "skipped", key
            return "conflict", f"{key}: already in {bucket} with different content; use a new recording id"
        if dry_run:
            return "uploaded", key
        with open(path, "rb") as f:
            s3.put_object(
                Bucket=bucket, Key=key, Body=f, ContentLength=r.bytes,
                ContentType="audio/mpeg", CacheControl=CACHE_CONTROL, Metadata={"sha256": r.sha256},
            )
        return "uploaded", key

    print(f"{'checking' if dry_run else 'uploading'} {len(rows)} chapters to {bucket}", flush=True)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(one, r): r for r in rows}
        for i, fut in enumerate(as_completed(futures), 1):
            r = futures[fut]
            try:
                kind, msg = fut.result()
            except Exception as e:
                kind, msg = "error", f"{r.book} {r.chapter}: {e}"
            with lock:
                if kind == "conflict":
                    conflicts.append(msg)
                elif kind == "error":
                    errors.append(msg)
                else:
                    counts[kind] += 1
                    if not dry_run:
                        state.chapter(r.book, r.chapter)["uploaded"] = r.sha256
                if i % 50 == 0 or i == len(rows):
                    print(f"  {i}/{len(rows)}  uploaded {counts['uploaded']}  already there {counts['skipped']}", flush=True)
                    if not dry_run:
                        state.save()
    if not dry_run:
        state.save()

    if masters and not conflicts and not errors:
        mbucket = env.get("R2_MASTERS_BUCKET", "ts-audio-masters")
        for name, z in state.data["zips"].items():
            key = f"{version}/{recording}/source/{name}"
            head = _head(s3, mbucket, key)
            if head is not None and head.get("ContentLength") == z["size"]:
                print(f"  master {name}: already in {mbucket}")
                continue
            if dry_run:
                print(f"  master {name}: would upload to {mbucket}")
                continue
            print(f"  master {name}: uploading {z['size'] / 1e9:.2f} GB to {mbucket}…", flush=True)
            s3.upload_file(z["path"], mbucket, key, ExtraArgs={"ContentType": "application/zip"})

    for label, items in (("conflicts", conflicts), ("errors", errors)):
        if items:
            print(f"{len(items)} {label}:", file=sys.stderr)
            for x in items[:20]:
                print(f"  {x}", file=sys.stderr)
    return 1 if conflicts or errors else 0


def _request(url: str, method: str = "HEAD", headers: dict | None = None):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read() if method == "GET" else b""
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, body
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, b""


def check_one(base: str, version: str, recording: str, r: repo.ChapterRow, ranged: bool) -> list[str]:
    url = f"{base}/{repo.object_key(version, recording, r.book, r.chapter)}"
    status, h, _ = _request(url)
    if status != 200:
        return [f"{url}: HTTP {status}"]
    bad = []
    if h.get("content-length") != str(r.bytes):
        bad.append(f"length {h.get('content-length')} != {r.bytes}")
    if h.get("content-type") != "audio/mpeg":
        bad.append(f"content-type {h.get('content-type')}")
    if h.get("accept-ranges") != "bytes":
        bad.append(f"accept-ranges {h.get('accept-ranges')}")
    if "immutable" not in h.get("cache-control", ""):
        bad.append(f"cache-control {h.get('cache-control')!r}")
    if ranged:
        lo = r.bytes // 2
        hi = lo + 1023
        status, h, body = _request(url, "GET", {"Range": f"bytes={lo}-{hi}"})
        if status != 206 or h.get("content-range") != f"bytes {lo}-{hi}/{r.bytes}" or len(body) != 1024:
            bad.append(f"range request: HTTP {status}, {h.get('content-range')}, {len(body)} bytes")
    return [f"{url}: {'; '.join(bad)}"] if bad else []


def verify(version: str, recording: str, jobs: int) -> int:
    rows = repo.read_chapters(version, recording)
    if not rows:
        raise SystemExit("chapters.tsv is empty; run `audio ingest` first")
    base = repo.load_base()
    state = repo.State(version, recording)
    print(f"verifying {len(rows)} chapters at {base}", flush=True)
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(check_one, base, version, recording, r, i % 50 == 0): r for i, r in enumerate(rows)}
        for i, fut in enumerate(as_completed(futures), 1):
            r = futures[fut]
            try:
                problems = fut.result()
            except Exception as e:
                problems = [f"{r.book} {r.chapter}: {e}"]
            state.chapter(r.book, r.chapter)["verified"] = r.sha256 if not problems else False
            failures += problems
            if i % 100 == 0 or i == len(rows):
                print(f"  {i}/{len(rows)}  failures {len(failures)}", flush=True)
    state.save()
    for f in failures[:30]:
        print(f"  {f}", file=sys.stderr)
    if failures:
        print(f"{len(failures)} chapters failed; do not commit until they pass", file=sys.stderr)
        return 1
    print("all chapters verified")
    return 0
