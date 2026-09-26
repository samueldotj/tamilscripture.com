"""`translate review-names --web`: the name review in a browser, which draws
Tamil properly where Windows consoles do not. A small server on 127.0.0.1
serves one page and a JSON API over the same `Session` the terminal uses;
every answer is written to names-ta.toml at once.

Writes need the `X-Review` header, which a page on another site cannot send
to this server without a CORS preflight it never gets an answer to.
"""

from __future__ import annotations

import html
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import repo, review
from .review import TAMIL_WORD
from .session import Session, state_of, suggest

VERSES_SHOWN = 4


def _mark_en(text: str, name: str) -> str:
    import re

    t = html.escape(text)
    pat = re.compile(rf"\b{re.escape(html.escape(name))}\b", re.IGNORECASE)
    return pat.sub(lambda m: f"<mark class=en>{m[0]}</mark>", t)


def _mark_ta(text: str, style) -> str:
    return TAMIL_WORD.sub(
        lambda m: f"<mark class={s}>{m[0]}</mark>" if (s := style(m[0])) else m[0], html.escape(text)
    )


def view(s: Session, shown: int, tcv: bool, english: str) -> dict:
    """Everything the page shows for the current name."""
    base = {"counts": dict(s.counts), "total": len(s.items), "can_undo": bool(s.history)}
    item = s.current
    if item is None:
        return {**base, "done": True, "summary": s.summary()}
    cands, suggestions = suggest(item)
    few = len(item.verses) <= 3
    style = review.tamil_style({item.entry["label"], *item.entry["forms"]}, cands[0].prefix if cands else None)
    verses = []
    for vid in item.verses[:shown]:
        row = {
            "id": vid,
            "en": _mark_en(repo.verse_text(vid, english) or "(no text)", item.name),
            "ta": [{"near": label, "html": _mark_ta(t, style)} for label, t in review.tamil_rows(vid, repo.TAMIL_VERSION, style, few)],
        }
        if tcv:
            row["tcv"] = [{"near": label, "html": _mark_ta(t, style)} for label, t in review.tamil_rows(vid, "TCV", style, few)]
        verses.append(row)
    return {
        **base,
        "done": False,
        "pos": s.i + 1,
        "name": item.name,
        "state": state_of(item.entry),
        "confidence": item.entry.get("confidence", 1.0),
        "label": item.entry["label"],
        "forms": item.entry["forms"][:12],
        "briefs": review.name_briefs().get(item.name, [])[:4],
        "ai": _ai_notes().get(item.name),
        "n_verses": len(item.verses),
        "more": max(0, len(item.verses) - shown),
        "verses": verses,
        "english": english,
        "suggestions": [
            {"label": g.label, "covered": g.covered, "sounds": round(g.sounds, 2), "words": g.words[:4], "ai": g.ai}
            for g in suggestions
        ],
    }


def _ai_notes() -> dict:
    from . import ai_names

    return ai_names.notes()


def make_handler(s: Session, english: str):
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data: dict, code: int = 200) -> None:
            self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            from urllib.parse import parse_qs, urlparse

            u = urlparse(self.path)
            if u.path == "/":
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif u.path == "/api/state":
                q = parse_qs(u.query)
                shown = VERSES_SHOWN + int(q.get("more", ["0"])[0] or 0)
                with lock:
                    self._json(view(s, shown, q.get("tcv", ["0"])[0] == "1", english))
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path != "/api/answer" or self.headers.get("X-Review") != "1":
                self._send(403, b"forbidden", "text/plain")
                return
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            action = body.get("action")
            with lock:
                name = s.current.name if s.current else None
                try:
                    if action == "accept":
                        forms = [f.strip() for f in (body.get("forms") or "").split(",") if f.strip()] or None
                        after = s.accept(body.get("label", ""), forms)
                        msg = f"✓ {name} = {after['label']}  ({', '.join(after['forms'][:6])})"
                    elif action == "keep":
                        after = s.keep()
                        msg = f"✓ {name} = {after['label']} (kept)"
                    elif action == "reject":
                        s.reject()
                        msg = f"✗ {name} rejected: hidden on the site until someone gives the Tamil"
                    elif action == "skip":
                        s.skip()
                        msg = f"→ {name} skipped"
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


