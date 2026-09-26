"""`translate review-terms --web`: approve the theological glossary one term at
a time in the browser. Each term shows Claude's proposal (editable: Tamil,
forms, renderings to avoid, note), the IRV and KJV verses behind it, and how
the dictionaries use the term. Approving writes the entry without
`review = true`, which is what lets the translator use it.

Same server shape as web.py: 127.0.0.1 only, writes need the X-Review header.
"""

from __future__ import annotations

import html
import json
import re
import threading
import webbrowser
from collections import Counter
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import checks, repo, terms


@dataclass
class TermSession:
    keys: list[str]
    i: int = 0
    counts: Counter = field(default_factory=Counter)
    history: list[tuple[str, dict, int, str]] = field(default_factory=list)

    @property
    def current(self) -> str | None:
        return self.keys[self.i] if self.i < len(self.keys) else None

    def _save(self, key: str, entry: dict, what: str) -> None:
        before = terms.load_file().get(key, {})
        terms.save_entry(key, entry)
        self.history.append((key, before, self.i, what))
        self.counts[what] += 1
        self.i += 1

    def approve(self, ta: str, forms: list[str], avoid: list[str], note: str) -> dict:
        key = self.current
        if key is None:
            raise ValueError("no term left")
        ta = " ".join(ta.split())
        if not re.search(r"[஀-௿]", ta):
            raise ValueError("the Tamil rendering must be in Tamil script")
        e = dict(terms.load_file()[key])
        e.update(ta=ta, forms=list(dict.fromkeys([ta, *forms])), avoid=avoid, note=note.strip(), review=False)
        e.pop("status", None)
        self._save(key, e, "approved")
        return e

    def reject(self) -> None:
        key = self.current
        if key is None:
            raise ValueError("no term left")
        e = dict(terms.load_file()[key])
        e.update(status="rejected", review=True)
        self._save(key, e, "rejected")

    def skip(self) -> None:
        if self.current is not None:
            self.counts["skipped"] += 1
            self.i += 1

    def undo(self) -> str | None:
        if not self.history:
            return None
        key, before, i, what = self.history.pop()
        entries = terms.load_file()
        if before:
            entries[key] = before
        else:
            entries.pop(key, None)
        terms.save_file(entries)
        self.i = i
        self.counts[what] -= 1
        self.counts["undone"] += 1
        return key


def queue(everything: bool = False, include_rejected: bool = False) -> list[str]:
    """Glossary keys to review, in seed order (related terms together)."""
    entries = terms.load_file()
    order = {s.key: k for k, s in enumerate(terms.load_seed())}
    keys = [k for k, e in entries.items()
            if (everything or e.get("review")) and (include_rejected or e.get("status") != "rejected")]
    return sorted(keys, key=lambda k: (order.get(k, 10**6), k))


def _mark_en(text: str, forms: list[str]) -> str:
    t = html.escape(text)
    for f in sorted(forms, key=len, reverse=True):
        flags = 0 if f.isupper() and len(f) > 1 else re.IGNORECASE
        t = re.sub(rf"\b({re.escape(html.escape(f))})(s|es|'s)?\b", r"<mark class=en>\1\2</mark>", t, flags=flags)
    return t


def _mark_ta(text: str, forms: list[str]) -> str:
    t = html.escape(text)
    for f in sorted({f for f in forms if f}, key=len, reverse=True):
        t = re.sub(rf"(?<![஀-௿<]){re.escape(html.escape(f))}", lambda m: f"<mark class=ta>{m[0]}</mark>", t)
    return t


def view(s: TermSession) -> dict:
    base = {"counts": dict(s.counts), "total": len(s.keys), "can_undo": bool(s.history)}
    key = s.current
    if key is None:
        return {**base, "done": True}
    e = terms.load_file()[key]
    seed = next((x for x in terms.load_seed() if x.key == key), None)
    en_forms = [e["en"], *e.get("also", [])]
    n, example = terms.in_articles(seed) if seed else (0, "")
    verses = [{"id": v,
               "en": _mark_en(repo.verse_text(v, "KJV") or "", en_forms),
               "ta": _mark_ta(repo.verse_text(v) or "", e.get("forms", []))}
              for v in e.get("verses", [])]
    return {**base, "done": False, "pos": s.i + 1, "en": e["en"], "also": e.get("also", []),
            "group": e.get("group", "").replace("_", " "), "ta": e.get("ta", ""), "forms": e.get("forms", []),
            "avoid": e.get("avoid", []), "source": e.get("source", ""), "strongs": e.get("strongs", []),
            "note": e.get("note", ""), "status": e.get("status", ""), "articles": n,
            "example": _mark_en(example, en_forms), "verses": verses}


def _split(s: str) -> list[str]:
    return [x.strip() for x in re.split(r"[,،]", s or "") if x.strip()]


