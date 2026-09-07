"""Build the self-hosted web fonts (M1.18).

Downloads the variable TTFs from the Google Fonts repository (all OFL),
instances them at the two weights the site uses, subsets Tamil faces to the
characters that occur in the corpus (plus digits and punctuation), Latin
faces to Latin-1 + general punctuation, and writes woff2 files into
apps/web/static/fonts/. The outputs are committed; rerun after adding a text.

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
FONTS = {
    # name: (url, family slug, script)
    "NotoSerifTamil": (GF + "notoseriftamil/NotoSerifTamil%5Bwdth%2Cwght%5D.ttf", "noto-serif-tamil", "tamil"),
    "NotoSansTamil": (GF + "notosanstamil/NotoSansTamil%5Bwdth%2Cwght%5D.ttf", "noto-sans-tamil", "tamil"),
    "SourceSerif4": (GF + "sourceserif4/SourceSerif4%5Bopsz%2Cwght%5D.ttf", "source-serif-4", "latin"),
    "SourceSans3": (GF + "sourcesans3/SourceSans3%5Bwght%5D.ttf", "source-sans-3", "latin"),
}
WEIGHTS = {"regular": 400, "semibold": 600}


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
    opts.drop_tables += ["DSIG"]
    subsetter = subset.Subsetter(opts)
    subsetter.populate(unicodes=unicodes)
    subsetter.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def main():
    corpus = corpus_chars()
    tamil_unicodes = {ord(c) for c in corpus if 0x0B80 <= ord(c) <= 0x0BFF or c in "0123456789 .,;:!?()[]-–—‘’“”'\"…·•"}
    tamil_unicodes |= {0x200C, 0x200D, 0x25CC}  # ZWNJ/ZWJ, dotted circle
    latin_unicodes = set(range(0x20, 0x7F)) | set(range(0xA0, 0x100)) | set(range(0x2000, 0x2070)) | {0x20B9, 0x2122, 0x2190, 0x2192, 0x2039, 0x203A}
    print(f"corpus chars: {len(corpus)}, tamil subset: {len(tamil_unicodes)}, latin subset: {len(latin_unicodes)}")

    for name, (url, slug, script) in FONTS.items():
        path = download(name, url)
        unicodes = tamil_unicodes if script == "tamil" else latin_unicodes
        for wname, wght in WEIGHTS.items():
            font = TTFont(path)
            axes = {a.axisTag: a for a in font["fvar"].axes}
            loc = {"wght": wght}
            if "wdth" in axes:
                loc["wdth"] = 100
            if "opsz" in axes:
                loc["opsz"] = 14
            inst = instancer.instantiateVariableFont(font, loc, inplace=False, updateFontNames=False)
            data = subset_font(inst, unicodes, script)
            out = os.path.join(OUT, f"{slug}-{wname}.woff2")
            with open(out, "wb") as fh:
                fh.write(data)
            print(f"{os.path.basename(out):40} {len(data)/1024:7.1f} kB")


if __name__ == "__main__":
    main()
