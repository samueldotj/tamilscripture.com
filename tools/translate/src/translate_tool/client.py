"""Claude API calls: direct (pilot, repairs) and Message Batches (bulk runs at
half price). Credentials come from the environment (ANTHROPIC_API_KEY or an
`ant auth login` profile); never from a file in the repository."""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone

from . import prompts, repo

DEFAULT_MODEL = "claude-opus-5"
DEFAULT_EFFORT = "medium"
MAX_TOKENS = 64000

USAGE_LOG = repo.WORK / "usage.jsonl"
_LOG_LOCK = threading.Lock()  # direct runs log from several threads
DEFAULT_WORKERS = 6


_CLIENT = None


def client():
    """One client for the whole run. A client made per call can be garbage
    collected, closing its connection, while a streamed response (batch
    results) is still being read."""
    global _CLIENT
    if _CLIENT is None:
        try:
            import anthropic
        except ImportError:
            raise SystemExit("the anthropic package is missing: pip install -e tools/translate")
        _CLIENT = anthropic.Anthropic()
    return _CLIENT


def params(system: list[dict], messages: list[dict], model: str, effort: str) -> dict:
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": messages,
        "output_config": {
            "effort": effort,
            "format": {"type": "json_schema", "schema": prompts.OUTPUT_SCHEMA},
        },
    }


@dataclass
class Reply:
    data: dict | None  # parsed JSON, or None
    error: str | None
    text: str  # raw JSON text, for a repair turn


def read_message(msg) -> Reply:
    if msg.stop_reason == "refusal":
        cat = getattr(getattr(msg, "stop_details", None), "category", None)
        return Reply(None, f"refused ({cat})", "")
    if msg.stop_reason == "max_tokens":
        return Reply(None, "hit max_tokens", "")
    text = next((b.text for b in msg.content if b.type == "text"), "")
    try:
        return Reply(json.loads(text), None, text)
    except json.JSONDecodeError as e:
        return Reply(None, f"invalid JSON: {e}", text)


def log_usage(kind: str, custom_id: str, msg) -> None:
    u = msg.usage
    repo.WORK.mkdir(exist_ok=True)
    row = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        "id": custom_id,
        "model": msg.model,
        "input": u.input_tokens,
        "cache_read": u.cache_read_input_tokens or 0,
        "cache_write": u.cache_creation_input_tokens or 0,
        "output": u.output_tokens,
    }
    with _LOG_LOCK, open(USAGE_LOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row) + "\n")


def run_direct(p: dict, custom_id: str) -> Reply:
    """One request, streamed so long Tamil output cannot time out."""
    import anthropic

    c = client()
    for attempt in range(3):
        try:
            with c.messages.stream(**p) as stream:
                msg = stream.get_final_message()
            log_usage("direct", custom_id, msg)
            return read_message(msg)
        except anthropic.RateLimitError as e:
            wait = int(e.response.headers.get("retry-after", "30"))
            print(f"  rate limited; waiting {wait}s", flush=True)
            time.sleep(wait)
        except (anthropic.APIConnectionError, anthropic.InternalServerError) as e:
            print(f"  {type(e).__name__}; retrying", flush=True)
            time.sleep(10 * (attempt + 1))
    return Reply(None, "gave up after retries", "")


# ---- batches ----

BATCHES = repo.WORK / "batches.jsonl"


def submit_batch(requests: list[tuple[str, dict]], note: str) -> str:
    """requests: (custom_id, params). Records the batch id in the work folder."""
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    batch = client().messages.batches.create(
        requests=[Request(custom_id=cid, params=MessageCreateParamsNonStreaming(**p)) for cid, p in requests]
    )
    repo.WORK.mkdir(exist_ok=True)
    with open(BATCHES, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"id": batch.id, "note": note, "requests": len(requests),
                            "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}) + "\n")
    return batch.id


def batch_status(batch_id: str):
    return client().messages.batches.retrieve(batch_id)


def cancel_batch(batch_id: str):
    """Ask the API to cancel a batch. Requests already done stay done (and
    billed); the rest are cancelled, and the batch ends with them marked so."""
    return client().messages.batches.cancel(batch_id)


def run_many(jobs: list[tuple[str, dict]], workers: int = DEFAULT_WORKERS):
    """Run direct requests `workers` at a time; yield (index, Reply) as each
    finishes, in whatever order. The caller writes results from its own
    thread, so files are never written by two threads at once."""
    client()  # make the one client before the threads share it
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(run_direct, p, cid): k for k, (cid, p) in enumerate(jobs)}
        for f in as_completed(futures):
            yield futures[f], f.result()


def download_results(batch_id: str) -> list:
    """Every result of an ended batch, saved to the work folder first so a
    collect that fails halfway (or runs again) does not need the network."""
    from anthropic.types.messages import MessageBatchIndividualResponse

    path = repo.WORK / f"{batch_id}.results.jsonl"
    if not path.exists():
        part = path.with_suffix(".part")
        with open(part, "w", encoding="utf-8", newline="\n") as f:
            for r in client().messages.batches.results(batch_id):
                f.write(r.to_json(indent=None) + "\n")
        part.replace(path)
        fresh = True
    else:
        fresh = False
    rows = [MessageBatchIndividualResponse.model_validate_json(l)
            for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if fresh:
        for r in rows:
            if r.result.type == "succeeded":
                log_usage("batch", r.custom_id, r.result.message)
    return rows


def batch_results(batch_id: str):
    """(custom_id, Reply) for every request; failed requests give an error Reply."""
    for r in download_results(batch_id):
        match r.result.type:
            case "succeeded":
                yield r.custom_id, read_message(r.result.message)
            case "errored":
                err = r.result.error.error  # ErrorResponse → the typed error
                yield r.custom_id, Reply(None, f"errored: {err.type}: {getattr(err, 'message', '')}", "")
            case other:
                yield r.custom_id, Reply(None, other, "")


def recorded_batches() -> list[dict]:
    if not BATCHES.exists():
        return []
    return [json.loads(line) for line in BATCHES.read_text(encoding="utf-8").splitlines() if line.strip()]
