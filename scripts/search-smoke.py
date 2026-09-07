"""Smoke-test search against the live database and the deployed site.
Sends UTF-8 JSON bodies (Windows shells mangle Tamil in command-line args).

    python scripts/search-smoke.py [site-origin]
"""
import json, sys, time, urllib.request, urllib.parse

sys.stdout.reconfigure(encoding="utf-8")
SUPABASE = "https://zytgmnqmrvgspjdokajp.supabase.co"
KEY = "sb_publishable_9kbp5Fkm29ZBkhPxzSkhsg_6yK_SJV7"
SITE = sys.argv[1] if len(sys.argv) > 1 else "https://tamilscripturecom.vercel.app"


def rpc(name, body):
    req = urllib.request.Request(
        f"{SUPABASE}/rest/v1/rpc/{name}",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"apikey": KEY, "authorization": f"Bearer {KEY}", "content-type": "application/json; charset=utf-8"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8")), time.time() - t0
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode("utf-8")[:200]}, time.time() - t0


def show(title, res, dt):
    print(f"== {title} [{dt*1000:.0f} ms]")
    if isinstance(res, dict):
        print("  ", res)
        return
    total = res[0]["total"] if res else 0
    print(f"   rows {len(res)} total {total}")
    for r in res[:3]:
        print(f"   {r['verse_id']:12} {r['version']:7} {r['rank']:.3f} {r['text'][:70]}")


print("tamil_norm:", rpc("tamil_norm", {"t": "அன்பு தேவன் அன்பினால்"})[0])
cases = [
    ("அன்பு IRVTAM", {"q": "அன்பு", "versions": ["IRVTAM"], "exact": False}),
    ("misspelt அண்பு", {"q": "அண்பு", "versions": ["IRVTAM"], "exact": False}),
    ("தேவன் அன்பு IRVTAM+TCV", {"q": "தேவன் அன்பு", "versions": ["IRVTAM", "TCV"], "exact": False}),
    ("exact நித்திய ஜீவன்", {"q": "நித்திய ஜீவன்", "versions": ["IRVTAM"], "exact": True}),
    ("typo நித்தியஜீவனெ (fuzzy)", {"q": "நித்தியஜீவனெ", "versions": ["IRVTAM"], "exact": False}),
    ("love BSB", {"q": "love", "versions": ["BSB"], "exact": False}),
    ("exact 'God so loved' BSB", {"q": "God so loved", "versions": ["BSB"], "exact": True}),
    ("all versions அன்பு", {"q": "அன்பு", "versions": ["IRVTAM", "TCV", "BSB", "WEB", "KJV"], "exact": False}),
]
for title, body in cases:
    body = {**body, "lim": 5, "off": 0}
    res, dt = rpc("search_verses", body)
    show(title, res, dt)

print()
print("== site API ==")
for q, v in [("அன்பு", "IRVTAM"), ('"நித்திய ஜீவன்"', "IRVTAM"), ("love", "BSB")]:
    url = f"{SITE}/api/search?" + urllib.parse.urlencode({"q": q, "v": v})
    t0 = time.time()
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
        print(f"   {q:22} {v:7} total {d['total']:6} took {d['took_ms']:4} ms  [{(time.time()-t0)*1000:.0f} ms]  first {d['hits'][0]['verse_id'] if d['hits'] else '-'}")
    except Exception as e:
        print(f"   {q:22} {v:7} ERROR {e}")
