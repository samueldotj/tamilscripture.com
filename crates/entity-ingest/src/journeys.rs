//! Hand-authored journeys from `data/entities/geo/journeys.toml`: ordered
//! stops that reference place ids. Version 1 routes are straight legs between
//! stops; a `route` override with lon/lat pairs can replace a leg later.

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Clone, Deserialize)]
pub struct StopIn {
    pub place: String,
    #[serde(default)]
    pub r#ref: Option<String>,
    #[serde(default)]
    pub note_en: Option<String>,
    #[serde(default)]
    pub note_ta: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct JourneyIn {
    pub id: String,
    pub name_en: String,
    pub name_ta: String,
    pub period: String,
    #[serde(default)]
    pub summary_en: Option<String>,
    #[serde(default)]
    pub summary_ta: Option<String>,
    #[serde(default)]
    pub passages: Vec<String>,
    pub stops: Vec<StopIn>,
}

#[derive(Deserialize)]
struct File {
    journey: Vec<JourneyIn>,
}

pub fn load(path: &Path) -> Result<Vec<JourneyIn>> {
    if !path.exists() {
        return Ok(Vec::new());
    }
    let text =
        std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    let f: File = toml::from_str(&text).with_context(|| format!("parsing {}", path.display()))?;
    let mut ids = std::collections::HashSet::new();
    for j in &f.journey {
        if !ids.insert(j.id.clone()) {
            bail!("duplicate journey id {}", j.id);
        }
        if j.stops.len() < 2 {
            bail!("journey {} needs at least two stops", j.id);
        }
    }
    Ok(f.journey)
}

#[derive(Debug, Clone, Serialize)]
pub struct StopOut {
    pub place: String,
    pub name_en: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name_ta: Option<String>,
    pub lon: f64,
    pub lat: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub r#ref: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub note_en: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub note_ta: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct JourneyOut {
    pub id: String,
    pub name_en: String,
    pub name_ta: String,
    pub period: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub summary_en: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub summary_ta: Option<String>,
    pub passages: Vec<String>,
    pub stops: Vec<StopOut>,
    /// [min_lon, min_lat, max_lon, max_lat]
    pub bbox: [f64; 4],
}
