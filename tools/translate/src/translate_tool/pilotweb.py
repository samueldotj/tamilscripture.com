"""`translate review-pilot --web`: compare two models' pilot drafts blind.

Each article shows the English paragraphs beside version A and version B, with
the checks' remaining problems under each. Which model is A is fixed per
article (a hash of its id) and hidden until every article is rated; ratings
are stored with the model names in .translate-work/pilot/ratings.jsonl.
"""

from __future__ import annotations

import hashlib
import html
import json
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import pilot

WINNERS = {"a": "A better", "b": "B better", "g": "both good", "w": "both need work"}


class PilotSession:
    def __init__(self, models: list[str], pm=pilot):
        self.pm = pm
        if len(models) != 2:
            raise SystemExit(f"the comparison needs drafts from two models; found {models or 'none'} "
                             "(translate pilot run --model …)")
        self.models = models
        self.ids = [i for i in pm.ids()
                    if all(pm.draft(m, pm.load(i)) for m in models)]
        self.problems = {m: pm.problems(m) for m in models}
        self.i = self.first_unrated()
        self.lock = threading.Lock()

    def first_unrated(self) -> int:
        done = self.pm.ratings()
        return next((k for k, i in enumerate(self.ids) if i not in done), len(self.ids))

    def order(self, article_id: str) -> tuple[str, str]:
        """(model shown as A, model shown as B), fixed per article."""
        flip = hashlib.sha1(article_id.encode()).digest()[0] % 2
        a, b = self.models
        return (b, a) if flip else (a, b)

    def view(self) -> dict:
        done = self.pm.ratings()
        base = {"total": len(self.ids), "rated": sum(i in done for i in self.ids)}
        if self.i >= len(self.ids):
            return {**base, "done": True, "summary": self.pm.status(), "results": self.results()}
        aid = self.ids[self.i]
        art = self.pm.load(aid)
        ma, mb = self.order(aid)
        da, db = self.pm.draft(ma, art), self.pm.draft(mb, art)
        ta = {p["id"]: p["text"] for p in da["paragraphs"]}
        tb = {p["id"]: p["text"] for p in db["paragraphs"]}
        rows = [{"en": p["text"], "a": ta.get(p["id"], ""), "b": tb.get(p["id"], ""), "heading": p.get("heading", False)}
                for p in art["paragraphs"]]
        prev = done.get(aid)
        return {**base, "done": False, "pos": self.i + 1, "id": aid, "title": art["title"],
                "title_a": da.get("title", ""), "title_b": db.get("title", ""), "rows": rows,
                "problems_a": self.problems[ma].get(aid, []), "problems_b": self.problems[mb].get(aid, []),
                "previous": {"winner": prev["label"], "note": prev.get("note", "")} if prev else None}

    def results(self) -> dict:
        """Model → how often it won, once everything is rated."""
        out = {m: {"better": 0, "worse": 0, "both good": 0, "both need work": 0} for m in self.models}
        for i, r in self.pm.ratings().items():
            if i not in self.ids:
                continue
            for m in self.models:
                if r["label"] in ("both good", "both need work"):
                    out[m][r["label"]] += 1
                else:
                    out[m]["better" if r["winner"] == m else "worse"] += 1
        return out

    def rate(self, key: str, note: str) -> str:
        if self.i >= len(self.ids):
            raise ValueError("every article is rated")
        aid = self.ids[self.i]
        ma, mb = self.order(aid)
        label = WINNERS[key]
        winner = ma if key == "a" else mb if key == "b" else label
        self.pm.ROOT.mkdir(parents=True, exist_ok=True)
        with open(self.pm.RATINGS, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"id": aid, "label": label, "winner": winner, "a": ma, "b": mb, "note": note.strip(),
                                "at": datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False) + "\n")
        self.i += 1
        return f"{aid}: {label}"

    def move(self, step: int) -> None:
        self.i = max(0, min(len(self.ids), self.i + step))


