"""Re-encode one chapter to the site's format with ffmpeg (docs/feature_audio.md §1):
MP3, mono, 64 kbit/s CBR, 44.1 kHz, loudness -16 LUFS and true peak -3 dBTP by two-pass loudnorm,
Xing header, ID3v2.3 tags and no cover art."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

# Bump when the encode changes in a way that should redo every chapter.
# 2: true-peak target -3.0 (was -1.5). FCBH masters are hot (BSB Philemon 1:
# -13.4 LUFS, +1.2 dBTP), so loudnorm falls back to its limiter at exactly the
# target, and a 64 kbit/s MP3 adds about 2 dB of overshoot: -1.5 decoded to
# +0.5 dBTP with samples at 0 dBFS; -3.0 decodes to about -0.7 dBTP.
ENCODER_VERSION = 2
LRA = 11


def require_ffmpeg() -> None:
    for exe in ("ffmpeg", "ffprobe"):
        if not shutil.which(exe):
            raise SystemExit(f"{exe} is not on PATH; install it (winget install Gyan.FFmpeg)")


def settings(enc: dict) -> dict:
    return {
        "encoder": ENCODER_VERSION,
        "bitrate_kbps": int(enc.get("bitrate_kbps", 64)),
        "sample_rate": int(enc.get("sample_rate", 44100)),
        "loudness": float(enc.get("loudness", -16.0)),
        "true_peak": float(enc.get("true_peak", -3.0)),
    }


def _run(args: list[str]) -> subprocess.CompletedProcess:
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        tail = "\n".join(p.stderr.strip().splitlines()[-8:])
        raise RuntimeError(f"{args[0]} failed ({p.returncode}):\n{tail}")
    return p


def measure(src: Path, loudness: float, true_peak: float) -> dict | None:
    """First loudnorm pass; None when the input is silent and can't be measured."""
    p = _run([
        "ffmpeg", "-hide_banner", "-nostdin", "-i", str(src), "-map", "0:a:0",
        "-af", f"loudnorm=I={loudness}:TP={true_peak}:LRA={LRA}:print_format=json",
        "-f", "null", "-",
    ])
    blocks = re.findall(r"\{[^{}]*\}", p.stderr)
    if not blocks:
        raise RuntimeError(f"loudnorm printed no measurement for {src}")
    m = json.loads(blocks[-1])
    if m.get("input_i") in ("-inf", "inf") or m.get("input_tp") in ("-inf", "inf"):
        return None
    return m


def encode(src: Path, dst: Path, s: dict, tags: dict[str, str]) -> None:
    m = measure(src, s["loudness"], s["true_peak"])
    af = "anull"
    if m:
        af = (
            f"loudnorm=I={s['loudness']}:TP={s['true_peak']}:LRA={LRA}"
            f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
            f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
            f":offset={m['target_offset']}:linear=true"
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.stem + ".part.mp3")
    meta = []
    for k, v in tags.items():
        if v:
            meta += ["-metadata", f"{k}={v}"]
    _run([
        "ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", str(src),
        "-map", "0:a:0", "-map_metadata", "-1", "-map_chapters", "-1",
        "-af", af, "-ac", "1", "-ar", str(s["sample_rate"]),
        "-c:a", "libmp3lame", "-b:a", f"{s['bitrate_kbps']}k",
        "-write_xing", "1", "-id3v2_version", "3", *meta,
        str(tmp),
    ])
    tmp.replace(dst)


def probe(path: Path) -> tuple[int, int, str]:
    """(duration ms, bytes, sha256) of an encoded file."""
    p = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    ms = round(float(p.stdout.strip()) * 1000)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return ms, path.stat().st_size, h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()
