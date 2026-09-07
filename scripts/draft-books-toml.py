"""Draft data/books.toml from the USFM headers of the source versions.

Run once to produce the initial file, then maintain data/books.toml by hand.
Tamil names come from IRVTAM (\\h) and abbreviations from the \\toc2/\\toc3
lines of IRVTAM and TCV. English names come from BSB. English abbreviations
and slugs are a curated list below. OpenBible abbreviations are verified
against data/xrefs/cross_references.txt.
"""
import glob, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(__file__), "..", "data")

# code, testament, slug, alternate slugs, English abbreviations, OpenBible abbreviation
CANON = [
    ("GEN", "OT", "genesis", ["gen", "ge", "gn"], ["Gen", "Ge", "Gn"], "Gen"),
    ("EXO", "OT", "exodus", ["exo", "ex", "exod"], ["Exo", "Ex", "Exod"], "Exod"),
    ("LEV", "OT", "leviticus", ["lev", "le", "lv"], ["Lev", "Le", "Lv"], "Lev"),
    ("NUM", "OT", "numbers", ["num", "nu", "nm", "nb"], ["Num", "Nu", "Nm", "Nb"], "Num"),
    ("DEU", "OT", "deuteronomy", ["deu", "deut", "dt", "de"], ["Deu", "Deut", "Dt", "De"], "Deut"),
    ("JOS", "OT", "joshua", ["jos", "josh", "jsh"], ["Jos", "Josh", "Jsh"], "Josh"),
    ("JDG", "OT", "judges", ["jdg", "judg", "jg", "jgs"], ["Jdg", "Judg", "Jg", "Jgs"], "Judg"),
    ("RUT", "OT", "ruth", ["rut", "ru", "rth"], ["Rut", "Ru", "Rth"], "Ruth"),
    ("1SA", "OT", "1-samuel", ["1sa", "1sam", "1sm", "1s"], ["1Sa", "1Sam", "1Sm", "1S"], "1Sam"),
    ("2SA", "OT", "2-samuel", ["2sa", "2sam", "2sm", "2s"], ["2Sa", "2Sam", "2Sm", "2S"], "2Sam"),
    ("1KI", "OT", "1-kings", ["1ki", "1kgs", "1kg", "1k"], ["1Ki", "1Kgs", "1Kg", "1K"], "1Kgs"),
    ("2KI", "OT", "2-kings", ["2ki", "2kgs", "2kg", "2k"], ["2Ki", "2Kgs", "2Kg", "2K"], "2Kgs"),
    ("1CH", "OT", "1-chronicles", ["1ch", "1chr", "1chron"], ["1Ch", "1Chr", "1Chron"], "1Chr"),
    ("2CH", "OT", "2-chronicles", ["2ch", "2chr", "2chron"], ["2Ch", "2Chr", "2Chron"], "2Chr"),
    ("EZR", "OT", "ezra", ["ezr", "ezra"], ["Ezr", "Ezra"], "Ezra"),
    ("NEH", "OT", "nehemiah", ["neh", "ne"], ["Neh", "Ne"], "Neh"),
    ("EST", "OT", "esther", ["est", "esth", "es"], ["Est", "Esth", "Es"], "Esth"),
    ("JOB", "OT", "job", ["job", "jb"], ["Job", "Jb"], "Job"),
    ("PSA", "OT", "psalms", ["psa", "ps", "psalm", "pss", "psm"], ["Psa", "Ps", "Psalm", "Pss", "Psm"], "Ps"),
    ("PRO", "OT", "proverbs", ["pro", "prov", "pr", "prv"], ["Pro", "Prov", "Pr", "Prv"], "Prov"),
    ("ECC", "OT", "ecclesiastes", ["ecc", "eccl", "ec", "qoh"], ["Ecc", "Eccl", "Ec", "Qoh"], "Eccl"),
    ("SNG", "OT", "song-of-songs", ["sng", "song", "sos", "ss", "song-of-solomon", "canticles"], ["Sng", "Song", "SoS", "SS", "Cant"], "Song"),
    ("ISA", "OT", "isaiah", ["isa", "is"], ["Isa", "Is"], "Isa"),
    ("JER", "OT", "jeremiah", ["jer", "je", "jr"], ["Jer", "Je", "Jr"], "Jer"),
    ("LAM", "OT", "lamentations", ["lam", "la"], ["Lam", "La"], "Lam"),
    ("EZK", "OT", "ezekiel", ["ezk", "ezek", "eze"], ["Ezk", "Ezek", "Eze"], "Ezek"),
    ("DAN", "OT", "daniel", ["dan", "da", "dn"], ["Dan", "Da", "Dn"], "Dan"),
    ("HOS", "OT", "hosea", ["hos", "ho"], ["Hos", "Ho"], "Hos"),
    ("JOL", "OT", "joel", ["jol", "joel", "jl"], ["Jol", "Joel", "Jl"], "Joel"),
    ("AMO", "OT", "amos", ["amo", "amos", "am"], ["Amo", "Amos", "Am"], "Amos"),
    ("OBA", "OT", "obadiah", ["oba", "obad", "ob"], ["Oba", "Obad", "Ob"], "Obad"),
    ("JON", "OT", "jonah", ["jon", "jonah", "jnh"], ["Jon", "Jonah", "Jnh"], "Jonah"),
    ("MIC", "OT", "micah", ["mic", "mc"], ["Mic", "Mc"], "Mic"),
    ("NAM", "OT", "nahum", ["nam", "nah", "na"], ["Nam", "Nah", "Na"], "Nah"),
    ("HAB", "OT", "habakkuk", ["hab", "hb"], ["Hab", "Hb"], "Hab"),
    ("ZEP", "OT", "zephaniah", ["zep", "zeph", "zp"], ["Zep", "Zeph", "Zp"], "Zeph"),
    ("HAG", "OT", "haggai", ["hag", "hg"], ["Hag", "Hg"], "Hag"),
    ("ZEC", "OT", "zechariah", ["zec", "zech", "zc"], ["Zec", "Zech", "Zc"], "Zech"),
    ("MAL", "OT", "malachi", ["mal", "ml"], ["Mal", "Ml"], "Mal"),
    ("MAT", "NT", "matthew", ["mat", "matt", "mt"], ["Mat", "Matt", "Mt"], "Matt"),
    ("MRK", "NT", "mark", ["mrk", "mark", "mk", "mr"], ["Mrk", "Mark", "Mk", "Mr"], "Mark"),
    ("LUK", "NT", "luke", ["luk", "luke", "lk"], ["Luk", "Luke", "Lk"], "Luke"),
    ("JHN", "NT", "john", ["jhn", "john", "jn", "joh"], ["Jhn", "John", "Jn", "Joh"], "John"),
    ("ACT", "NT", "acts", ["act", "acts", "ac"], ["Act", "Acts", "Ac"], "Acts"),
    ("ROM", "NT", "romans", ["rom", "ro", "rm"], ["Rom", "Ro", "Rm"], "Rom"),
    ("1CO", "NT", "1-corinthians", ["1co", "1cor", "1c"], ["1Co", "1Cor", "1C"], "1Cor"),
    ("2CO", "NT", "2-corinthians", ["2co", "2cor", "2c"], ["2Co", "2Cor", "2C"], "2Cor"),
    ("GAL", "NT", "galatians", ["gal", "ga"], ["Gal", "Ga"], "Gal"),
    ("EPH", "NT", "ephesians", ["eph", "ep"], ["Eph", "Ep"], "Eph"),
    ("PHP", "NT", "philippians", ["php", "phil", "pp"], ["Php", "Phil", "Pp"], "Phil"),
    ("COL", "NT", "colossians", ["col", "co"], ["Col", "Co"], "Col"),
    ("1TH", "NT", "1-thessalonians", ["1th", "1thess", "1thes", "1ths"], ["1Th", "1Thess", "1Thes", "1Ths"], "1Thess"),
    ("2TH", "NT", "2-thessalonians", ["2th", "2thess", "2thes", "2ths"], ["2Th", "2Thess", "2Thes", "2Ths"], "2Thess"),
    ("1TI", "NT", "1-timothy", ["1ti", "1tim", "1tm"], ["1Ti", "1Tim", "1Tm"], "1Tim"),
    ("2TI", "NT", "2-timothy", ["2ti", "2tim", "2tm"], ["2Ti", "2Tim", "2Tm"], "2Tim"),
    ("TIT", "NT", "titus", ["tit", "ti"], ["Tit", "Ti"], "Titus"),
    ("PHM", "NT", "philemon", ["phm", "phlm", "philem", "pm"], ["Phm", "Phlm", "Philem", "Pm"], "Phlm"),
    ("HEB", "NT", "hebrews", ["heb", "he"], ["Heb", "He"], "Heb"),
    ("JAS", "NT", "james", ["jas", "jm", "jam"], ["Jas", "Jm", "Jam"], "Jas"),
    ("1PE", "NT", "1-peter", ["1pe", "1pet", "1pt", "1p"], ["1Pe", "1Pet", "1Pt", "1P"], "1Pet"),
    ("2PE", "NT", "2-peter", ["2pe", "2pet", "2pt", "2p"], ["2Pe", "2Pet", "2Pt", "2P"], "2Pet"),
    ("1JN", "NT", "1-john", ["1jn", "1john", "1jo", "1j"], ["1Jn", "1John", "1Jo", "1J"], "1John"),
    ("2JN", "NT", "2-john", ["2jn", "2john", "2jo", "2j"], ["2Jn", "2John", "2Jo", "2J"], "2John"),
    ("3JN", "NT", "3-john", ["3jn", "3john", "3jo", "3j"], ["3Jn", "3John", "3Jo", "3J"], "3John"),
    ("JUD", "NT", "jude", ["jud", "jude", "jd"], ["Jud", "Jude", "Jd"], "Jude"),
    ("REV", "NT", "revelation", ["rev", "re", "rv", "apocalypse"], ["Rev", "Re", "Rv"], "Rev"),
]


