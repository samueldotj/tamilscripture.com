"""Clip the Cliopatria polity borders to the atlas region and era.

Cliopatria (Seshat Global History Databank) is CC BY 4.0: worldwide political
entities from 3400 BCE, each row carrying the years it applies to. See
https://github.com/Seshat-Global-History-Databank/cliopatria and the paper at
https://doi.org/10.1038/s41597-025-04516-9.

One row per polity per period, so the explore map loads a single file and
filters it by year in the browser — no request per step of the timeline.

    pip install --user shapely
    python scripts/build-polities.py              # build polities.geojson
    python scripts/build-polities.py --fetch-ta   # refresh the Tamil drafts

`--fetch-ta` asks Wikidata for a Tamil label for every polity and writes
data/entities/geo/polities-ta.toml. Those are drafts: Wikidata labels are not
always the name a reader wants (it returned the Indus *script* for the Indus
Valley Civilisation), so they are marked `draft = true` until a maintainer
confirms them, the same as the Tamil place names.
"""
import json, os, re, sys, time, unicodedata, urllib.parse, urllib.request, zipfile

sys.stdout.reconfigure(encoding="utf-8")
from shapely.geometry import box, mapping, shape

ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(ROOT, "data", "polities-src")
OUT = os.path.join(ROOT, "data", "entities", "geo", "polities")
TA_PATH = os.path.join(ROOT, "data", "entities", "geo", "polities-ta.toml")

ZIP_URL = "https://raw.githubusercontent.com/Seshat-Global-History-Databank/cliopatria/main/cliopatria.geojson.zip"
ZIP_NAME = "cliopatria.geojson.zip"
MEMBER = "cliopatria_polities_only.geojson"

# Europe, the Middle East, Egypt and India — the ground the atlas covers, wider
# than the biblical world the base map is clipped to.
REGION = box(-12.0, 5.0, 92.0, 62.0)
# 4000 BCE is the ask; Cliopatria itself starts at 3400 BCE.
FROM_YEAR, TO_YEAR = -4000, 350
# 0.05° is about 5 km: empire outlines, not coastlines.
TOLERANCE, DP = 0.05, 2

WIKIDATA = "https://www.wikidata.org/w/api.php"
UA = "tamilscripture-atlas/0.1 (https://www.tamilscripture.com)"


def fetch_zip():
    os.makedirs(SRC, exist_ok=True)
    path = os.path.join(SRC, ZIP_NAME)
    if not os.path.exists(path):
        print("downloading", ZIP_NAME, "(44 MB)")
        urllib.request.urlretrieve(ZIP_URL, path)
    return path


def slug(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


def rnd(coords, dp=DP):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], dp), round(coords[1], dp)]
    return [rnd(c, dp) for c in coords]


def rows():
    """Cliopatria rows inside the region and era, oldest first."""
    with zipfile.ZipFile(fetch_zip()).open(MEMBER) as fh:
        data = json.load(fh)
    out = []
    for f in data["features"]:
        p = f["properties"]
        fy, ty = p.get("FromYear"), p.get("ToYear")
        # RELATION rows, and the bracketed composites, repeat the territory of
        # the polities they are made of; drawing both would double every fill.
        if p.get("Type") != "POLITY" or p.get("Name", "").startswith("("):
            continue
        if fy is None or ty is None or ty < FROM_YEAR or fy > TO_YEAR or not f.get("geometry"):
            continue
        g = shape(f["geometry"])
        if not g.intersects(REGION):
            continue
        out.append((p, g))
    out.sort(key=lambda r: (r[0]["FromYear"], r[0]["Name"]))
    return out


def read_ta():
    """polities-ta.toml → id: (label, draft). Missing file means no Tamil yet."""
    if not os.path.exists(TA_PATH):
        return {}
    import tomllib

    with open(TA_PATH, "rb") as fh:
        d = tomllib.load(fh)
    return {k: (v.get("ta", ""), bool(v.get("draft"))) for k, v in d.get("polity", {}).items()}


