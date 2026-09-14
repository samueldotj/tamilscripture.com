# Natural Earth base map

| | |
|---|---|
| Source | Natural Earth physical vectors, GeoJSON conversions from https://github.com/nvkelso/natural-earth-vector: 1:10m (`geojson/ne_10m_land.geojson`, `ne_10m_coastline.geojson`, `ne_10m_lakes.geojson`, `ne_10m_rivers_lake_centerlines.geojson`) and 1:110m (`ne_110m_land.geojson`) for the world silhouette |
| Licence | Public domain (see LICENSE) |
| Downloaded | 2026-09-12 |
| Processing | Clipped to lon 10–52, lat 22–46 and simplified by `scripts/build-basemap.py`; lakes with scalerank ≤ 6 and rivers with scalerank ≤ 7 kept. `world` is the whole globe from the 1:110m land, simplified to 0.05°, clipped to the Web Mercator band (±85.05°) and with the bounding box cut out of it, so it fills in around the detailed layers when the explore map zooms out |
| Files | `land.geojson`, `coast.geojson`, `lakes.geojson`, `rivers.geojson`, `world.geojson` |