def serve(s: Session, english: str = "KJV", port: int = 8765, open_browser: bool = True) -> None:
    # Threaded: browsers open spare connections and leave them idle, which
    # would block a single-threaded server. The handler's lock keeps the
    # session to one request at a time.
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(s, english))
    server.daemon_threads = True
    url = f"http://127.0.0.1:{port}/"
    print(f"{len(s.items)} names to review at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("\n" + s.summary())
        if s.counts["accepted"]:
            print("Run `pnpm content` to check the accepted forms against the text.")


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Name review</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600&display=swap">
<style>
:root {
  --bg: #f7f6f3; --panel: #ffffff; --fg: #1d1d1b; --muted: #6b6a66; --line: #e3e1db;
  --accent: #1f5f8b; --accent-fg: #ffffff; --en: #fde68a; --cand: #bae6fd; --known: #bbf7d0;
  --ok: #166534; --bad: #9f1239; --key: #efede8;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #141413; --panel: #1d1d1b; --fg: #ecebe7; --muted: #a09e98; --line: #34332f;
    --accent: #6fb3e0; --accent-fg: #0f1a22; --en: #6b5300; --cand: #0e4a66; --known: #14532d;
    --ok: #86efac; --bad: #fda4af; --key: #2a2926;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.55 system-ui, sans-serif; }
[lang=ta], .ta { font-family: "Noto Sans Tamil", "Nirmala UI", "Latha", sans-serif; }
main { max-width: 980px; margin: 0 auto; padding: 16px; }
header { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
header h1 { font-size: 15px; margin: 0; font-weight: 600; }
.bar { flex: 1; min-width: 120px; height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--accent); }
.counts { color: var(--muted); font-size: 13px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px; margin-bottom: 12px; }
.name { font-size: 26px; font-weight: 700; margin: 0; }
.now { margin-top: 4px; }
.badge { font-size: 12px; padding: 1px 8px; border-radius: 99px; background: var(--key); color: var(--muted); margin-left: 6px; }
.briefs { color: var(--muted); font-size: 13px; margin: 6px 0 0; padding: 0; list-style: none; }
.claude { color: var(--accent); font-weight: 600; }
.ai { margin: 8px 0 0; padding: 8px 10px; border-left: 3px solid var(--accent); background: var(--bg); border-radius: 4px; }
.sugg { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 8px; margin-top: 12px; }
.sugg button { text-align: left; padding: 10px 12px; border: 1px solid var(--line); background: var(--panel); color: var(--fg);
  border-radius: 8px; cursor: pointer; }
.sugg button:hover, .sugg button:focus-visible { border-color: var(--accent); outline: none; }
.sugg button.first { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
.sugg .lbl { font-size: 20px; font-weight: 600; display: block; }
.sugg .meta { font-size: 12px; color: var(--muted); display: block; }
kbd { font: 12px ui-monospace, monospace; background: var(--key); border: 1px solid var(--line); border-radius: 4px; padding: 0 5px; }
.row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; align-items: center; }
input[type=text] { font-size: 17px; padding: 8px 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); color: var(--fg); min-width: 0; }
#label { flex: 1 1 180px; } #forms { flex: 2 1 240px; font-size: 14px; }
.actions button { padding: 8px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); color: var(--fg); cursor: pointer; }
.actions button.primary { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }
.actions button:disabled { opacity: .45; cursor: default; }
#msg { min-height: 1.5em; font-size: 14px; margin-top: 8px; }
#msg.ok { color: var(--ok); } #msg.err { color: var(--bad); }
.verse { border-top: 1px solid var(--line); padding: 10px 0; }
.verse:first-child { border-top: 0; padding-top: 0; }
.ref { font-size: 12px; color: var(--muted); font-weight: 600; }
.en { margin: 2px 0; }
.tatext { margin: 2px 0; font-size: 16px; }
.near { color: var(--muted); font-size: 14px; }
.near small, .tcv small { font-family: system-ui, sans-serif; font-size: 11px; margin-right: 4px; }
.tcv { color: var(--muted); font-size: 14px; }
mark { color: inherit; border-radius: 3px; padding: 0 2px; }
mark.en { background: var(--en); } mark.cand { background: var(--cand); } mark.known { background: var(--known); }
.legend { font-size: 12px; color: var(--muted); }
.help { font-size: 12px; color: var(--muted); line-height: 2; }
.done { text-align: center; padding: 40px 16px; }
@media (max-width: 600px) { .name { font-size: 22px; } main { padding: 12px; } }
</style>
</head>
<body>
<main>
  <header>
    <h1>Tamil names · review</h1>
    <div class="bar"><i id="bar"></i></div>
    <span class="counts" id="counts"></span>
  </header>
  <div id="app"><div class="card">Loading…</div></div>
  <p class="help">
    <kbd>Enter</kbd> accept 1 · <kbd>1</kbd>–<kbd>5</kbd> accept · <kbd>/</kbd> type a name · <kbd>c</kbd> keep current ·
    <kbd>r</kbd> reject · <kbd>s</kbd> skip · <kbd>u</kbd> undo · <kbd>m</kbd> more verses · <kbd>t</kbd> TCV
  </p>
