"""Resolve the early-church roster against Wikidata into church.json.

`data/entities/church/roster.toml` says who is on the list, which city each
belongs to and how they are grouped — the editorial part. This script asks
Wikidata (CC0) for everything datable: the years a father lived, the year and
place of a council, the coordinates of a city the biblical gazetteer does not
carry, and a Tamil label where one exists. Nothing here is typed from memory.

    python scripts/build-church.py

Writes data/entities/church/church.json, which is committed and passed through
the content build. Re-run it to refresh from Wikidata; the Tamil names in
church-ta.toml are kept, so a name a maintainer has confirmed is never lost.
"""
import io, json, os, re, sys, time, tomllib, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(__file__), "..")
DIR = os.path.join(ROOT, "data", "entities", "church")
ROSTER = os.path.join(DIR, "roster.toml")
TA_PATH = os.path.join(DIR, "church-ta.toml")
OUT = os.path.join(DIR, "church.json")
PLACES_TA = os.path.join(ROOT, "data", "entities", "geo")

API = "https://www.wikidata.org/w/api.php"
UA = {"User-Agent": "tamilscripture-atlas/0.1 (https://www.tamilscripture.com)"}


def entities(ids):
    """Wikidata id → labels, claims and the English Wikipedia title."""
    out = {}
    ids = [i for i in dict.fromkeys(ids) if i]
    for i in range(0, len(ids), 40):
        batch = ids[i : i + 40]
        url = (f"{API}?action=wbgetentities&ids={urllib.parse.quote('|'.join(batch))}"
               "&props=labels|claims|sitelinks&languages=en|ta&sitefilter=enwiki&format=json")
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as fh:
            out.update(json.load(fh).get("entities", {}))
        time.sleep(0.2)
    return out


def claim_ids(e, prop):
    return [s["mainsnak"]["datavalue"]["value"]["id"]
            for s in e.get("claims", {}).get(prop, [])
            if s["mainsnak"].get("datavalue")]


def claim_year(e, prop):
    """The year of the first dated claim, negative for BCE."""
    for s in e.get("claims", {}).get(prop, []):
        v = s["mainsnak"].get("datavalue", {}).get("value")
        if isinstance(v, dict) and "time" in v:
            m = re.match(r"([+-])(\d+)-", v["time"])
            if m:
                return int(m.group(2)) * (-1 if m.group(1) == "-" else 1)
    return None


def coord(e):
    for s in e.get("claims", {}).get("P625", []):
        v = s["mainsnak"].get("datavalue", {}).get("value")
        if v:
            return round(v["latitude"], 5), round(v["longitude"], 5)
    return None


def label(e, lang):
    return e.get("labels", {}).get(lang, {}).get("value")


def wiki(e):
    return (e.get("sitelinks", {}).get("enwiki", {}) or {}).get("title")


def read_ta():
    if not os.path.exists(TA_PATH):
        return {}
    with open(TA_PATH, "rb") as fh:
        d = tomllib.load(fh)
    # [name.father] / [name.council] / [name.site] → "father.augustine" → (ta, draft)
    out = {}
    for kind, entries in d.get("name", {}).items():
        for key, v in entries.items():
            out[f"{kind}.{key}"] = (v.get("ta", ""), bool(v.get("draft")))
    return out


