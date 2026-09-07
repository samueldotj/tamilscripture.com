"""Summarise a Lighthouse HTML report (as uploaded by lhci) from a URL or file:
category scores, CLS with culprits, and failing accessibility audits.

    python scripts/lh-report.py <report-url-or-path>
"""
import json, re, sys, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
src = sys.argv[1]
html = urllib.request.urlopen(src).read().decode("utf-8") if src.startswith("http") else open(src, encoding="utf-8").read()
m = re.search(r"window\.__LIGHTHOUSE_JSON__ = (\{.*?\});</script>", html, re.S)
d = json.loads(m.group(1))
print("URL:", d["finalDisplayedUrl"])
print("scores:", {k: round((v["score"] or 0) * 100) for k, v in d["categories"].items()})
a = d["audits"]
print("LCP %.0f ms  CLS %.3f  TBT %.0f ms  bytes %.0f kB" % (
    a["largest-contentful-paint"]["numericValue"], a["cumulative-layout-shift"]["numericValue"],
    a["total-blocking-time"]["numericValue"], a["total-byte-weight"]["numericValue"] / 1024))
for item in a.get("layout-shifts", {}).get("details", {}).get("items", [])[:5]:
    print("  shift %.3f %s" % (item.get("score", 0), (item.get("node") or {}).get("snippet", "")[:100]))
    for c in item.get("subItems", {}).get("items", [])[:3]:
        print("      cause:", c.get("cause", ""), (c.get("extra") or {}).get("value", "") if isinstance(c.get("extra"), dict) else "")
refs = {r["id"] for r in d["categories"]["accessibility"]["auditRefs"]}
for aid in sorted(refs):
    au = a.get(aid)
    if au and au.get("score") is not None and au["score"] < 1:
        print("  a11y FAIL:", aid, "-", au["title"][:80])
        for it in au.get("details", {}).get("items", [])[:3]:
            print("      ", (it.get("node") or {}).get("snippet", "")[:110])
