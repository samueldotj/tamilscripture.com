//! OpenBible.info geocoding: `ancient.jsonl`, one JSON object per biblical
//! place. Only the fields the site needs are read: identity, English names,
//! the best identification's coordinates and type, and the verse list.
//! Geometry files derived from OpenStreetMap are ODbL and are not used.

use crate::books::Books;
use anyhow::{Context, Result};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

#[derive(Debug, Clone)]
pub struct Place {
    /// OpenBible id, e.g. `a69c1d4`.
    pub ob_id: String,
    /// Our slug, unique, e.g. `damascus`, `antioch-1`.
    pub id: String,
    /// English display name without the disambiguating number.
    pub name_en: String,
    /// "1", "2" … when several places share a name.
    pub qualifier: Option<String>,
    /// "the" when English wants an article (the Jordan).
    pub article: String,
    pub types: Vec<String>,
    pub class: String,
    pub lon: Option<f64>,
    pub lat: Option<f64>,
    /// point · area · approximate · unlocated
    pub precision: String,
    /// Best modern identification's name, if any.
    pub modern: Option<String>,
    /// Other English spellings across translations, most frequent first.
    pub alt_en: Vec<String>,
    /// Verse ids in our form `GEN.14.15`, canonical order, unique.
    pub verses: Vec<String>,
}

fn slugify(s: &str) -> String {
    let mut out = String::new();
    let mut dash = false;
    for c in s.chars() {
        if c.is_ascii_alphanumeric() {
            out.push(c.to_ascii_lowercase());
            dash = false;
        } else if !dash && !out.is_empty() {
            out.push('-');
            dash = true;
        }
    }
    out.trim_end_matches('-').to_string()
}

fn split_qualifier(friendly: &str) -> (String, Option<String>) {
    match friendly.rsplit_once(' ') {
        Some((name, n)) if !n.is_empty() && n.chars().all(|c| c.is_ascii_digit()) => (name.to_string(), Some(n.to_string())),
        _ => (friendly.to_string(), None),
    }
}

fn verse_id(books: &Books, osis: &str) -> Option<(u32, u32, u32, String)> {
    let mut parts = osis.split('.');
    let (b, c, v) = (parts.next()?, parts.next()?, parts.next()?);
    let book = books.by_openbible(b)?;
    let ch: u32 = c.parse().ok()?;
    // Verse may carry a letter suffix in rare cases (e.g. "5a"); keep digits.
    let digits: String = v.chars().take_while(|c| c.is_ascii_digit()).collect();
    let vn: u32 = digits.parse().ok()?;
    Some((book.order, ch, vn, format!("{}.{}.{}", book.code, ch, vn)))
}

pub fn load(path: &Path, books: &Books) -> Result<Vec<Place>> {
    let text = std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    let mut places = Vec::new();
    let mut seen_slugs: BTreeMap<String, usize> = BTreeMap::new();
    for (lineno, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let d: Value = serde_json::from_str(line).with_context(|| format!("ancient.jsonl line {}", lineno + 1))?;
        let ob_id = d["id"].as_str().unwrap_or_default().to_string();
        let friendly = d["friendly_id"].as_str().unwrap_or_default().to_string();
        let (name_en, qualifier) = split_qualifier(&friendly);
        let mut id = slugify(&friendly);
        if let Some(n) = seen_slugs.get_mut(&id) {
            *n += 1;
            id = format!("{id}-{}", ob_id);
        } else {
            seen_slugs.insert(id.clone(), 1);
        }
        let article = d["preceding_article"].as_str().unwrap_or_default().to_string();
        let types: Vec<String> = d["types"].as_array().map(|a| a.iter().filter_map(|t| t.as_str().map(String::from)).collect()).unwrap_or_default();

        let ident = d["identifications"].as_array().and_then(|a| a.first());
        let class = ident.and_then(|i| i["class"].as_str()).unwrap_or("").to_string();
        let id_source = ident.and_then(|i| i["id_source"].as_str()).unwrap_or("");
        let res = ident.and_then(|i| i["resolutions"].as_array()).and_then(|a| a.first());
        let mut lon = None;
        let mut lat = None;
        let mut lonlat_type = String::new();
        if let Some(r) = res {
            if let Some(ll) = r["lonlat"].as_str() {
                if let Some((a, b)) = ll.split_once(',') {
                    lon = a.trim().parse::<f64>().ok();
                    lat = b.trim().parse::<f64>().ok();
                }
            }
            lonlat_type = r["lonlat_type"].as_str().unwrap_or("").to_string();
        }
        let precision = if id_source == "special" || lon.is_none() {
            lon = None;
            lat = None;
            "unlocated"
        } else if types.iter().any(|t| t == "region" || t == "people group" || t == "natural area" || t == "mountain range") {
            "area"
        } else if lonlat_type == "point" {
            "point"
        } else {
            "approximate"
        }
        .to_string();

        // Best modern association by score.
        let mut modern: Option<(i64, String)> = None;
        if let Some(assoc) = d["modern_associations"].as_object() {
            for (_k, m) in assoc {
                let score = m["score"].as_i64().unwrap_or(0);
                let name = m["name"].as_str().unwrap_or("").to_string();
                if !name.is_empty() && modern.as_ref().is_none_or(|(s, _)| score > *s) {
                    modern = Some((score, name));
                }
            }
        }

        let mut alt: Vec<(i64, String)> = d["translation_name_counts"]
            .as_object()
            .map(|o| o.iter().map(|(k, v)| (v.as_i64().unwrap_or(0), k.clone())).collect())
            .unwrap_or_default();
        alt.sort_by(|a, b| b.0.cmp(&a.0).then_with(|| a.1.cmp(&b.1)));
        let alt_en: Vec<String> = alt.into_iter().map(|(_, n)| n).filter(|n| n != &name_en).take(6).collect();

        let mut verses: BTreeSet<(u32, u32, u32, String)> = BTreeSet::new();
        if let Some(vs) = d["verses"].as_array() {
            for v in vs {
                if let Some(osis) = v["osis"].as_str() {
                    if let Some(t) = verse_id(books, osis) {
                        verses.insert(t);
                    }
                }
            }
        } else if let Some(extra) = d["extra"].as_str() {
            if let Ok(e) = serde_json::from_str::<Value>(extra) {
                for osis in e["osises"].as_array().into_iter().flatten() {
                    if let Some(t) = osis.as_str().and_then(|s| verse_id(books, s)) {
                        verses.insert(t);
                    }
                }
            }
        }

        places.push(Place {
            ob_id,
            id,
            name_en,
            qualifier,
            article,
            types,
            class,
            lon,
            lat,
            precision,
            modern: modern.map(|(_, n)| n),
            alt_en,
            verses: verses.into_iter().map(|(_, _, _, id)| id).collect(),
        });
    }
    places.sort_by(|a, b| a.id.cmp(&b.id));
    Ok(places)
}