def headers(version):
    out = {}
    for f in glob.glob(os.path.join(ROOT, "versions", version, "*.usfm")):
        t = open(f, encoding="utf-8-sig").read()
        m = re.search(r"\\id (\w{3})", t)
        if not m:
            continue
        d = {}
        for tag in ("h", "toc1", "toc2", "toc3"):
            mm = re.search(r"\\" + tag + r" ([^\n]*)", t)
            d[tag] = mm.group(1).strip() if mm else ""
        d["chapters"] = len(re.findall(r"\\c \d+", t))
        out[m.group(1)] = d
    return out


def toml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def toml_list(xs):
    return "[" + ", ".join(toml_str(x) for x in xs) + "]"


irv, tcv, bsb = headers("irvtam"), headers("tcv"), headers("bsb")

# Verify OpenBible abbreviations against the cross-reference file.
xref_books = set()
with open(os.path.join(ROOT, "xrefs", "cross_references.txt"), encoding="utf-8") as fh:
    next(fh)
    for line in fh:
        a, b, *_ = line.rstrip("\n").split("\t")
        for ref in (a, b):
            for part in ref.split("-"):
                xref_books.add(part.split(".")[0])
canon_ob = {c[5] for c in CANON}
missing = xref_books - canon_ob
extra = canon_ob - xref_books
if missing or extra:
    print("OpenBible abbreviation mismatch:", "missing", sorted(missing), "unused", sorted(extra), file=sys.stderr)
    sys.exit(1)