def write_ta(names, existing):
    """names: id → (english, tamil from wikidata). Confirmed entries are kept."""
    lines = [
        "# Tamil names for the early church: the fathers, the councils and the",
        "# cities this dataset adds. Seeded from Wikidata labels by",
        "# `python scripts/build-church.py`; `draft = true` means no one has checked",
        "# it yet. Clear `draft` once a maintainer confirms it, and edit `ta` freely —",
        "# the build takes this file as the authority.",
        "# Licence: CC BY 4.0 (tamilscripture.com contributors); Wikidata labels are CC0.",
        "",
    ]
    kept = 0
    for kind in ("father", "council", "site"):
        section = []
        for key in sorted(k for k in names if k.startswith(kind + ".")):
            name_en, from_wd = names[key]
            ta, draft = existing.get(key, ("", True))
            if draft:
                ta = from_wd or ta
            if not ta:
                continue
            kept += 1
            flag = ", draft = true" if draft else ""
            section.append(f'{key.split(".", 1)[1]} = {{ ta = "{ta}"{flag} }}  # {name_en}')
        if section:
            lines.append(f"[name.{kind}]")
            lines.extend(section)
            lines.append("")
    io.open(TA_PATH, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return kept


def main():
    with open(ROSTER, "rb") as fh:
        roster = tomllib.load(fh)

    ids = [s["wikidata"] for s in roster["site"]]
    ids += [f["wikidata"] for f in roster["father"]]
    ids += [c.get("wikidata", "") for c in roster["council"]]
    ent = entities(ids)
    # A father's city comes from his work location when the roster leaves it
    # open, so the anchor is sourced rather than guessed.
    extra = [q for f in roster["father"] if not f.get("place")
             for q in (claim_ids(ent.get(f["wikidata"], {}), "P937") or claim_ids(ent.get(f["wikidata"], {}), "P20"))[:1]]
    ent.update(entities(extra))

    ta_existing = read_ta()
    ta_seed = {}

    sites = {}
    for s in roster["site"]:
        e = ent.get(s["wikidata"], {})
        c = coord(e)
        if not c:
            print("  no coordinates for site", s["id"])
            continue
        # Several of these items are the modern city, which is the only way to
        # get coordinates; the ancient name is then given in the roster, and
        # the modern one is kept to show beside it.
        name_en = s.get("name") or label(e, "en")
        sites[s["id"]] = {"id": s["id"], "name_en": name_en, "lat": c[0], "lon": c[1],
                          "wikidata": s["wikidata"], "wikipedia": wiki(e)}
        if s.get("name") and label(e, "en") != name_en:
            sites[s["id"]]["modern"] = label(e, "en")
        # Seed Tamil from Wikidata only when the label is for the same place.
        ta_seed[f"site.{s['id']}"] = (name_en, None if s.get("name") else label(e, "ta"))

    fathers = []
    for f in roster["father"]:
        e = ent.get(f["wikidata"], {})
        place, anchor = f.get("place"), None
        if not place:
            for q in (claim_ids(e, "P937") or claim_ids(e, "P20"))[:1]:
                pe = ent.get(q, {})
                c = coord(pe)
                if c:
                    anchor = {"name_en": label(pe, "en"), "lat": c[0], "lon": c[1], "wikidata": q}
        born, died = claim_year(e, "P569"), claim_year(e, "P570")
        # Wikidata carries several claims for these dates and the first is not
        # always the best: Clement of Rome comes back born 100, died 99. When
        # they contradict each other, only the death year is kept.
        if born is not None and died is not None and born >= died:
            born = None
        fathers.append({"id": f["id"], "name_en": label(e, "en"), "tradition": f["tradition"],
                        "role": f["role"], "place": place or None, "anchor": anchor,
                        "born": born, "died": died,
                        "wikidata": f["wikidata"], "wikipedia": wiki(e)})
        ta_seed[f"father.{f['id']}"] = (label(e, "en"), label(e, "ta"))

    councils = []
    for c in roster["council"]:
        e = ent.get(c.get("wikidata", ""), {})
        # A council with no Wikidata item is named in the roster.
        councils.append({"id": c["id"], "name_en": c.get("name") or label(e, "en") or c["id"],
                         "year": c["year"], "place": c["place"], "kind": c["kind"],
                         "wikidata": c.get("wikidata") or None, "wikipedia": wiki(e)})
        ta_seed[f"council.{c['id']}"] = (councils[-1]["name_en"], label(e, "ta"))

    kept = write_ta(ta_seed, ta_existing)
    ta = read_ta()

    def ta_of(key):
        v = ta.get(key)
        return {"name_ta": v[0], "draft_ta": v[1]} if v and v[0] else {}

    for s in sites.values():
        s.update(ta_of(f"site.{s['id']}"))
    for f in fathers:
        f.update(ta_of(f"father.{f['id']}"))
    for c in councils:
        c.update(ta_of(f"council.{c['id']}"))

    doc = {"sites": list(sites.values()), "fathers": fathers, "councils": councils,
           "sees": [dict(s) for s in roster["see"]]}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    dated = sum(1 for f in fathers if f["born"] or f["died"])
    print(f"church {len(sites)} sites · {len(fathers)} fathers ({dated} dated) · "
          f"{len(councils)} councils · {len(doc['sees'])} sees · {kept} Tamil names")


if __name__ == "__main__":
    main()
