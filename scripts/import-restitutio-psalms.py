#!/usr/bin/env python3
"""Draft data/psalms/psalms.toml from Sean Finnegan's "All 150 Psalms Categorized"
(restitutio.org, 18 Feb 2024).

The page has two tables: the 15 types with their psalms, and the same data by
psalm. Both are parsed and cross-checked; disagreements are printed and the
by-psalm table wins. Each psalm also gets its superscription authors and a
draft primary theme (see docs/feature_psalms_explorer.md §3).

The output is a one-time draft for review. Once edited by hand, psalms.toml is
the source of truth; this script refuses to overwrite it without --force.

  python scripts/import-restitutio-psalms.py              # fetch the page
  python scripts/import-restitutio-psalms.py page.html    # or read a saved copy
"""
import html
import re
import sys
import urllib.request
from pathlib import Path

URL = "https://restitutio.org/2024/02/18/all-150-psalms-categorized/"
OUT = Path(__file__).resolve().parent.parent / "data" / "psalms" / "psalms.toml"

# Restitutio type name (as written on the page, lower-cased) -> genre id.
GENRE = {
    "praise": "praise", "historical": "historical", "torah": "torah",
    "creation": "creation", "royal": "royal", "enthronement": "enthronement",
    "enthronment": "enthronement",  # spelled so for psalms 9 and 24
    "wisdom": "wisdom", "prophecy": "prophecy", "trust": "trust",
    "petition": "petition", "complaint": "complaint", "repentance": "repentance",
    "imprecatory": "imprecatory", "thanksgiving": "thanksgiving",
    "zion": "zion", "zion, pilgrimage": "zion",
}

# Genre -> theme, and the order in which a psalm with several genres picks its
# primary theme: the more specific theme wins.
THEME_OF = {
    "repentance": "repent", "royal": "royal", "zion": "zion",
    "torah": "wisdom", "wisdom": "wisdom", "historical": "wisdom",
    "thanksgiving": "thanks",
    "petition": "lament", "complaint": "lament", "imprecatory": "lament",
    "trust": "trust", "prophecy": "wisdom",
    "praise": "praise", "enthronement": "praise", "creation": "praise",
}
PRIORITY = ["repentance", "royal", "zion", "torah", "wisdom", "thanksgiving",
            "petition", "complaint", "imprecatory", "historical", "trust",
            "prophecy", "praise", "enthronement", "creation"]


def spans(*ranges):
    out = []
    for r in ranges:
        a, b = r if isinstance(r, tuple) else (r, r)
        out.extend(range(a, b + 1))
    return out


# Authors named in the Hebrew superscriptions ("of David", "of Asaph", ...).
AUTHORS = {
    "david": spans((3, 9), (11, 32), (34, 41), (51, 65), (68, 70), 86, 101, 103,
                   (108, 110), 122, 124, 131, 133, (138, 145)),
    "asaph": spans(50, (73, 83)),
    "korah": spans(42, (44, 49), 84, 85, 87, 88),
    "solomon": [72, 127],
    "moses": [90],
    "heman": [88],
    "ethan": [89],
}
# The New Testament names David for two untitled psalms.
NT_AUTHORS = {2: (["david"], "Acts 4:25"), 95: (["david"], "Hebrews 4:7")}


def text_of(page):
    i = page.find('<div class="entry-content')
    j = page.find("sharedaddy", i)
    t = page[i:j]
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", t, flags=re.S)
    return t


def rows(table_html):
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, flags=re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
        out.append(cells)
    return out


def labels(cell):
    """'royal, prophecy?' -> [('royal', False), ('prophecy', True)]"""
    out = []
    for part in re.split(r",\s*", cell.strip()):
        part = part.strip().lower()
        if not part:
            continue
        maybe = part.endswith("?")
        out.append((GENRE[part.rstrip("?").strip()], maybe))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if OUT.exists() and "--force" not in sys.argv:
        sys.exit(f"{OUT} exists and may hold reviewed edits; pass --force to overwrite")
    if args:
        page = Path(args[0]).read_text(encoding="utf-8")
    else:
        req = urllib.request.Request(URL, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0",
            "Accept": "text/html", "Accept-Language": "en-US,en;q=0.9"})
        page = urllib.request.urlopen(req).read().decode("utf-8")

    tables = re.findall(r"<table[^>]*>.*?</table>", text_of(page), flags=re.S)
    by_type, by_psalm = rows(tables[0]), rows(tables[1])

    # Table 1: number, type, description, psalms.
    listed = {}
    for cells in by_type:
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        g = GENRE[cells[1].strip().lower()]
        for tok in re.findall(r"\d+\??", cells[3]):
            listed.setdefault(int(tok.rstrip("?")), set()).add((g, tok.endswith("?")))

    # Table 2: psalm, types.
    psalms = {}
    for cells in by_psalm:
        if len(cells) >= 2 and cells[0].isdigit():
            psalms[int(cells[0])] = (cells[1], labels(cells[1]))
    assert sorted(psalms) == list(range(1, 151)), "by-psalm table is not 1..150"

    for n in range(1, 151):
        a = set(psalms[n][1])
        b = listed.get(n, set())
        if a != b:
            print(f"Psalm {n}: by-psalm {sorted(a)} vs by-type {sorted(b)}; keeping by-psalm",
                  file=sys.stderr)

    lines = [
        "# Classification of the 150 psalms for the Psalms explorer.",
        "# Design: docs/feature_psalms_explorer.md. One line per psalm:",
        "#",
        "#   theme      the one coloured theme the grid shows (taxonomy.toml [[theme]])",
        "#   genres     every type the psalm belongs to (taxonomy.toml [[genre]]);",
        "#              the Genre filter matches any of them",
        "#   maybe      types the source marked with \"?\"; shown nowhere until moved",
        "#              into genres or deleted",
        "#   authors    names in the Hebrew superscription (taxonomy.toml [[author]]);",
        "#              empty means anonymous",
        "#   nt         authors named for the psalm in the New Testament, with the reference",
        "#   review     delete once the line has been checked",
        "#",
        "# genres and maybe were imported from Sean Finnegan, \"All 150 Psalms",
        "# Categorized\", restitutio.org, 18 Feb 2024, by",
        "# scripts/import-restitutio-psalms.py; the trailing comment keeps the",
        "# original wording. theme was derived from genres and needs checking where a",
        "# psalm has more than one. Edit freely: this file, not the source page, is",
        "# now the source of truth.",
        "",
        "[psalms]",
    ]
    for n in range(1, 151):
        raw, labs = psalms[n]
        genres = [g for g, maybe in labs if not maybe]
        maybe = [g for g, m in labs if m]
        theme = THEME_OF[min(genres, key=PRIORITY.index)]
        authors = [a for a, ns in AUTHORS.items() if n in ns]
        q = lambda xs: "[" + ", ".join(f'"{x}"' for x in xs) + "]"
        fields = [f'theme = "{theme}"', f"genres = {q(genres)}"]
        if maybe:
            fields.append(f"maybe = {q(maybe)}")
        fields.append(f"authors = {q(authors)}")
        if n in NT_AUTHORS:
            who, ref = NT_AUTHORS[n]
            fields.append(f'nt = {{ authors = {q(who)}, ref = "{ref}" }}')
        fields.append("review = true")
        lines.append(f"{n} = {{ {', '.join(fields)} }}  # {raw}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
