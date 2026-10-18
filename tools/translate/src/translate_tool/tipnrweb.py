"""`translate tipnr review`: go through the TIPNR lines the checks flagged, one
at a time in the browser. Each shows the English, who it describes, what the
checks found, the Tamil names and glossary terms the line uses (with whether
the name is reviewed in names-ta.toml), and the Tamil, editable and checked
again as you type.

- Accept writes the Tamil as shown to drafts/ta/tipnr.json, overruling any
  problem the checks still report (a check can be wrong: "Song of Solomon").
- Reject leaves the line without Tamil (the site shows the English) and keeps
  it flagged; the reason you give goes with it to `translate tipnr submit
  --repair`, which asks Claude again.

Same server shape as web.py: 127.0.0.1 only, writes need the X-Review header.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import checks, repo, tipnr


@dataclass
class Item:
    en: str
    kind: str
    about: list[str]
    ta: str
    problems: list[str]
    status: str  # flagged | rejected | written


def queue(texts: list[str] | None = None, include_rejected: bool = False) -> list[Item]:
    """The flagged lines (rejected ones only when asked), or with `texts`
    every line containing one of them, written or not."""
    every = tipnr.lines()
    failed = tipnr.failures()
    written = tipnr.load_drafts()["texts"]
    out = []
    if texts:
        for en, line in every.items():
            if not any(t.lower() in en.lower() for t in texts):
                continue
            r = failed.get(en)
            if r:
                out.append(Item(en, line.kind, line.about, r.get("ta") or "", r["problems"],
                                "rejected" if r.get("rejected") else "flagged"))
            else:
                out.append(Item(en, line.kind, line.about, written.get(en, ""), [], "written" if en in written else "flagged"))
    else:
        for en, r in failed.items():
            if r.get("rejected") and not include_rejected:
                continue
            line = every.get(en)
            out.append(Item(en, r.get("kind", "short"), line.about if line else [], r.get("ta") or "", r["problems"],
                            "rejected" if r.get("rejected") else "flagged"))
    out.sort(key=lambda i: (i.about[0].lower() if i.about else "", i.en))
    return out


@dataclass
class Session:
    items: list[Item]
    i: int = 0
    counts: Counter = field(default_factory=Counter)
    # (index, the drafts entry before, the line's last log row before, what)
    history: list[tuple[int, str | None, dict | None, str]] = field(default_factory=list)
    ctx: tipnr.Context = field(default_factory=tipnr.Context)

    @property
    def current(self) -> Item | None:
        return self.items[self.i] if self.i < len(self.items) else None

    def _record(self, item: Item, row: dict, ta: str | None, what: str) -> None:
        drafts = tipnr.load_drafts()
        before = drafts["texts"].get(item.en)
        last = _last_rows().get(item.en)
        if ta is None:
            drafts["texts"].pop(item.en, None)
        else:
            drafts["texts"][item.en] = ta
        tipnr.save_drafts(drafts)
        _append(row)
        self.history.append((self.i, before, last, what))
        self.counts[what] += 1
        self.i += 1

    def accept(self, ta: str) -> str:
        item = self.current
        if item is None:
            raise ValueError("no line left")
        ta = " ".join(ta.split())
        if why := checks.check_text(ta):
            raise ValueError(f"cannot write it: {why}")
        overruled = tipnr.check(tipnr.Line(item.en, item.kind, item.about), ta, self.ctx)
        self._record(item, _row(item, ta, [], reviewed="accepted", overruled=overruled), ta, "accepted")
        return ta

    def reject(self, ta: str, reason: str) -> None:
        item = self.current
        if item is None:
            raise ValueError("no line left")
        problems = [f"rejected in review: {reason.strip()}"] if reason.strip() else (item.problems or ["rejected in review"])
        self._record(item, _row(item, " ".join(ta.split()), problems, reviewed="rejected", rejected=True), None, "rejected")

    def skip(self) -> None:
        if self.current is None:
            raise ValueError("no line left")
        self.history.append((self.i, None, None, "skipped"))
        self.counts["skipped"] += 1
        self.i += 1

    def undo(self) -> str | None:
        if not self.history:
            return None
        i, before, last, what = self.history.pop()
        self.counts[what] -= 1
        self.i = i
        item = self.items[i]
        if what != "skipped":
            drafts = tipnr.load_drafts()
            if before is None:
                drafts["texts"].pop(item.en, None)
            else:
                drafts["texts"][item.en] = before
            tipnr.save_drafts(drafts)
            # The log is append-only: the line's earlier row, again, is its state.
            if last:
                _append({**last, "at": datetime.now().isoformat(timespec="seconds"), "undone": True})
        return item.en


def _row(item: Item, ta: str, problems: list[str], **extra) -> dict:
    return {"en": item.en, "kind": item.kind, "ta": ta, "problems": problems, "model": "review",
            "prompt_version": tipnr.PROMPT_VERSION, "at": datetime.now().isoformat(timespec="seconds"), **extra}


def _append(row: dict) -> None:
    repo.WORK.mkdir(exist_ok=True)
    with open(tipnr.LOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _last_rows() -> dict[str, dict]:
    last: dict[str, dict] = {}
    if tipnr.LOG.exists():
        for l in tipnr.LOG.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                last[r["en"]] = r
    return last


def hints(item: Item, ctx: tipnr.Context) -> dict:
    """The names and glossary terms the line uses, as the request gave them."""
    names = []
    seen = set()
    for n in checks.names_in(item.en, ctx.names):
        seen.add(n.en)
        names.append({"en": n.en, "ta": n.label, "forms": n.forms[:6], "reviewed": True})
    for who in item.about:
        if who in seen:
            continue
        e = ctx.provisional.get(who)
        if e:
            names.append({"en": who, "ta": e["label"], "forms": list(e.get("forms", []))[:6], "reviewed": not e.get("review")})
    terms = [{"en": t.en, "ta": t.ta, "avoid": t.avoid} for t in checks.terms_in(item.en, ctx.terms)]
    return {"names": names, "terms": terms}


def view(s: Session) -> dict:
    item = s.current
    base = {"total": len(s.items), "pos": s.i + 1, "counts": dict(s.counts), "can_undo": bool(s.history)}
    if item is None:
        return {**base, "done": True}
    return {**base, "done": False, "en": item.en, "kind": item.kind, "about": item.about, "ta": item.ta,
            "problems": item.problems, "status": item.status, **hints(item, s.ctx)}


def make_handler(s: Session):
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
            if self.path not in ("/api/answer", "/api/check") or self.headers.get("X-Review") != "1":
                self._send(403, b"forbidden", "text/plain")
                return
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            with lock:
                item = s.current
                if self.path == "/api/check":
                    if item is None:
                        self._json({"problems": []})
                        return
                    ta = " ".join(body.get("ta", "").split())
                    self._json({"problems": tipnr.check(tipnr.Line(item.en, item.kind, item.about), ta, s.ctx) if ta else ["empty"]})
                    return
                action = body.get("action")
                try:
                    if action == "accept":
                        ta = s.accept(body.get("ta", ""))
                        msg = f"✓ written: {ta}"
                    elif action == "reject":
                        s.reject(body.get("ta", ""), body.get("reason", ""))
                        msg = "✗ rejected: the site shows the English; `translate tipnr submit --repair` asks again"
                    elif action == "skip":
                        s.skip()
                        msg = "→ skipped"
                    elif action == "undo":
                        back = s.undo()
                        msg = f"↶ restored: {back}" if back else "nothing to undo"
                    else:
                        raise ValueError(f"unknown action {action!r}")
                except ValueError as err:
                    self._json({"ok": False, "error": str(err)})
                    return
            self._json({"ok": True, "message": msg})

    return Handler


def serve(s: Session, port: int = 8767, open_browser: bool = True) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(s))
    server.daemon_threads = True
    url = f"http://127.0.0.1:{port}/"
    print(f"{len(s.items)} lines to review at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        c = s.counts
        print(f"\n{c['accepted']} accepted, {c['rejected']} rejected, {c['skipped']} skipped; "
              f"{len(s.items) - s.i} left in this list. Run `pnpm content` to build.")


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TIPNR review</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600&display=swap">
<style>
:root {
  --bg: #f7f6f3; --panel: #ffffff; --fg: #1d1d1b; --muted: #6b6a66; --line: #e3e1db;
  --accent: #1f5f8b; --accent-fg: #ffffff; --ok: #166534; --bad: #9f1239; --key: #efede8; --warn: #fde68a;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #141413; --panel: #1d1d1b; --fg: #ecebe7; --muted: #a09e98; --line: #34332f;
    --accent: #6fb3e0; --accent-fg: #0f1a22; --ok: #86efac; --bad: #fda4af; --key: #2a2926; --warn: #6b5300;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.55 system-ui, sans-serif; }
[lang=ta] { font-family: "Noto Sans Tamil", "Nirmala UI", "Latha", sans-serif; }
main { max-width: 900px; margin: 0 auto; padding: 16px; }
header { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
header h1 { font-size: 15px; margin: 0; font-weight: 600; }
.bar { flex: 1; min-width: 120px; height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--accent); }
.muted { color: var(--muted); font-size: 13px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px; margin-bottom: 12px; }
.en { font-size: 20px; font-weight: 600; margin: 4px 0 0; }
.badge { font-size: 12px; padding: 1px 8px; border-radius: 99px; background: var(--key); color: var(--muted); margin-left: 6px; font-weight: 400; }
ul.problems { margin: 10px 0 0; padding: 0; list-style: none; }
ul.problems li { padding: 4px 10px; border-left: 3px solid var(--bad); background: var(--bg); border-radius: 4px; margin-top: 4px; font-size: 14px; }
ul.problems li.ok { border-color: var(--ok); color: var(--ok); }
label { display: block; font-size: 12px; color: var(--muted); margin-top: 12px; }
textarea, input[type=text] { width: 100%; padding: 8px 10px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--bg); color: var(--fg); font: inherit; }
#ta { font-size: 18px; min-height: 4.5em; line-height: 1.7; }
.row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; align-items: center; }
button { padding: 8px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); color: var(--fg); cursor: pointer; font: inherit; }
button.primary { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }
button:disabled { opacity: .45; cursor: default; }
kbd { font: 12px ui-monospace, monospace; background: var(--key); border: 1px solid var(--line); border-radius: 4px; padding: 0 5px; }
#msg { min-height: 1.5em; font-size: 14px; margin-top: 8px; overflow-wrap: anywhere; }
#msg.ok { color: var(--ok); } #msg.err { color: var(--bad); }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 6px 8px; border-top: 1px solid var(--line); vertical-align: top; }
th { font-weight: 600; color: var(--muted); font-size: 12px; border-top: 0; }
.unrev { background: var(--warn); border-radius: 4px; padding: 0 6px; font-size: 12px; }
.help { font-size: 12px; color: var(--muted); line-height: 2; }
.done { text-align: center; padding: 40px 16px; }
@media (max-width: 600px) { main { padding: 12px; } .en { font-size: 18px; } }
</style>
</head>
<body>
<main>
  <header>
    <h1>TIPNR briefs and shorts · review</h1>
    <div class="bar"><i id="bar"></i></div>
    <span class="muted" id="counts"></span>
  </header>
  <div id="app"><div class="card">Loading…</div></div>
  <p class="help"><kbd>Ctrl</kbd>+<kbd>Enter</kbd> accept as shown · <kbd>e</kbd> edit the Tamil · <kbd>r</kbd> reject (with a reason) ·
    <kbd>s</kbd> skip · <kbd>u</kbd> undo. Accept writes the Tamil even when a check still objects; reject keeps the English on the site
    and sends the line, with your reason, to <code>translate tipnr submit --repair</code>.</p>
</main>
<script>
const app = document.getElementById('app');
let state = null, busy = false, lastMsg = null, checkTimer = null;
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const post = (path, body) => fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Review': '1' },
  body: JSON.stringify(body) }).then(r => r.json());

async function load() { state = await (await fetch('/api/state')).json(); render(); }

async function answer(action, extra = {}) {
  if (busy) return; busy = true;
  try {
    const res = await post('/api/answer', { action, ...extra });
    lastMsg = res.ok ? { ok: true, text: res.message } : { ok: false, text: res.error };
    await load();
  } finally { busy = false; }
}

const ta = () => document.getElementById('ta').value;
const accept = () => answer('accept', { ta: ta() });
function reject() {
  const reason = document.getElementById('reason');
  if (!reason.value.trim() && document.activeElement !== reason) { reason.focus(); return; }
  answer('reject', { ta: ta(), reason: reason.value });
}

function problemsHtml(list) {
  return list.length ? list.map(p => `<li>${esc(p)}</li>`).join('') : '<li class="ok">No problems with the Tamil as shown.</li>';
}

async function recheck() {
  const res = await post('/api/check', { ta: ta() });
  document.getElementById('now').innerHTML = problemsHtml(res.problems);
}

function render() {
  const c = state.counts || {};
  const doneN = (c.accepted || 0) + (c.rejected || 0) + (c.skipped || 0);
  document.getElementById('bar').style.width = `${state.total ? Math.min(100, 100 * doneN / state.total) : 100}%`;
  document.getElementById('counts').textContent =
    `${c.accepted || 0} accepted · ${c.rejected || 0} rejected · ${c.skipped || 0} skipped · ${state.total} in this session`;
  const msg = lastMsg ? `<div id="msg" class="${lastMsg.ok ? 'ok' : 'err'}">${esc(lastMsg.text)}</div>` : '<div id="msg"></div>';
  if (state.done) {
    app.innerHTML = `<div class="card done"><p>All lines in this session are done. Run <code>pnpm content</code> to build.</p>
      <div class="row" style="justify-content:center"><button id="undo" ${state.can_undo ? '' : 'disabled'}>Undo last <kbd>u</kbd></button></div>${msg}</div>`;
    const u = document.getElementById('undo'); if (u) u.onclick = () => answer('undo');
    return;
  }
  const names = state.names.map(n => `<tr><td>${esc(n.en)}</td><td lang="ta">${esc(n.ta)}</td>
      <td lang="ta" class="muted">${esc(n.forms.join(', '))}</td><td>${n.reviewed ? '' : '<span class="unrev">not reviewed</span>'}</td></tr>`).join('');
  const terms = state.terms.map(t => `<tr><td>${esc(t.en)}</td><td lang="ta">${esc(t.ta)}</td>
      <td lang="ta" class="muted">${t.avoid.length ? 'avoid ' + esc(t.avoid.join(', ')) : ''}</td><td></td></tr>`).join('');
  app.innerHTML = `
    <section class="card">
      <div class="muted">${state.pos} of ${state.total} · ${esc(state.kind)}${state.about.length ? ' about ' + esc(state.about.join(', ')) : ''}
        ${state.status !== 'flagged' ? `<span class="badge">${esc(state.status)}</span>` : ''}</div>
      <p class="en">${esc(state.en)}</p>
      ${state.problems.length ? `<label>What the checks found</label><ul class="problems">${problemsHtml(state.problems)}</ul>` : ''}
      <label for="ta">Tamil</label>
      <textarea id="ta" lang="ta" spellcheck="false">${esc(state.ta)}</textarea>
      <label>Checked again as you edit</label><ul class="problems" id="now"></ul>
      <label for="reason">Reason, if you reject (sent to Claude with --repair)</label>
      <input type="text" id="reason" autocomplete="off" placeholder="e.g. Arba is அர்பா, not Hebron">
      <div class="row">
        <button class="primary" id="accept">Accept <kbd>Ctrl</kbd>+<kbd>Enter</kbd></button>
        <button id="reject">Reject <kbd>r</kbd></button>
        <button id="skip">Skip <kbd>s</kbd></button>
        <button id="undo" ${state.can_undo ? '' : 'disabled'}>Undo <kbd>u</kbd></button>
      </div>
      ${msg}
    </section>
    ${names || terms ? `<section class="card"><table>
      <tr><th>English</th><th>Tamil given to Claude</th><th>Forms</th><th></th></tr>${names}${terms}</table>
      <p class="muted">Names come from names-ta.toml; a wrong one there is wrong here too: fix it with
      <code>translate verses NAME --accept LABEL</code>, then <code>translate tipnr recheck</code>.</p></section>` : ''}`;
  document.getElementById('accept').onclick = accept;
  document.getElementById('reject').onclick = reject;
  document.getElementById('skip').onclick = () => answer('skip');
  document.getElementById('undo').onclick = () => answer('undo');
  document.getElementById('ta').addEventListener('input', () => { clearTimeout(checkTimer); checkTimer = setTimeout(recheck, 250); });
  recheck();
}

document.addEventListener('keydown', e => {
  const typing = ['INPUT', 'TEXTAREA'].includes(e.target.tagName);
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && state && !state.done) { e.preventDefault(); return accept(); }
  if (typing) {
    if (e.key === 'Enter' && e.target.id === 'reason') { e.preventDefault(); reject(); }
    else if (e.key === 'Escape') e.target.blur();
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey || !state) return;
  if (e.key === 'u') return answer('undo');
  if (state.done) return;
  if (e.key === 'r') { e.preventDefault(); return reject(); }
  if (e.key === 's') return answer('skip');
  if (e.key === 'e') { e.preventDefault(); const t = document.getElementById('ta'); t.focus(); }
});

load();
</script>
</body>
</html>
"""
