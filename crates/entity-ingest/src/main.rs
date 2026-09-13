//! entity-ingest: biblical places for tamilscripture.com (M6).
//!
//! Usage:
//!   entity-ingest --books data/books.toml --entities data/entities \
//!                 --content apps/web/static/content [--draft-names] [--lenient]
//!
//! Reads `manifest.json` from the content directory for the build id and the
//! versions, and the chapter JSON of the Tamil versions for name alignment.
//! Output (under `{content}/{build}/`):
//!   entities/places.json                 index of every place
//!   entities/place/{id}.json             one place
//!   entities/mentions/{BOOK}/{ch}.json   verse id → place ids
//!   entities/journeys.json               journeys with resolved stops
//!   entities/geo/places.geojson          points for the explore map
//!   entities/geo/journeys.geojson        routes for the explore map
//!   entities/geo/base/*.geojson          Natural Earth outline layers (copied)
//!   entities/maps/{BOOK}/{ch}.svg        static chapter maps
//!   entities/maps/place/{id}.svg         static place maps
//!   entities/maps/journey/{id}.svg       static journey maps
//!   search/entities.csv                  id,type,slug,name_en,names_ta,alt_en,weight
//! `--draft-names` instead proposes Tamil forms into data/entities/names-ta.toml.

mod books;
mod corpus;
mod geo;
mod journeys;
mod names;
mod openbible;
mod svg;

use anyhow::{bail, Context, Result};
use books::Books;
use corpus::Corpus;
use names::{NameForm, NamesTa};
use openbible::Place;
use serde::Serialize;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

struct Args {
    books: PathBuf,
    entities: PathBuf,
    content: PathBuf,
    draft_names: bool,
    strict: bool,
}

fn parse_args() -> Result<Args> {
    let mut a = Args {
        books: PathBuf::from("data/books.toml"),
        entities: PathBuf::from("data/entities"),
        content: PathBuf::from("apps/web/static/content"),
        draft_names: false,
        strict: true,
    };
    let mut it = std::env::args().skip(1);
    while let Some(arg) = it.next() {
        match arg.as_str() {
            "--books" => a.books = it.next().context("--books needs a path")?.into(),
            "--entities" => a.entities = it.next().context("--entities needs a path")?.into(),
            "--content" => a.content = it.next().context("--content needs a path")?.into(),
            "--draft-names" => a.draft_names = true,
            "--lenient" => a.strict = false,
            "-h" | "--help" => {
                eprintln!("entity-ingest --books B --entities DIR --content DIR [--draft-names] [--lenient]");
                std::process::exit(0);
            }
            other => bail!("unknown argument {other}"),
        }
    }
    Ok(a)
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut bytes = serde_json::to_vec(value)?;
    bytes.push(b'\n');
    fs::write(path, bytes).with_context(|| format!("writing {}", path.display()))
}

fn write_text(path: &Path, text: &str) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(path, text).with_context(|| format!("writing {}", path.display()))
}

fn csv_field(s: &str) -> String {
    if s.contains(['"', ',', '\n', '\r']) {
        format!("\"{}\"", s.replace('"', "\"\""))
    } else {
        s.to_string()
    }
}

// ---- output shapes (mirrored in apps/web/src/lib/entities/types.ts) ----

#[derive(Serialize)]
struct NameTaOut {
    label: String,
    forms: Vec<String>,
    confidence: f32,
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    draft: bool,
}

#[derive(Serialize)]
struct GeoOut {
    lat: f64,
    lon: f64,
    precision: String,
}

#[derive(Serialize)]
struct PlaceOut<'a> {
    id: &'a str,
    #[serde(rename = "type")]
    kind: &'static str,
    name_en: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    qualifier: &'a Option<String>,
    #[serde(skip_serializing_if = "str::is_empty")]
    article: &'a str,
    #[serde(skip_serializing_if = "<[String]>::is_empty")]
    alt_en: &'a [String],
    names_ta: BTreeMap<String, NameTaOut>,
    place_type: &'a str,
    types: &'a [String],
    class: &'a str,
    geo: Option<GeoOut>,
    #[serde(skip_serializing_if = "Option::is_none")]
    modern: &'a Option<String>,
    verses: &'a [String],
    #[serde(skip_serializing_if = "Vec::is_empty")]
    journeys: Vec<String>,
    /// Nearby located places (within the place map's view), nearest first.
    #[serde(skip_serializing_if = "Vec::is_empty")]
    nearby: Vec<Value>,
    source: SourceOut,
}