def fetch_ta(names):
    """Ask Wikidata for a Tamil label for each polity, 50 ids at a time."""
    by_q = {}
    qs = sorted({q for _, q in names.values() if q})
    for i in range(0, len(qs), 50):
        batch = qs[i : i + 50]
        url = f"{WIKIDATA}?action=wbgetentities&props=labels&languages=ta&format=json&ids=" + urllib.parse.quote("|".join(batch))
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as fh:
            ents = json.load(fh).get("entities", {})
        for q, e in ents.items():
            label = e.get("labels", {}).get("ta", {}).get("value")
            if label:
                by_q[q] = label
        print(f"  wikidata {min(i + 50, len(qs))}/{len(qs)}")
        time.sleep(0.2)

    existing = read_ta()
    lines = [
        "# Tamil names for the polities drawn on the atlas timeline, keyed by the",
        "# id in geo/polities/polities.geojson. Seeded from Wikidata labels by",
        "# `python scripts/build-polities.py --fetch-ta`; `draft = true` means no",
        "# one has checked it yet. Clear `draft` once a maintainer confirms it, and",
        "# edit `ta` freely — the build takes this file as the authority.",
        "# Licence: CC BY 4.0 (tamilscripture.com contributors); Wikidata labels are CC0.",
        "",
    ]
    kept = 0
    for pid in sorted(names):
        name_en, q = names[pid]
        label, draft = existing.get(pid, ("", True))
        # A label a maintainer has confirmed is never overwritten from Wikidata.
        if draft:
            label = by_q.get(q, label)
        if not label:
            continue
        kept += 1
        esc = label.replace('"', '\\"')
        flag = ", draft = true" if draft else ""
        lines.append(f'{pid} = {{ ta = "{esc}"{flag} }}  # {name_en}')
    body = "[polity]\n" + "\n".join(lines[7:]) + "\n"
    with open(TA_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines[:7]) + "\n" + body)
    print(f"{kept}/{len(names)} polities have a Tamil name → {os.path.relpath(TA_PATH, ROOT)}")


def build():
    ta = read_ta()
    feats, names, years = [], {}, set()
    for p, g in rows():
        pid = slug(p["Name"])
        names[pid] = (p["Name"], p.get("Wikidata") or "")
        g = g.intersection(REGION).simplify(TOLERANCE, preserve_topology=True)
        if g.is_empty:
            continue
        gm = mapping(g)
        if gm["type"] != "GeometryCollection":
            gm["coordinates"] = rnd(gm["coordinates"])
        label_ta, draft = ta.get(pid, ("", False))
        # Where to hang the name, and how wide the polity is, so the map can
        # label only the ones with room for it. representative_point is inside
        # the polygon even when the centroid is not (Egypt along the Nile).
        rp = g.representative_point()
        x0, y0, x1, y1 = g.bounds
        props = {
            "id": pid,
            "name_en": p["Name"],
            "from": p["FromYear"],
            "to": p["ToYear"],
            "lon": round(rp.x, 2),
            "lat": round(rp.y, 2),
            "span": round(max(x1 - x0, y1 - y0), 2),
            "wikipedia": p.get("Wikipedia") or "",
            "wikidata": p.get("Wikidata") or "",
        }
        if label_ta:
            props["name_ta"] = label_ta
            if draft:
                props["draft_ta"] = True
        feats.append({"type": "Feature", "properties": props, "geometry": gm})
        years.add(max(p["FromYear"], FROM_YEAR))
        if p["ToYear"] < TO_YEAR:
            years.add(p["ToYear"] + 1)

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "polities.geojson")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"type": "FeatureCollection", "features": feats}, fh, ensure_ascii=False, separators=(",", ":"))
    with_ta = sum(1 for f in feats if f["properties"].get("name_ta"))
    print(f"polities {len(feats):5} rows · {len(names)} polities ({with_ta} with Tamil) · "
          f"{len(years)} steps · {os.path.getsize(path) / 1024:.0f} kB")
    return names


if __name__ == "__main__":
    names = build()
    if "--fetch-ta" in sys.argv:
        fetch_ta(names)
        build()
