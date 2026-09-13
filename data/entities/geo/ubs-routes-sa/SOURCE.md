# UBS Bible Routes (Project MARBLE)

| | |
|---|---|
| Publisher | United Bible Societies, © 2023; routes drawn for UBS by Dr. Leen Ritmeyer as part of Project MARBLE |
| Licence | CC BY-SA 4.0 (LICENSE.md). ShareAlike: this directory stays separate from the CC BY journey data, and every map or GeoJSON we publish that contains these lines is itself CC BY-SA 4.0 and says so in its credit. |
| Repository | https://github.com/ubsicap/ubs-open-license, folder `ubs-bible-routes`, commit on `main` as of 13 Sep 2026 |
| Files | `GeoJsonRoutes/*.geojson` (179 files, 508 LineStrings in WGS84 lon/lat; one file per story route, a few with several legs), `metadata.csv` (story number, title, map image name), `README-upstream.md`. The SVG renderings upstream are not stored. |
| Hash | `042. Exodus Route1.geojson` sha256 d68d124ffbe2071c…, `205. Paul's Voyage to Rome.geojson` 8638311bfdacaf0c… |
| Downloaded | 2026-09-13 |
| Attribution shown | Routes: UBS Project MARBLE (Leen Ritmeyer), © United Bible Societies 2023, CC BY-SA 4.0 |
| Notes | A journey in `../journeys.toml` references files by name in `routes = [...]`; the build reads every LineString in those files, draws them instead of straight legs between stops, and marks the journey `route_source = "ubs"`. `061. Battle against Gibeon.geojson` contains a null feature, which the loader skips. Stops, names and passages remain ours (CC BY), resolved to OpenBible places. |
