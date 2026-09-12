# Natural Earth base map

| | |
|---|---|
| Source | Natural Earth 1:10m physical vectors, GeoJSON conversions from https://github.com/nvkelso/natural-earth-vector (`geojson/ne_10m_land.geojson`, `ne_10m_lakes.geojson`, `ne_10m_rivers_lake_centerlines.geojson`) |
| Licence | Public domain (see LICENSE) |
| Downloaded | 2026-09-12 |
| Processing | Clipped to lon 10–52, lat 22–46 and simplified by `scripts/build-basemap.py`; lakes with scalerank ≤ 6 and rivers with scalerank ≤ 7 kept |
| Files | `land.geojson`, `lakes.geojson`, `rivers.geojson` |
