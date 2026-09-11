"""Build the self-hosted web fonts (M1.18).

Downloads the TTFs from the Google Fonts repository (all OFL), instances
variable fonts at the two weights the site uses, subsets Tamil faces to the
characters that occur in the corpus (plus digits and punctuation), Latin
faces to Latin-1 + general punctuation, and writes woff2 files into
apps/web/static/fonts/. The outputs are committed; rerun after adding a text.

Faces (see docs/design.md, theme): Mukta Malar is the Tamil display and
scripture face; Noto Sans Tamil and Noto Serif Tamil are the alternatives
offered in settings; Noto Sans carries every Latin string.

    pip install --user fonttools brotli
    python scripts/subset-fonts.py
"""
import glob, io, os, sys, urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(ROOT, "data", "fonts-src")
OUT = os.path.join(ROOT, "apps", "web", "static", "fonts")
os.makedirs(SRC, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

GF = "https://github.com/google/fonts/raw/main/ofl/"
WEIGHTS = {"regular": 400, "semibold": 600}
FONTS = {
    # slug: (script, source). A variable source is one url; a static source
    # maps each weight name to its own file.
    "mukta-malar": ("tamil", {"regular": GF + "muktamalar/MuktaMalar-Regular.ttf", "semibold": GF + "muktamalar/MuktaMalar-SemiBold.ttf"}),
    "noto-sans-tamil": ("tamil", GF + "notosanstamil/NotoSansTamil%5Bwdth%2Cwght%5D.ttf"),
    "noto-serif-tamil": ("tamil", GF + "notoseriftamil/NotoSerifTamil%5Bwdth%2Cwght%5D.ttf"),
    "noto-sans": ("latin", GF + "notosans/NotoSans%5Bwdth%2Cwght%5D.ttf"),
}
# Faces no longer used; removed so stale files do not ship.
RETIRED = ["source-serif-4", "source-sans-3"]


def corpus_chars():
    chars = set()
    for f in glob.glob(os.path.join(ROOT, "data", "versions", "*", "*.usfm")):
        chars.update(open(f, encoding="utf-8-sig").read())
    # UI text and numerals in either script.
    chars.update("0123456789௦௧௨௩௪௫௬௭௮௯")
    chars.update("‹›‘’“”–—…·•₹")
    return chars


def download(name, url):
    path = os.path.join(SRC, name + ".ttf")
    if not os.path.exists(path):
        print("downloading", name)
        urllib.request.urlretrieve(url, path)
    return path


def subset_font(font: TTFont, unicodes, script, flavor="woff2") -> bytes:
    opts = subset.Options()
    opts.flavor = flavor
    if script == "tamil":
        opts.layout_features = ["*"]  # Tamil shaping needs every GSUB/GPOS feature
    # Latin keeps fontTools' default feature list (kern, liga, calt, ...).
    opts.notdef_outline = True
    opts.hinting = False  # static Mukta Malar ships TrueType instructions worth ~70 kB; browsers ignore them
    opts.drop_tables += ["DSIG"]
    subsetter = subset.Subsetter(opts)
    subsetter.populate(unicodes=unicodes)
    subsetter.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def instance(path, wght):
    font = TTFont(path)
    if "fvar" not in font:
        return font  # static face already at the requested weight
    axes = {a.axisTag: a for a in font["fvar"].axes}
    loc = {"wght": wght}
    if "wdth" in axes:
        loc["wdth"] = 100
    if "opsz" in axes:
        loc["opsz"] = 14
    return instancer.instantiateVariableFont(font, loc, inplace=False, updateFontNames=False)


def main():
    corpus = corpus_chars()
    tamil_unicodes = {ord(c) for c in corpus if 0x0B80 <= ord(c) <= 0x0BFF or c in "0123456789 .,;:!?()[]-–—‘’“”'\"…·•"}
    tamil_unicodes |= {0x200C, 0x200D, 0x25CC}  # ZWNJ/ZWJ, dotted circle
    latin_unicodes = set(range(0x20, 0x7F)) | set(range(0xA0, 0x100)) | set(range(0x2000, 0x2070)) | {0x20B9, 0x2122, 0x2190, 0x2192, 0x2039, 0x203A, 0x2713, 0x25C9, 0x2021, 0x270E}
    print(f"corpus chars: {len(corpus)}, tamil subset: {len(tamil_unicodes)}, latin subset: {len(latin_unicodes)}")

    for slug, (script, source) in FONTS.items():
        unicodes = tamil_unicodes if script == "tamil" else latin_unicodes
        for wname, wght in WEIGHTS.items():
            if isinstance(source, dict):
                path = download(f"{slug}-{wname}", source[wname])
            else:
                path = download(slug, source)
            data = subset_font(instance(path, wght), unicodes, script)
            out = os.path.join(OUT, f"{slug}-{wname}.woff2")
            with open(out, "wb") as fh:
                fh.write(data)
            print(f"{os.path.basename(out):40} {len(data)/1024:7.1f} kB")

    for slug in RETIRED:
        for wname in WEIGHTS:
            p = os.path.join(OUT, f"{slug}-{wname}.woff2")
            if os.path.exists(p):
                os.remove(p)
                print("removed", os.path.basename(p))


if __name__ == "__main__":
    main()
