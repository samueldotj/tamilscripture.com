# Cliopatria polity borders

| | |
|---|---|
| Publisher | Seshat Global History Databank. Cliopatria: a geospatial database of world-wide political entities from 3400 BCE to 2024 CE. |
| Licence | CC BY 4.0, the same as the rest of the atlas data, so this directory needs no separate treatment. |
| Citation | Bennett, J.S. et al. (2025), *Cliopatria — A geospatial database of world-wide political entities from 3400BCE to 2024CE*, Scientific Data 12. https://doi.org/10.1038/s41597-025-04516-9 |
| Repository | https://github.com/Seshat-Global-History-Databank/cliopatria, `cliopatria.geojson.zip` on `main` |
| Source hash | `cliopatria.geojson.zip` sha256 d01ae3a20d358cc5… (44 MB; unzips to `cliopatria_polities_only.geojson`, 158 MB, 13,765 rows worldwide) |
| Downloaded | 2026-09-14 |
| Files | `polities.geojson` — the only file here, built by `scripts/build-polities.py` |
| Processing | Rows of `Type = POLITY` whose years overlap 4000 BCE – AD 800 and whose geometry meets lon −12…68, lat 5…62 (Europe, the Middle East and Egypt; the eastern edge is the Indus). Clipped to that box, simplified to 0.1° (about 11 km) and rounded to 2 decimals. Rows named in brackets, and the `RELATION` rows, are dropped: they repeat the territory of the polities they are composed of. A kingdom with less than 15% of its territory on our side of the Indus is dropped as well, judged over its whole life rather than row by row: the Maurya and Gupta empires reach Gandhara and the Tang held the Tarim basin, but drawing those slivers would label the edge of the map with an empire that is not on it. 1,773 rows, 236 polities, 234 distinct years at which something changes. The range runs to AD 800 because the timeline also carries the early church, whose last council is in 787. |
| Attribution shown | Regions: Cliopatria (Seshat Global History Databank), CC BY 4.0 |
| Tamil names | `../polities-ta.toml`, seeded from Wikidata labels by `build-polities.py --fetch-ta` and merged in as `name_ta`. Every one is `draft = true` until a maintainer confirms it; drafts also carry `draft_ta` in the GeoJSON. Wikidata is not always right — it offered the Byzantine Empire for the Roman Empire and the Indus script for the Indus Valley Civilisation — and where the Tamil Bible has a spelling (Assyria, Elam, Phoenicia, Babylonia, Israel, Judah) that spelling is used instead. |
| Notes | Cliopatria starts at 3400 BCE, so the first six centuries the atlas offers are empty. Its polygons are drawn against modern coastlines, as ours are: the Nile delta, the head of the Persian Gulf and the Dead Sea have all moved since. Border uncertainty is not encoded; the authors ask that the maps be read as one reading of a polity's territory, not the reading. |