</main>
<script>
const app = document.getElementById('app');
let state = null, more = 0, tcv = false, busy = false, lastMsg = null;

function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

async function load() {
  const r = await fetch(`/api/state?more=${more}&tcv=${tcv ? 1 : 0}`);
  state = await r.json();
  render();
}

async function answer(action, extra = {}) {
  if (busy) return;
  busy = true;
  try {
    const r = await fetch('/api/answer', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Review': '1' },
      body: JSON.stringify({ action, ...extra }) });
    const res = await r.json();
    lastMsg = res.ok ? { ok: true, text: res.message } : { ok: false, text: res.error };
    if (res.ok) more = 0;
    await load();
  } finally { busy = false; }
}

function render() {
  const c = state.counts || {};
  const doneCount = (c.accepted || 0) + (c.rejected || 0) + (c.skipped || 0);
  document.getElementById('bar').style.width = `${state.total ? Math.min(100, 100 * doneCount / state.total) : 100}%`;
  document.getElementById('counts').textContent =
    `${c.accepted || 0} accepted · ${c.rejected || 0} rejected · ${c.skipped || 0} skipped · ${state.total} in this session`;
  const msg = lastMsg ? `<div id="msg" class="${lastMsg.ok ? 'ok' : 'err'}">${esc(lastMsg.text)}</div>` : '<div id="msg"></div>';
  if (state.done) {
    app.innerHTML = `<div class="card done"><p>${esc(state.summary)}</p><p>Run <kbd>pnpm content</kbd> to check the accepted forms.</p>
      <div class="row actions" style="justify-content:center"><button id="undo" ${state.can_undo ? '' : 'disabled'}>Undo last <kbd>u</kbd></button></div>${msg}</div>`;
    const u = document.getElementById('undo'); if (u) u.onclick = () => answer('undo');
    return;
  }
  const sugg = state.suggestions.map((g, k) => `
    <button data-k="${k}" class="${k === 0 ? 'first' : ''}">
      <span class="meta"><kbd>${k + 1}</kbd></span>
      <span class="lbl" lang="ta">${esc(g.label)}</span>
      <span class="meta">${g.ai ? '<span class="claude">Claude</span> · ' : `${g.covered}/${state.n_verses} verses · `}sounds ${g.sounds.toFixed(2)}</span>
      <span class="meta" lang="ta">${esc(g.words.map(w => w[0]).join(', '))}</span>
    </button>`).join('');
  const verses = state.verses.map(v => `
    <div class="verse">
      <div class="ref">${esc(v.id)}</div>
      <p class="en">${v.en}</p>
      ${v.ta.map(t => `<p class="tatext ${t.near ? 'near' : ''}" lang="ta">${t.near ? `<small>${esc(t.near)}</small>` : ''}${t.html}</p>`).join('')}
      ${(v.tcv || []).map(t => `<p class="tcv" lang="ta"><small>TCV${t.near ? ' ' + esc(t.near) : ''}</small>${t.html}</p>`).join('')}
    </div>`).join('');
  app.innerHTML = `
    <section class="card">
      <div class="counts">${state.pos} of ${state.total}</div>
      <h2 class="name">${esc(state.name)}</h2>
      <div class="now">Now: <strong lang="ta">${esc(state.label)}</strong><span class="badge">${esc(state.state)} · confidence ${Number(state.confidence).toFixed(2)}</span></div>
      <ul class="briefs">${state.briefs.map(b => `<li>${esc(b)}</li>`).join('')}</ul>
      ${state.ai ? `<p class="ai">Claude: <strong lang="ta">${esc(state.ai.label)}</strong>
        <span class="badge">${esc(state.ai.source === 'irv' ? 'found in the IRV' : 'composed')} · ${esc(state.ai.confidence)}</span>
        ${state.ai.note ? `<br><span class="counts">${esc(state.ai.note)}</span>` : ''}
        ${state.ai.why ? `<br><span class="counts">Not accepted automatically: ${esc(state.ai.why)}</span>` : ''}</p>` : ''}
      <div class="sugg">${sugg || '<span class="counts">No suggestions: type the name, or reject.</span>'}</div>
      <form class="row" id="typed">
        <input type="text" id="label" lang="ta" placeholder="Type the Tamil name" autocomplete="off">
        <input type="text" id="forms" lang="ta" placeholder="Forms, comma-separated (optional)" autocomplete="off">
        <button class="primary" type="submit" style="padding:8px 12px;border-radius:8px;border:1px solid var(--accent);background:var(--accent);color:var(--accent-fg)">Save</button>
      </form>
      <div class="row actions">
        <button id="keep">Keep current <kbd>c</kbd></button>
        <button id="reject">Reject <kbd>r</kbd></button>
        <button id="skip">Skip <kbd>s</kbd></button>
        <button id="undo" ${state.can_undo ? '' : 'disabled'}>Undo <kbd>u</kbd></button>
      </div>
      ${msg}
    </section>
    <section class="card">
      <div class="legend"><mark class="en">English name</mark> <mark class="cand">best candidate</mark> <mark class="known">current entry</mark> · ${esc(state.english)} and IRV${tcv ? ' and TCV' : ''}</div>
      ${verses}
      <div class="row actions">
        ${state.more ? `<button id="more">${state.more} more verses <kbd>m</kbd></button>` : ''}
        <button id="tcv">${tcv ? 'Hide' : 'Show'} TCV <kbd>t</kbd></button>
      </div>
    </section>`;
  app.querySelectorAll('.sugg button').forEach(b => b.onclick = () => answer('accept', { label: state.suggestions[+b.dataset.k].label }));
  document.getElementById('typed').onsubmit = e => {
    e.preventDefault();
    const label = document.getElementById('label').value.trim();
    if (label) answer('accept', { label, forms: document.getElementById('forms').value });
  };
  document.getElementById('keep').onclick = () => answer('keep');
  document.getElementById('reject').onclick = () => answer('reject');
  document.getElementById('skip').onclick = () => answer('skip');
  document.getElementById('undo').onclick = () => answer('undo');
  const m = document.getElementById('more'); if (m) m.onclick = () => { more += 10; load(); };
  document.getElementById('tcv').onclick = () => { tcv = !tcv; load(); };
}

document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') { if (e.key === 'Escape') e.target.blur(); return; }
  if (e.ctrlKey || e.metaKey || e.altKey || !state) return;
  const k = e.key;
  if (k === 'u') return answer('undo');
  if (state.done) return;
  if (k === 'Enter' && state.suggestions.length) { e.preventDefault(); return answer('accept', { label: state.suggestions[0].label }); }
  if (/^[1-5]$/.test(k) && state.suggestions[+k - 1]) return answer('accept', { label: state.suggestions[+k - 1].label });
  if (k === 'c') return answer('keep');
  if (k === 'r') return answer('reject');
  if (k === 's') return answer('skip');
  if (k === 'm' && state.more) { more += 10; return load(); }
  if (k === 't') { tcv = !tcv; return load(); }
  if (k === '/' || k === 'e') { e.preventDefault(); document.getElementById('label').focus(); }
});

load();
</script>
</body>
</html>
"""