lines = [
    "# Book table for tamilscripture.com. One entry per book, canonical order.",
    "#",
    "# code      USFM/Paratext book id, used in verse ids (JHN.3.16) and file names",
    "# slug      canonical URL segment; slugs are alternates that redirect to it",
    "# abbr_*    accepted in the reference box and search, matched case-insensitively;",
    "#           a trailing dot is always optional",
    "# name_ta   IRVTAM heading; alias_ta holds other spellings (TCV) that must also match",
    "# openbible book abbreviation in data/xrefs/cross_references.txt",
    "#",
    "# Drafted by scripts/draft-books-toml.py from the USFM headers; maintained by hand.",
    "",
]
for order, (code, testament, slug, slugs, abbr_en, openbible) in enumerate(CANON, 1):
    i, t, b = irv[code], tcv[code], bsb[code]
    if not (i["chapters"] == t["chapters"] == b["chapters"]):
        print("chapter count mismatch", code, file=sys.stderr)
        sys.exit(1)
    name_ta = i["h"]
    alias_ta = []
    for alt in (t["h"], t["toc2"], i["toc1"]):
        if alt and alt != name_ta and alt not in alias_ta:
            alias_ta.append(alt)
    abbr_ta = []
    for a in (i["toc2"], i["toc3"], t["toc3"], t["toc2"]):
        a = a.rstrip(".").strip()
        if a and a != name_ta and a not in alias_ta and a not in abbr_ta:
            abbr_ta.append(a)
    lines += [
        "[[book]]",
        f"code = {toml_str(code)}",
        f"order = {order}",
        f"testament = {toml_str(testament)}",
        f"chapters = {i['chapters']}",
        f"slug = {toml_str(slug)}",
        f"slugs = {toml_list(slugs)}",
        f"name_en = {toml_str(b['h'])}",
        f"abbr_en = {toml_list(abbr_en)}",
        f"name_ta = {toml_str(name_ta)}",
        f"alias_ta = {toml_list(alias_ta)}",
        f"abbr_ta = {toml_list(abbr_ta)}",
        f"openbible = {toml_str(openbible)}",
        "",
    ]

out = os.path.join(ROOT, "books.toml")
with open(out, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines))
print(f"wrote {out} with {len(CANON)} books; xref book ids verified ({len(xref_books)})")
