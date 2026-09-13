//! Hand-authored journeys from `data/entities/geo/journeys.toml`: ordered
//! stops that reference place ids, and optional `routes` naming UBS Project
//! MARBLE GeoJSON files (CC BY-SA 4.0, `geo/ubs-routes-sa/`) whose lines are
//! drawn instead of straight legs between stops.

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::Path;

use crate::geo::Pt;

pub struct RouteSource {
    pub key: &'static str,
    pub attribution: &'static str,
}

pub const UBS_ROUTES: RouteSource = RouteSource {
    key: "ubs",
    attribution: "Routes: UBS Project MARBLE (Leen Ritmeyer), © United Bible Societies 2023, CC BY-SA 4.0",
};

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
    /// File stems under `geo/ubs-routes-sa/GeoJsonRoutes/` (without `.geojson`).
    #[serde(default)]
    pub routes: Vec<String>,
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
    /// "ubs" when the drawn route comes from a ShareAlike source
    #[serde(skip_serializing_if = "Option::is_none")]
    pub route_source: Option<&'static str>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub route_attribution: Option<&'static str>,
}

/// Every LineString in the named UBS files, in file order. A referenced file
/// that is missing fails the build; a null feature (one upstream file has
/// one) is skipped.
pub fn load_routes(dir: &Path, journey: &str, names: &[String]) -> Result<Vec<Vec<Pt>>> {
    let mut out = Vec::new();
    for name in names {
        let path = dir.join(format!("{name}.geojson"));
        let text = std::fs::read_to_string(&path)
            .with_context(|| format!("journey {journey}: route file {}", path.display()))?;
        let v: Value = serde_json::from_str(&text)
            .with_context(|| format!("journey {journey}: parsing {}", path.display()))?;
        let feats: Vec<&Value> = match v.get("type").and_then(Value::as_str) {
            Some("FeatureCollection") => v["features"].as_array().into_iter().flatten().collect(),
            _ => vec![&v],
        };
        let before = out.len();
        for f in feats {
            let Some(g) = f.get("geometry") else { continue };
            let coords = &g["coordinates"];
            match g.get("type").and_then(Value::as_str) {
                Some("LineString") => out.push(line(coords)),
                Some("MultiLineString") => {
                    for l in coords.as_array().into_iter().flatten() {
                        out.push(line(l));
                    }
                }
                _ => {}
            }
        }
        out.retain(|l| l.len() >= 2);
        if out.len() == before {
            bail!("journey {journey}: route file {name} has no lines");
        }
    }
    Ok(out)
}

fn line(coords: &Value) -> Vec<Pt> {
    coords
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|c| {
            let a = c.as_array()?;
            Some([a.first()?.as_f64()?, a.get(1)?.as_f64()?])
        })
        .collect()
}
