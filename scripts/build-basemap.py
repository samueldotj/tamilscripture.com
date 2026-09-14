"""Clip and simplify Natural Earth 1:10m physical layers to the biblical world.

Natural Earth is public domain (https://www.naturalearthdata.com/about/terms-of-use/).
Downloads the GeoJSON conversions from github.com/nvkelso/natural-earth-vector,
clips to the bounding box below, simplifies, and writes small GeoJSON files
under data/entities/geo/base/ for the static map renderer and the explore map.

`world` is the exception: the whole globe, simplified hard, so the explore map
can zoom out past the biblical world instead of stopping at the clip. It is a
silhouette only — no rivers, no lakes, no labels out there.

    pip install --user shapely
    python scripts/build-basemap.py
"""
import json, os, sys, urllib.request
from shapely.geometry import shape, box, mapping

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(ROOT, "data", "basemap-src")
OUT = os.path.join(ROOT, "data", "entities", "geo", "base")
os.makedirs(SRC, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

# Rome to the Persian Gulf, Upper Egypt to the Black Sea.
BBOX = box(10.0, 22.0, 52.0, 46.0)
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
LAYERS = {
    # out name: (source file, simplify tolerance in degrees, property filter)
    "land": ("ne_10m_land.geojson", 0.008, None),
    # The coastline as its own lines: stroking the clipped `land` polygon would
    # draw the bounding box itself as if it were shore.
    "coast": ("ne_10m_coastline.geojson", 0.008, None),
    "lakes": ("ne_10m_lakes.geojson", 0.005, lambda p: p.get("scalerank", 9) <= 6),
    "rivers": ("ne_10m_rivers_lake_centerlines.geojson", 0.01, lambda p: p.get("scalerank", 9) <= 7),
}
# Whole-world silhouette, from the 1:110m land instead of the 1:10m: at the
# zooms it is drawn for, that is already more detail than a pixel can hold, and
# it keeps the file under 80 kB. Specks below MIN_AREA (square degrees) go.
WORLD = ("ne_110m_land.geojson", 0.05, 0.05)
# Web Mercator sends the poles to infinity, and Antarctica in the source runs
# to -90: a tile of that never finishes, and the map never fires `load`.
MERCATOR = box(-180.0, -85.05, 180.0, 85.05)


def fetch(name):
    path = os.path.join(SRC, name)
    if not os.path.exists(path):
        print("downloading", name)
        urllib.request.urlretrieve(NE + name, path)
    return path


def rnd(coords, dp=4):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], dp), round(coords[1], dp)]
    return [rnd(c, dp) for c in coords]


def write(out, feats):
    fc = {"type": "FeatureCollection", "features": feats}
    path = os.path.join(OUT, out + ".geojson")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"{out:8} {len(feats):5} features {os.path.getsize(path)/1024:8.1f} kB")


def main():
    for out, (src, tol, keep) in LAYERS.items():
        data = json.load(open(fetch(src), encoding="utf-8"))
        feats = []
        for f in data["features"]:
            if keep and not keep(f.get("properties", {})):
                continue
            g = shape(f["geometry"])
            if not g.intersects(BBOX):
                continue
            g = g.intersection(BBOX).simplify(tol, preserve_topology=True)
            if g.is_empty:
                continue
            props = {}
            if out in ("rivers", "lakes"):
                props["name"] = f["properties"].get("name") or ""
            gm = mapping(g)
            gm["coordinates"] = rnd(gm["coordinates"]) if gm["type"] != "GeometryCollection" else gm["coordinates"]
            feats.append({"type": "Feature", "properties": props, "geometry": gm})
        write(out, feats)

    src, tol, min_area = WORLD
    data = json.load(open(fetch(src), encoding="utf-8"))
    feats = []
    for f in data["features"]:
        g = shape(f["geometry"]).simplify(tol, preserve_topology=True)
        if not g.is_empty:
            # Everything outside BBOX only: inside it the 1:10m `land` is drawn,
            # and two coastlines 5 km apart would ghost against each other.
            g = g.intersection(MERCATOR).difference(BBOX)
        if g.is_empty or g.area < min_area:
            continue
        gm = mapping(g)
        gm["coordinates"] = rnd(gm["coordinates"], 2)
        feats.append({"type": "Feature", "properties": {}, "geometry": gm})
    write("world", feats)


if __name__ == "__main__":
    main()