#[derive(Serialize)]
struct SourceOut {
    openbible_id: String,
    url: String,
    licence: &'static str,
    attribution: &'static str,
}

#[derive(Serialize)]
struct IndexEntry<'a> {
    id: &'a str,
    name_en: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    qualifier: &'a Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    name_ta: Option<String>,
    place_type: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    lat: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    lon: Option<f64>,
    precision: &'a str,
    mentions: usize,
}

#[derive(Serialize)]
struct Index<'a> {
    build: &'a str,
    count: usize,
    places: Vec<IndexEntry<'a>>,
}

fn round5(v: f64) -> f64 {
    (v * 1e5).round() / 1e5
}

/// Tamil label for a place: the default Tamil version first, then any other.
fn label_ta(names: &NamesTa, name_en: &str, versions: &[String]) -> Option<String> {
    let per = names.get(name_en)?;
    for v in versions {
        if let Some(f) = per.get(v).filter(|f| f.display_ok()) {
            return Some(f.label.clone());
        }
    }
    per.values()
        .find(|f| f.display_ok())
        .map(|f| f.label.clone())
}

fn main() -> Result<()> {
    let args = parse_args()?;
    let books = Books::load(&args.books)?;

    // Manifest: build id and versions of the current content build.
    let manifest_path = args.content.join("manifest.json");
    let manifest: Value =
        serde_json::from_str(&fs::read_to_string(&manifest_path).with_context(|| {
            format!(
                "reading {} (run usfm-ingest first)",
                manifest_path.display()
            )
        })?)?;
    let build = manifest["build"]
        .as_str()
        .context("manifest.build")?
        .to_string();
    let build_dir = args.content.join(&build);
    let mut tamil_versions: Vec<String> = manifest["versions"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|v| v["lang"].as_str() == Some("ta"))
        .filter_map(|v| v["code"].as_str().map(String::from))
        .collect();
    // Default Tamil version first for labels.
    tamil_versions.sort_by_key(|v| if v == "IRVTAM" { 0 } else { 1 });

    let places = openbible::load(&args.entities.join("openbible-geo/ancient.jsonl"), &books)?;
    eprintln!(
        "places: {} ({} located)",
        places.len(),
        places.iter().filter(|p| p.lon.is_some()).count()
    );

    // Verses per English name (same-named places share Tamil forms).
    let mut verses_by_name: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for p in &places {
        verses_by_name
            .entry(p.name_en.clone())
            .or_default()
            .extend(p.verses.iter().cloned());
    }

    let corpora: Vec<Corpus> = tamil_versions
        .iter()
        .map(|v| Corpus::load(&build_dir, v, &books.list))
        .collect::<Result<_>>()?;
    for c in &corpora {
        eprintln!("corpus {}: {} verses", c.version, c.n_verses);
    }

    let names_path = args.entities.join("names-ta.toml");
    if args.draft_names {
        let mut names = names::load(&names_path)?;
        let (mut added, mut kept) = (0usize, 0usize);
        for (name, verses) in &verses_by_name {
            let verses: Vec<String> = verses.iter().cloned().collect();
            for c in &corpora {
                if names.get(name).and_then(|m| m.get(&c.version)).is_some() {
                    kept += 1;
                    continue;
                }
                if let Some(form) = names::draft_one(&verses, c) {
                    names
                        .entry(name.clone())
                        .or_default()
                        .insert(c.version.clone(), form);
                    added += 1;
                }
            }
        }
        names::save(&names_path, &names)?;
        let review = names
            .values()
            .flat_map(|m| m.values())
            .filter(|f| f.review)
            .count();
        eprintln!(
            "names-ta.toml: {added} drafted, {kept} kept, {review} marked review → {}",
            names_path.display()
        );
        return Ok(());
    }

    // ---- build ----
    let names = names::load(&names_path)?;
    if names.is_empty() {
        eprintln!(
            "warning: {} missing or empty; maps carry English labels only",
            names_path.display()
        );
    }
    let mut problems: Vec<String> = Vec::new();
    for (name, per) in &names {
        let Some(verses) = verses_by_name.get(name) else {
            problems.push(format!("{name}: not a place name in the OpenBible data"));
            continue;
        };
        let verses: Vec<String> = verses.iter().cloned().collect();
        for (version, form) in per {
            if let Some(c) = corpora.iter().find(|c| &c.version == version) {
                problems.extend(names::validate(name, form, &verses, c));
            }
        }
    }
    if !problems.is_empty() {
        for p in &problems {
            eprintln!("error: {p}");
        }
        if args.strict {
            bail!("{} name problems", problems.len());
        }
    }

    let out = build_dir.join("entities");
    let base = svg::Base {
        land: geo::load_layer(&args.entities.join("geo/base/land.geojson"))?,
        lakes: geo::load_layer(&args.entities.join("geo/base/lakes.geojson"))?,
        rivers: geo::load_layer(&args.entities.join("geo/base/rivers.geojson"))?,
    };
    for f in ["land", "lakes", "rivers", "LICENSE", "SOURCE.md"] {
        let name = if f.ends_with(".md") || f == "LICENSE" {
            f.to_string()
        } else {
            format!("{f}.geojson")
        };
        let src = args.entities.join("geo/base").join(&name);
        if src.exists() {
            fs::create_dir_all(out.join("geo/base"))?;
            fs::copy(&src, out.join("geo/base").join(&name))?;
        }
    }

    let by_id: BTreeMap<&str, &Place> = places.iter().map(|p| (p.id.as_str(), p)).collect();

    // Journeys resolve stops to places.
    let journeys_in = journeys::load(&args.entities.join("geo/journeys.toml"))?;
    let mut journeys_out: Vec<journeys::JourneyOut> = Vec::new();
    let mut journeys_by_place: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for j in &journeys_in {
        let mut stops = Vec::new();
        let mut bbox = geo::BBox::empty();
        for s in &j.stops {
            let Some(p) = by_id.get(s.place.as_str()) else {
                bail!("journey {}: unknown place {}", j.id, s.place)
            };
            let (Some(lon), Some(lat)) = (p.lon, p.lat) else {
                bail!("journey {}: place {} has no coordinates", j.id, s.place)
            };
            bbox.add([lon, lat]);
            journeys_by_place
                .entry(p.id.clone())
                .or_default()
                .push(j.id.clone());
            stops.push(journeys::StopOut {
                place: p.id.clone(),
                name_en: p.name_en.clone(),
                name_ta: label_ta(&names, &p.name_en, &tamil_versions),
                lon: round5(lon),
                lat: round5(lat),
                r#ref: s.r#ref.clone(),
                note_en: s.note_en.clone(),
                note_ta: s.note_ta.clone(),
            });
        }
        journeys_out.push(journeys::JourneyOut {
            id: j.id.clone(),
            name_en: j.name_en.clone(),
            name_ta: j.name_ta.clone(),
            period: j.period.clone(),
            summary_en: j.summary_en.clone(),
            summary_ta: j.summary_ta.clone(),
            passages: j.passages.clone(),
            stops,
            bbox: [
                round5(bbox.min_lon),
                round5(bbox.min_lat),
                round5(bbox.max_lon),
                round5(bbox.max_lat),
            ],
        });
    }
    for v in journeys_by_place.values_mut() {
        v.dedup();
    }
    write_json(&out.join("journeys.json"), &journeys_out)?;

    // Glossary (place types, precision, periods) in both languages, for the app.
    let glossary_path = args.entities.join("glossary-ta.toml");
    if glossary_path.exists() {
        let g: toml::Value = toml::from_str(&fs::read_to_string(&glossary_path)?)
            .context("parsing glossary-ta.toml")?;
        write_json(&out.join("glossary.json"), &g)?;
    }

    // Mentions per chapter: verse id → place ids, plus a summary of every
    // place named in the chapter so the reader panel needs no second fetch.
    let mut mentions: BTreeMap<(u32, u32), BTreeMap<String, Vec<String>>> = BTreeMap::new();
    let mut chapter_places: BTreeMap<(u32, u32), BTreeSet<String>> = BTreeMap::new();
    for p in &places {
        for v in &p.verses {
            let mut it = v.split('.');
            let (Some(code), Some(ch)) = (it.next(), it.next()) else {
                continue;
            };
            let Some(book) = books.by_code(code) else {
                continue;
            };
            let ch: u32 = ch.parse().unwrap_or(0);
            mentions
                .entry((book.order, ch))
                .or_default()
                .entry(v.clone())
                .or_default()
                .push(p.id.clone());
            chapter_places
                .entry((book.order, ch))
                .or_default()
                .insert(p.id.clone());
        }
    }
    for ((order, ch), m) in &mentions {
        let book = &books.list[(*order - 1) as usize];
        let mut entries: Vec<(&String, &Vec<String>)> = m.iter().collect();
        entries.sort_by_key(|(k, _)| {
            k.rsplit('.')
                .next()
                .and_then(|v| v.parse::<u32>().ok())
                .unwrap_or(0)
        });
        let verses: Vec<Value> = entries
            .iter()
            .map(|(k, v)| serde_json::json!({ "verse": k, "places": v }))
            .collect();
        let summary: BTreeMap<&str, Value> = chapter_places[&(*order, *ch)]
            .iter()
            .filter_map(|id| by_id.get(id.as_str()))
            .map(|p| {
                (
                    p.id.as_str(),
                    serde_json::json!({
                        "name_en": p.name_en, "qualifier": p.qualifier, "name_ta": label_ta(&names, &p.name_en, &tamil_versions),
                        "type": p.types.first().cloned().unwrap_or_default(), "precision": p.precision,
                        "lat": p.lat.map(round5), "lon": p.lon.map(round5), "mentions": p.verses.len()
                    }),
                )
            })
            .collect();
        write_json(
            &out.join("mentions")
                .join(&book.code)
                .join(format!("{ch}.json")),
            &serde_json::json!({ "book": book.code, "chapter": ch, "verses": verses, "places": summary, "map": !summary.values().all(|p| p["lat"].is_null()) }),
        )?;
    }

    // Place files and index.
    let mut index_entries = Vec::new();
    let mut csv = String::from("id,type,slug,name_en,names_ta,alt_en,weight\n");
    let located: Vec<&Place> = places.iter().filter(|p| p.lon.is_some()).collect();
    for p in &places {
        let names_ta: BTreeMap<String, NameTaOut> = names
            .get(&p.name_en)
            .map(|per| {
                per.iter()
                    .map(|(v, f): (&String, &NameForm)| {
                        (
                            v.clone(),
                            NameTaOut {
                                label: f.label.clone(),
                                forms: f.forms.clone(),
                                confidence: f.confidence,
                                draft: f.review,
                            },
                        )
                    })
                    .collect()
            })
            .unwrap_or_default();
        // Nearby places: within ~1.2° for the place map, nearest first, up to 12.
        let mut nearby: Vec<(f64, &str)> = Vec::new();
        if let (Some(lon), Some(lat)) = (p.lon, p.lat) {
            for q in &located {
                if q.id == p.id {
                    continue;
                }
                let d =
                    ((q.lon.unwrap() - lon) * lat.to_radians().cos()).hypot(q.lat.unwrap() - lat);
                if d < 1.2 {
                    nearby.push((d, q.id.as_str()));
                }
            }
            nearby.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap().then_with(|| a.1.cmp(b.1)));
            nearby.truncate(12);
        }
        let place_type = p.types.first().map(String::as_str).unwrap_or("place");
        let out_place = PlaceOut {
            id: &p.id,
            kind: "place",
            name_en: &p.name_en,
            qualifier: &p.qualifier,
            article: &p.article,
            alt_en: &p.alt_en,
            names_ta,
            place_type,
            types: &p.types,
            class: &p.class,
            geo: p.lon.map(|lon| GeoOut { lat: round5(p.lat.unwrap()), lon: round5(lon), precision: p.precision.clone() }),
            modern: &p.modern,
            verses: &p.verses,
            journeys: journeys_by_place.get(&p.id).cloned().unwrap_or_default(),
            nearby: nearby
                .iter()
                .filter_map(|(_, id)| by_id.get(id))
                .map(|q| serde_json::json!({ "id": q.id, "name_en": q.name_en, "qualifier": q.qualifier, "name_ta": label_ta(&names, &q.name_en, &tamil_versions) }))
                .collect(),
            source: SourceOut {
                openbible_id: p.ob_id.clone(),
                url: format!("https://www.openbible.info/geo/ancient/{}/{}", p.ob_id, p.id.trim_end_matches(|c: char| c.is_ascii_digit() || c == '-')),
                licence: "CC BY 4.0",
                attribution: "OpenBible.info Bible Geocoding, CC BY 4.0",
            },
        };
        write_json(
            &out.join("place").join(format!("{}.json", p.id)),
            &out_place,
        )?;
        let name_ta = label_ta(&names, &p.name_en, &tamil_versions);
        index_entries.push(IndexEntry {
            id: &p.id,
            name_en: &p.name_en,
            qualifier: &p.qualifier,
            name_ta: name_ta.clone(),
            place_type,
            lat: p.lat.map(round5),
            lon: p.lon.map(round5),
            precision: &p.precision,
            mentions: p.verses.len(),
        });
        let all_ta: BTreeSet<String> = names
            .get(&p.name_en)
            .map(|per| {
                per.values()
                    .flat_map(|f| std::iter::once(f.label.clone()).chain(f.forms.iter().cloned()))
                    .collect()
            })
            .unwrap_or_default();
        let weight = ((1 + p.verses.len()) as f64).ln();
        csv.push_str(&format!(
            "{},place,{},{},{},{},{:.3}\n",
            csv_field(&p.id),
            csv_field(&p.id),
            csv_field(&format!(
                "{}{}",
                p.name_en,
                p.qualifier
                    .as_ref()
                    .map(|q| format!(" {q}"))
                    .unwrap_or_default()
            )),
            csv_field(&all_ta.into_iter().collect::<Vec<_>>().join(" ")),
            csv_field(&p.alt_en.join(" ")),
            weight
        ));
    }
    write_json(
        &out.join("places.json"),
        &Index {
            build: &build,
            count: places.len(),
            places: index_entries,
        },
    )?;
    write_text(&build_dir.join("search/entities.csv"), &csv)?;

    // GeoJSON for the explore map.
    let feats: Vec<Value> = located
        .iter()
        .map(|p| {
            serde_json::json!({
                "type": "Feature",
                "properties": {
                    "id": p.id, "name_en": p.name_en, "name_ta": label_ta(&names, &p.name_en, &tamil_versions),
                    "type": p.types.first().cloned().unwrap_or_default(), "precision": p.precision, "mentions": p.verses.len()
                },
                "geometry": { "type": "Point", "coordinates": [round5(p.lon.unwrap()), round5(p.lat.unwrap())] }
            })
        })
        .collect();
    write_json(
        &out.join("geo/places.geojson"),
        &serde_json::json!({ "type": "FeatureCollection", "features": feats }),
    )?;
    let jfeats: Vec<Value> = journeys_out
        .iter()
        .map(|j| {
            serde_json::json!({
                "type": "Feature",
                "properties": { "id": j.id, "name_en": j.name_en, "name_ta": j.name_ta, "period": j.period },
                "geometry": { "type": "LineString", "coordinates": j.stops.iter().map(|s| [s.lon, s.lat]).collect::<Vec<_>>() }
            })
        })
        .collect();
    write_json(
        &out.join("geo/journeys.geojson"),
        &serde_json::json!({ "type": "FeatureCollection", "features": jfeats }),
    )?;

    // Static maps.
    let point_of = |p: &Place, emphasis: bool, number: Option<u32>| svg::MapPoint {
        id: p.id.clone(),
        lon: p.lon.unwrap(),
        lat: p.lat.unwrap(),
        label_en: p.name_en.clone(),
        label_ta: label_ta(&names, &p.name_en, &tamil_versions),
        href: format!("/place/{}", p.id),
        emphasis,
        weight: p.verses.len() as u32,
        number,
    };
    let mut n_maps = 0usize;
    for ((order, ch), ids) in &chapter_places {
        let book = &books.list[(*order - 1) as usize];
        let pts: Vec<svg::MapPoint> = ids
            .iter()
            .filter_map(|id| by_id.get(id.as_str()))
            .filter(|p| p.lon.is_some())
            .map(|p| point_of(p, false, None))
            .collect();
        if pts.is_empty() {
            continue;
        }
        let title = format!("{} {} · {} {}", book.name_ta, ch, book.name_en, ch);
        // Chapter maps are drawn at the size of the context panel so labels stay legible.
        let svg_text = svg::render(
            &base,
            &svg::MapSpec {
                title,
                points: &pts,
                route: None,
                w: 360.0,
                h: 225.0,
                min_span: 2.5,
                small: true,
            },
        );
        write_text(
            &out.join("maps").join(&book.code).join(format!("{ch}.svg")),
            &svg_text,
        )?;
        n_maps += 1;
    }
    for p in &located {
        let mut pts = vec![point_of(p, true, None)];
        let nearby: Vec<&Place> = {
            let mut v: Vec<(f64, &Place)> = located
                .iter()
                .filter(|q| q.id != p.id)
                .map(|q| {
                    (
                        ((q.lon.unwrap() - p.lon.unwrap()) * p.lat.unwrap().to_radians().cos())
                            .hypot(q.lat.unwrap() - p.lat.unwrap()),
                        *q,
                    )
                })
                .filter(|(d, _)| *d < 1.2)
                .collect();
            v.sort_by(|a, b| {
                a.0.partial_cmp(&b.0)
                    .unwrap()
                    .then_with(|| a.1.id.cmp(&b.1.id))
            });
            v.into_iter().take(12).map(|(_, q)| q).collect()
        };
        pts.extend(nearby.iter().map(|q| point_of(q, false, None)));
        let title = match label_ta(&names, &p.name_en, &tamil_versions) {
            Some(ta) => format!("{ta} · {}", p.name_en),
            None => p.name_en.clone(),
        };
        // Keep the place central: fit to it plus the nearest few, with a minimum span.
        let spec = svg::MapSpec {
            title,
            points: &pts,
            route: None,
            w: 800.0,
            h: 480.0,
            min_span: 2.0,
            small: false,
        };
        write_text(
            &out.join("maps/place").join(format!("{}.svg", p.id)),
            &svg::render(&base, &spec),
        )?;
        n_maps += 1;
    }
    for j in &journeys_out {
        let route: Vec<geo::Pt> = j.stops.iter().map(|s| [s.lon, s.lat]).collect();
        let mut seen = BTreeSet::new();
        let pts: Vec<svg::MapPoint> = j
            .stops
            .iter()
            .enumerate()
            .filter(|(_, s)| seen.insert(s.place.clone()))
            .map(|(i, s)| {
                let p = by_id[s.place.as_str()];
                point_of(p, true, Some(i as u32 + 1))
            })
            .collect();
        let spec = svg::MapSpec {
            title: format!("{} · {}", j.name_ta, j.name_en),
            points: &pts,
            route: Some(&route),
            w: 800.0,
            h: 520.0,
            min_span: 3.0,
            small: false,
        };
        write_text(
            &out.join("maps/journey").join(format!("{}.svg", j.id)),
            &svg::render(&base, &spec),
        )?;
        n_maps += 1;
    }

    eprintln!(
        "entities: {} places, {} chapters with mentions, {} journeys, {} maps → {}",
        places.len(),
        mentions.len(),
        journeys_out.len(),
        n_maps,
        out.display()
    );
    Ok(())
}
