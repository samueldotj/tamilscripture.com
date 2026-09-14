//! The early church: fathers, the councils that wrote the creeds, and the sees.
//!
//! `data/entities/church/church.json` is built by `scripts/build-church.py`,
//! which resolves the curated roster against Wikidata. This module only joins
//! it to the place gazetteer: an entry names either a place in
//! `entities/places.json`, when scripture names the city, or one of the sites
//! the church data carries of its own. Anything that cannot be located is
//! reported and dropped, so nothing lands on the map at (0, 0).

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

#[derive(Debug, Deserialize)]
pub struct Church {
    pub sites: Vec<Site>,
    pub fathers: Vec<Father>,
    pub councils: Vec<Council>,
    pub sees: Vec<See>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Site {
    pub id: String,
    pub name_en: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name_ta: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub draft_ta: Option<bool>,
    /// The city that stands on the site now, when the two names differ.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub modern: Option<String>,
    pub lat: f64,
    pub lon: f64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub wikidata: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub wikipedia: Option<String>,
}

/// A father's own coordinates, when the roster left his city open and Wikidata
/// supplied a work location instead.
#[derive(Debug, Clone, Deserialize)]
pub struct Anchor {
    pub name_en: String,
    pub lat: f64,
    pub lon: f64,
}

#[derive(Debug, Deserialize)]
pub struct Father {
    pub id: String,
    pub name_en: String,
    #[serde(default)]
    pub name_ta: Option<String>,
    #[serde(default)]
    pub draft_ta: Option<bool>,
    pub tradition: String,
    pub role: String,
    #[serde(default)]
    pub place: Option<String>,
    #[serde(default)]
    pub anchor: Option<Anchor>,
    #[serde(default)]
    pub born: Option<i32>,
    #[serde(default)]
    pub died: Option<i32>,
    #[serde(default)]
    pub wikipedia: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct Council {
    pub id: String,
    pub name_en: String,
    #[serde(default)]
    pub name_ta: Option<String>,
    #[serde(default)]
    pub draft_ta: Option<bool>,
    pub year: i32,
    pub place: String,
    /// "ecumenical" for the seven, "apostolic" for Jerusalem, else "council".
    pub kind: String,
    #[serde(default)]
    pub wikipedia: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct See {
    pub id: String,
    pub place: String,
    pub rank: String,
}

/// An entry with its place resolved: what the app and the map both read.
#[derive(Debug, Serialize)]
pub struct Entry {
    pub id: String,
    /// "father", "council" or "see".
    #[serde(rename = "type")]
    pub kind: String,
    pub name_en: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name_ta: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub draft_ta: Option<bool>,
    /// The place id when the city is in the gazetteer, else the site id.
    pub place: String,
    pub place_name_en: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub place_name_ta: Option<String>,
    pub lat: f64,
    pub lon: f64,
    /// True when `place` is an id in places.json and so has a page of its own.
    pub place_linked: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tradition: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub role: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub rank: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub born: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub died: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub year: Option<i32>,
    /// "kind" on the wire: `kind` above is the entry type.
    #[serde(rename = "kind", skip_serializing_if = "Option::is_none")]
    pub kind_of_council: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub wikipedia: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct ChurchOut {
    pub sites: Vec<Site>,
    pub entries: Vec<Entry>,
}

pub fn load(path: &Path) -> Result<Option<Church>> {
    if !path.exists() {
        return Ok(None);
    }
    let text = fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    Ok(Some(
        serde_json::from_str(&text).with_context(|| format!("parsing {}", path.display()))?,
    ))
}

/// Where a place id points: the gazetteer first, then the church's own sites.
pub struct Gazetteer<'a> {
    /// place id → (name_en, name_ta, lat, lon)
    pub places: BTreeMap<&'a str, (&'a str, Option<&'a str>, f64, f64)>,
}

impl Church {
    /// Join every entry to a place. `problems` collects what could not be found.
    pub fn resolve(&self, gaz: &Gazetteer, problems: &mut Vec<String>) -> ChurchOut {
        let sites: BTreeMap<&str, &Site> = self.sites.iter().map(|s| (s.id.as_str(), s)).collect();
        let locate = |id: &str| -> Option<(String, Option<String>, f64, f64, bool)> {
            if let Some((en, ta, lat, lon)) = gaz.places.get(id) {
                return Some((en.to_string(), ta.map(str::to_string), *lat, *lon, true));
            }
            sites
                .get(id)
                .map(|s| (s.name_en.clone(), s.name_ta.clone(), s.lat, s.lon, false))
        };

        let mut entries: Vec<Entry> = Vec::new();
        for f in &self.fathers {
            let placed = f.place.as_deref().and_then(locate).or_else(|| {
                f.anchor
                    .as_ref()
                    .map(|a| (a.name_en.clone(), None, a.lat, a.lon, false))
            });
            let Some((pen, pta, lat, lon, linked)) = placed else {
                problems.push(format!("church: no place for father {}", f.id));
                continue;
            };
            entries.push(Entry {
                id: f.id.clone(),
                kind: "father".into(),
                name_en: f.name_en.clone(),
                name_ta: f.name_ta.clone(),
                draft_ta: f.draft_ta,
                place: f.place.clone().unwrap_or_else(|| pen.clone()),
                place_name_en: pen,
                place_name_ta: pta,
                lat,
                lon,
                place_linked: linked && f.place.is_some(),
                tradition: Some(f.tradition.clone()),
                role: Some(f.role.clone()),
                rank: None,
                born: f.born,
                died: f.died,
                year: None,
                kind_of_council: None,
                wikipedia: f.wikipedia.clone(),
            });
        }
        for c in &self.councils {
            let Some((pen, pta, lat, lon, linked)) = locate(&c.place) else {
                problems.push(format!(
                    "church: unknown place {} for council {}",
                    c.place, c.id
                ));
                continue;
            };
            entries.push(Entry {
                id: c.id.clone(),
                kind: "council".into(),
                name_en: c.name_en.clone(),
                name_ta: c.name_ta.clone(),
                draft_ta: c.draft_ta,
                place: c.place.clone(),
                place_name_en: pen,
                place_name_ta: pta,
                lat,
                lon,
                place_linked: linked,
                tradition: None,
                role: None,
                rank: None,
                born: None,
                died: None,
                year: Some(c.year),
                kind_of_council: Some(c.kind.clone()),
                wikipedia: c.wikipedia.clone(),
            });
        }
        for s in &self.sees {
            let Some((pen, pta, lat, lon, linked)) = locate(&s.place) else {
                problems.push(format!(
                    "church: unknown place {} for see {}",
                    s.place, s.id
                ));
                continue;
            };
            entries.push(Entry {
                id: s.id.clone(),
                kind: "see".into(),
                name_en: pen.clone(),
                name_ta: pta.clone(),
                draft_ta: None,
                place: s.place.clone(),
                place_name_en: pen,
                place_name_ta: pta,
                lat,
                lon,
                place_linked: linked,
                tradition: None,
                role: None,
                rank: Some(s.rank.clone()),
                born: None,
                died: None,
                year: None,
                kind_of_council: None,
                wikipedia: None,
            });
        }
        ChurchOut {
            sites: self.sites.clone(),
            entries,
        }
    }
}