def make_handler(s: TermSession):
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data: dict) -> None:
            self._send(200, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            if self.path == "/":
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path.startswith("/api/state"):
                with lock:
                    self._json(view(s))
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path != "/api/answer" or self.headers.get("X-Review") != "1":
                self._send(403, b"forbidden", "text/plain")
                return
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            action = body.get("action")
            with lock:
                key = s.current
                try:
                    if action == "approve":
                        e = s.approve(body.get("ta", ""), _split(body.get("forms", "")), _split(body.get("avoid", "")),
                                      body.get("note", ""))
                        msg = f"✓ {e['en']} = {e['ta']}"
                    elif action == "reject":
                        en = terms.load_file().get(key, {}).get("en", key)
                        s.reject()
                        msg = f"✗ {en} rejected: ask again with `translate ai-terms run --terms \"{en}\"`"
                    elif action == "skip":
                        s.skip()
                        msg = f"→ {key} skipped"
                    elif action == "undo":
                        back = s.undo()
                        msg = f"↶ {back} restored" if back else "nothing to undo"
                    else:
                        raise ValueError(f"unknown action {action!r}")
                except ValueError as err:
                    self._json({"ok": False, "error": str(err)})
                    return
            self._json({"ok": True, "message": msg})

    return Handler


def serve(s: TermSession, port: int = 8766, open_browser: bool = True) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(s))
    server.daemon_threads = True
    url = f"http://127.0.0.1:{port}/"
    print(f"{len(s.keys)} terms to review at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        c = s.counts
        print(f"\n{c['approved']} approved, {c['rejected']} rejected, {c['skipped']} skipped; "
              f"{len(s.keys) - s.i} left in this list.")


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Glossary review</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600&display=swap">
<style>
:root {
  --bg: #f7f6f3; --panel: #ffffff; --fg: #1d1d1b; --muted: #6b6a66; --line: #e3e1db;
  --accent: #1f5f8b; --accent-fg: #ffffff; --en: #fde68a; --ta: #bbf7d0; --ok: #166534; --bad: #9f1239; --key: #efede8;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #141413; --panel: #1d1d1b; --fg: #ecebe7; --muted: #a09e98; --line: #34332f;
    --accent: #6fb3e0; --accent-fg: #0f1a22; --en: #6b5300; --ta: #14532d; --ok: #86efac; --bad: #fda4af; --key: #2a2926;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.55 system-ui, sans-serif; }
[lang=ta] { font-family: "Noto Sans Tamil", "Nirmala UI", "Latha", sans-serif; }
main { max-width: 980px; margin: 0 auto; padding: 16px; }
header { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
header h1 { font-size: 15px; margin: 0; font-weight: 600; }
.bar { flex: 1; min-width: 120px; height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--accent); }
.muted { color: var(--muted); font-size: 13px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px; margin-bottom: 12px; }
.term { font-size: 26px; font-weight: 700; margin: 0; }
.badge { font-size: 12px; padding: 1px 8px; border-radius: 99px; background: var(--key); color: var(--muted); margin-left: 6px; }
.note { margin: 10px 0 0; padding: 8px 10px; border-left: 3px solid var(--accent); background: var(--bg); border-radius: 4px; }
label { display: block; font-size: 12px; color: var(--muted); margin-top: 10px; }
input[type=text], textarea { width: 100%; font-size: 16px; padding: 8px 10px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--bg); color: var(--fg); font-family: inherit; }
#ta { font-size: 22px; font-weight: 600; }
textarea { font-size: 14px; min-height: 3.2em; }
.row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; align-items: center; }
button { padding: 8px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); color: var(--fg); cursor: pointer; font: inherit; }
button.primary { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }
button:disabled { opacity: .45; cursor: default; }
kbd { font: 12px ui-monospace, monospace; background: var(--key); border: 1px solid var(--line); border-radius: 4px; padding: 0 5px; }
#msg { min-height: 1.5em; font-size: 14px; margin-top: 8px; }
#msg.ok { color: var(--ok); } #msg.err { color: var(--bad); }
.verse { border-top: 1px solid var(--line); padding: 10px 0; }
.verse:first-child { border-top: 0; padding-top: 0; }
.ref { font-size: 12px; color: var(--muted); font-weight: 600; }
.verse p { margin: 2px 0; }
.verse p[lang=ta] { font-size: 16px; }
mark { color: inherit; border-radius: 3px; padding: 0 2px; }
mark.en { background: var(--en); } mark.ta { background: var(--ta); }
.help { font-size: 12px; color: var(--muted); line-height: 2; }
.done { text-align: center; padding: 40px 16px; }
@media (max-width: 600px) { .term { font-size: 22px; } main { padding: 12px; } }
</style>
</head>
<body>
<main>
  <header>
    <h1>Theological glossary · review</h1>
    <div class="bar"><i id="bar"></i></div>
    <span class="muted" id="counts"></span>
  </header>
  <div id="app"><div class="card">Loading…</div></div>
  <p class="help"><kbd>Enter</kbd> approve as shown · <kbd>e</kbd> edit the Tamil · <kbd>r</kbd> reject · <kbd>s</kbd> skip ·
    <kbd>u</kbd> undo · in a field, <kbd>Ctrl</kbd>+<kbd>Enter</kbd> approves</p>