def make_handler(s: PilotSession):
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
                with s.lock:
                    self._json(s.view())
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path != "/api/answer" or self.headers.get("X-Review") != "1":
                self._send(403, b"forbidden", "text/plain")
                return
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            with s.lock:
                try:
                    act = body.get("action")
                    if act in WINNERS:
                        msg = s.rate(act, body.get("note", ""))
                    elif act == "prev":
                        s.move(-1)
                        msg = ""
                    elif act == "next":
                        s.move(1)
                        msg = ""
                    else:
                        raise ValueError(f"unknown action {act!r}")
                except ValueError as err:
                    self._json({"ok": False, "error": str(err)})
                    return
            self._json({"ok": True, "message": msg})

    return Handler


def serve(port: int = 8767, open_browser: bool = True, pm=pilot) -> None:
    s = PilotSession(pm.models(), pm)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(s))
    server.daemon_threads = True
    url = f"http://127.0.0.1:{port}/"
    print(f"{len(s.ids)} pilot articles to compare at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("\n" + pm.status())


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pilot comparison</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600&display=swap">
<style>
:root { --bg:#f7f6f3; --panel:#fff; --fg:#1d1d1b; --muted:#6b6a66; --line:#e3e1db; --accent:#1f5f8b; --accent-fg:#fff;
  --warn:#9a3412; --ok:#166534; --key:#efede8; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#141413; --panel:#1d1d1b; --fg:#ecebe7;
  --muted:#a09e98; --line:#34332f; --accent:#6fb3e0; --accent-fg:#0f1a22; --warn:#fdba74; --ok:#86efac; --key:#2a2926; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.6 system-ui, sans-serif; }
[lang=ta] { font-family: "Noto Sans Tamil", "Nirmala UI", "Latha", sans-serif; }
main { max-width:1400px; margin:0 auto; padding:16px; }
header { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:12px; }
header h1 { font-size:15px; margin:0; }
.bar { flex:1; min-width:120px; height:6px; background:var(--line); border-radius:3px; overflow:hidden; }
.bar i { display:block; height:100%; background:var(--accent); }
.muted { color:var(--muted); font-size:13px; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px; margin-bottom:12px; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th, td { text-align:left; vertical-align:top; padding:8px; border-top:1px solid var(--line); }
th { font-size:13px; color:var(--muted); font-weight:600; border-top:0; }
td.en { color:var(--muted); font-size:14px; }
td[lang=ta] { font-size:15.5px; }
tr.heading td { font-weight:700; }
.titles td { font-size:18px; font-weight:700; }
.problems { font-size:13px; color:var(--warn); margin:0; padding-left:18px; }
.row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-top:12px; }
button { padding:8px 12px; border:1px solid var(--line); border-radius:8px; background:var(--panel); color:var(--fg); cursor:pointer; font:inherit; }
button.primary { background:var(--accent); color:var(--accent-fg); border-color:var(--accent); }
textarea { width:100%; min-height:3em; font:inherit; font-size:14px; padding:8px; border:1px solid var(--line); border-radius:8px; background:var(--bg); color:var(--fg); }
kbd { font:12px ui-monospace, monospace; background:var(--key); border:1px solid var(--line); border-radius:4px; padding:0 5px; }
#msg { min-height:1.4em; font-size:14px; color:var(--ok); }
pre { white-space:pre-wrap; font:13px/1.5 ui-monospace, monospace; }
@media (max-width: 800px) { table, tbody, tr, td, th { display:block; } th { display:none; } td { border-top:0; }
  tr { border-top:1px solid var(--line); padding:6px 0; } td[data-label]::before { content: attr(data-label) " "; font-weight:600; color:var(--muted); } }
</style>
</head>
<body>
<main>
  <header><h1>Pilot · blind comparison</h1><div class="bar"><i id="bar"></i></div><span class="muted" id="counts"></span></header>
  <div id="app"><div class="card">Loading…</div></div>
  <p class="muted"><kbd>a</kbd> A better · <kbd>b</kbd> B better · <kbd>g</kbd> both good · <kbd>w</kbd> both need work ·
    <kbd>←</kbd>/<kbd>→</kbd> previous/next · write a note first if you like (it is saved with the rating)</p>
</main>
<script>
const app = document.getElementById('app');
let state = null, busy = false, msg = '';
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function load() { state = await (await fetch('/api/state')).json(); render(); }
async function act(action) {
  if (busy) return; busy = true;
  try {
    const note = document.getElementById('note')?.value || '';
    const r = await (await fetch('/api/answer', { method:'POST', headers:{'Content-Type':'application/json','X-Review':'1'},
      body: JSON.stringify({ action, note }) })).json();
    msg = r.ok ? r.message : r.error; await load(); window.scrollTo(0, 0);
  } finally { busy = false; }
}
function render() {
  document.getElementById('bar').style.width = `${state.total ? 100 * state.rated / state.total : 0}%`;
  document.getElementById('counts').textContent = `${state.rated} of ${state.total} rated`;
  if (state.done) {
    const res = Object.entries(state.results).map(([m, r]) =>
      `<tr><td>${esc(m)}</td><td>${r.better}</td><td>${r.worse}</td><td>${r['both good']}</td><td>${r['both need work']}</td></tr>`).join('');
    app.innerHTML = `<div class="card"><h2>Results</h2>
      <table><tr><th>Model</th><th>Better</th><th>Worse</th><th>Both good</th><th>Both need work</th></tr>${res}</table>
      <pre>${esc(state.summary)}</pre>
      <div class="row"><button id="prev">← Back to the last article</button></div></div>`;
    document.getElementById('prev').onclick = () => act('prev');
    return;
  }
  const rows = state.rows.map(r => `<tr class="${r.heading ? 'heading' : ''}">
      <td class="en" data-label="EN">${esc(r.en)}</td><td lang="ta" data-label="A">${esc(r.a)}</td><td lang="ta" data-label="B">${esc(r.b)}</td></tr>`).join('');
  const probs = p => p.length ? `<ul class="problems">${p.map(x => `<li>${esc(x.replace(/^[^:]+#p\\d+-[0-9a-f]+: /, ''))}</li>`).join('')}</ul>` : '<span class="muted">no problems found by the checks</span>';
  app.innerHTML = `
    <section class="card">
      <div class="muted">${state.pos} of ${state.total} · ${esc(state.id)}${state.previous ? ` · rated before: ${esc(state.previous.winner)}` : ''}</div>
      <table>
        <tr><th style="width:28%">English</th><th>A</th><th>B</th></tr>
        <tr class="titles"><td>${esc(state.title)}</td><td lang="ta">${esc(state.title_a)}</td><td lang="ta">${esc(state.title_b)}</td></tr>
        ${rows}
        <tr><td class="muted">Checks</td><td>${probs(state.problems_a)}</td><td>${probs(state.problems_b)}</td></tr>
      </table>
      <textarea id="note" placeholder="Note (optional): what is wrong or better">${esc(state.previous?.note || '')}</textarea>
      <div class="row">
        <button class="primary" data-a="a">A better <kbd>a</kbd></button>
        <button class="primary" data-a="b">B better <kbd>b</kbd></button>
        <button data-a="g">Both good <kbd>g</kbd></button>
        <button data-a="w">Both need work <kbd>w</kbd></button>
        <button data-a="prev">← Previous</button><button data-a="next">Next →</button>
        <span id="msg">${esc(msg)}</span>
      </div>
    </section>`;
  app.querySelectorAll('button[data-a]').forEach(b => b.onclick = () => act(b.dataset.a));
}
document.addEventListener('keydown', e => {
  if (['TEXTAREA', 'INPUT'].includes(e.target.tagName)) { if (e.key === 'Escape') e.target.blur(); return; }
  if (e.ctrlKey || e.metaKey || e.altKey || !state) return;
  if (e.key === 'ArrowLeft') return act('prev');
  if (e.key === 'ArrowRight') return act('next');
  if (state.done) return;
  if (['a', 'b', 'g', 'w'].includes(e.key)) act(e.key);
});
load();
</script>
</body>
</html>
"""