</main>
<script>
const app = document.getElementById('app');
let state = null, busy = false, lastMsg = null;
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

async function load() { state = await (await fetch('/api/state')).json(); render(); }

async function answer(action, extra = {}) {
  if (busy) return; busy = true;
  try {
    const r = await fetch('/api/answer', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Review': '1' },
      body: JSON.stringify({ action, ...extra }) });
    const res = await r.json();
    lastMsg = res.ok ? { ok: true, text: res.message } : { ok: false, text: res.error };
    await load();
  } finally { busy = false; }
}

function approve() {
  answer('approve', { ta: document.getElementById('ta').value, forms: document.getElementById('forms').value,
    avoid: document.getElementById('avoid').value, note: document.getElementById('note').value });
}

function render() {
  const c = state.counts || {};
  const doneN = (c.approved || 0) + (c.rejected || 0) + (c.skipped || 0);
  document.getElementById('bar').style.width = `${state.total ? Math.min(100, 100 * doneN / state.total) : 100}%`;
  document.getElementById('counts').textContent =
    `${c.approved || 0} approved · ${c.rejected || 0} rejected · ${c.skipped || 0} skipped · ${state.total} in this session`;
  const msg = lastMsg ? `<div id="msg" class="${lastMsg.ok ? 'ok' : 'err'}">${esc(lastMsg.text)}</div>` : '<div id="msg"></div>';
  if (state.done) {
    app.innerHTML = `<div class="card done"><p>All terms in this session are done.</p>
      <div class="row" style="justify-content:center"><button id="undo" ${state.can_undo ? '' : 'disabled'}>Undo last <kbd>u</kbd></button></div>${msg}</div>`;
    const u = document.getElementById('undo'); if (u) u.onclick = () => answer('undo');
    return;
  }
  const src = state.source === 'irv' ? 'the IRV\\'s word' : state.source === 'curated' ? 'curated: no single Bible word' : state.source;
  const verses = state.verses.map(v => `<div class="verse"><div class="ref">${esc(v.id)}</div>
      <p>${v.en}</p><p lang="ta">${v.ta}</p></div>`).join('') || '<p class="muted">No Bible verses: a curated term.</p>';
  app.innerHTML = `
    <section class="card">
      <div class="muted">${state.pos} of ${state.total} · ${esc(state.group)}</div>
      <h2 class="term">${esc(state.en)}<span class="badge">${esc(src)}</span>${state.status ? `<span class="badge">${esc(state.status)}</span>` : ''}</h2>
      ${state.also.length ? `<div class="muted">also: ${esc(state.also.join(', '))}</div>` : ''}
      <div class="muted">used in ${state.articles} dictionary articles${state.strongs.length ? ' · Strong\\'s ' + esc(state.strongs.join(', ')) : ''}</div>
      ${state.example ? `<p class="muted">“${state.example}”</p>` : ''}
      <label for="ta">Tamil</label><input type="text" id="ta" lang="ta" value="${esc(state.ta)}" autocomplete="off">
      <label for="forms">Forms that count as using it (comma-separated)</label>
      <input type="text" id="forms" lang="ta" value="${esc(state.forms.join(', '))}" autocomplete="off">
      <label for="avoid">Renderings to avoid (comma-separated)</label>
      <input type="text" id="avoid" lang="ta" value="${esc(state.avoid.join(', '))}" autocomplete="off">
      <label for="note">Note</label><textarea id="note">${esc(state.note)}</textarea>
      <div class="row">
        <button class="primary" id="approve">Approve <kbd>Enter</kbd></button>
        <button id="reject">Reject <kbd>r</kbd></button>
        <button id="skip">Skip <kbd>s</kbd></button>
        <button id="undo" ${state.can_undo ? '' : 'disabled'}>Undo <kbd>u</kbd></button>
      </div>
      ${msg}
    </section>
    <section class="card">
      <div class="muted"><mark class="en">English term</mark> <mark class="ta">Tamil forms</mark> · KJV and IRV</div>
      ${verses}
    </section>`;
  document.getElementById('approve').onclick = approve;
  document.getElementById('reject').onclick = () => answer('reject');
  document.getElementById('skip').onclick = () => answer('skip');
  document.getElementById('undo').onclick = () => answer('undo');
}

document.addEventListener('keydown', e => {
  const typing = ['INPUT', 'TEXTAREA'].includes(e.target.tagName);
  if (typing) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); approve(); }
    else if (e.key === 'Escape') e.target.blur();
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey || !state) return;
  if (e.key === 'u') return answer('undo');
  if (state.done) return;
  if (e.key === 'Enter') { e.preventDefault(); return approve(); }
  if (e.key === 'r') return answer('reject');
  if (e.key === 's') return answer('skip');
  if (e.key === 'e') { e.preventDefault(); const t = document.getElementById('ta'); t.focus(); t.select(); }
});

load();
</script>
</body>
</html>
"""
