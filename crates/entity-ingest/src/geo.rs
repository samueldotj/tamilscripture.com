//! Minimal GeoJSON reading, rectangle clipping and an equirectangular
//! projection for the static SVG maps. Enough for outline maps; not a GIS.

use anyhow::{Context, Result};
use serde_json::Value;
use std::path::Path;

pub type Pt = [f64; 2]; // lon, lat

#[derive(Debug, Clone, Copy)]
pub struct BBox {
    pub min_lon: f64,
    pub min_lat: f64,
    pub max_lon: f64,
    pub max_lat: f64,
}

impl BBox {
    pub fn empty() -> BBox {
        BBox { min_lon: f64::MAX, min_lat: f64::MAX, max_lon: f64::MIN, max_lat: f64::MIN }
    }
    pub fn add(&mut self, p: Pt) {
        self.min_lon = self.min_lon.min(p[0]);
        self.max_lon = self.max_lon.max(p[0]);
        self.min_lat = self.min_lat.min(p[1]);
        self.max_lat = self.max_lat.max(p[1]);
    }
    pub fn is_empty(&self) -> bool {
        self.min_lon > self.max_lon
    }
}

pub struct Layer {
    /// Polygons as rings (outer first, holes after), lon/lat.
    pub polygons: Vec<Vec<Vec<Pt>>>,
    /// Polylines, lon/lat.
    pub lines: Vec<Vec<Pt>>,
}

fn read_pts(v: &Value) -> Vec<Pt> {
    v.as_array()
        .map(|a| {
            a.iter()
                .filter_map(|p| {
                    let c = p.as_array()?;
                    Some([c.first()?.as_f64()?, c.get(1)?.as_f64()?])
                })
                .collect()
        })
        .unwrap_or_default()
}

pub fn load_layer(path: &Path) -> Result<Layer> {
    let text = std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    let d: Value = serde_json::from_str(&text).with_context(|| format!("parsing {}", path.display()))?;
    let mut layer = Layer { polygons: Vec::new(), lines: Vec::new() };
    for f in d["features"].as_array().into_iter().flatten() {
        let g = &f["geometry"];
        match g["type"].as_str() {
            Some("Polygon") => layer.polygons.push(g["coordinates"].as_array().into_iter().flatten().map(read_pts).collect()),
            Some("MultiPolygon") => {
                for poly in g["coordinates"].as_array().into_iter().flatten() {
                    layer.polygons.push(poly.as_array().into_iter().flatten().map(read_pts).collect());
                }
            }
            Some("LineString") => layer.lines.push(read_pts(&g["coordinates"])),
            Some("MultiLineString") => {
                for l in g["coordinates"].as_array().into_iter().flatten() {
                    layer.lines.push(read_pts(l));
                }
            }
            _ => {}
        }
    }
    Ok(layer)
}

/// Sutherland–Hodgman clipping of one ring against a rectangle.
pub fn clip_ring(ring: &[Pt], b: &BBox) -> Vec<Pt> {
    fn clip_edge(input: &[Pt], inside: impl Fn(Pt) -> bool, intersect: impl Fn(Pt, Pt) -> Pt) -> Vec<Pt> {
        let mut out = Vec::with_capacity(input.len());
        if input.is_empty() {
            return out;
        }
        let mut prev = input[input.len() - 1];
        for &cur in input {
            let (ci, pi) = (inside(cur), inside(prev));
            if ci {
                if !pi {
                    out.push(intersect(prev, cur));
                }
                out.push(cur);
            } else if pi {
                out.push(intersect(prev, cur));
            }
            prev = cur;
        }
        out
    }
    let at_x = |x: f64| move |p: Pt, q: Pt| -> Pt { let t = (x - p[0]) / (q[0] - p[0]); [x, p[1] + t * (q[1] - p[1])] };
    let at_y = |y: f64| move |p: Pt, q: Pt| -> Pt { let t = (y - p[1]) / (q[1] - p[1]); [p[0] + t * (q[0] - p[0]), y] };
    let r = clip_edge(ring, |p| p[0] >= b.min_lon, at_x(b.min_lon));
    let r = clip_edge(&r, |p| p[0] <= b.max_lon, at_x(b.max_lon));
    let r = clip_edge(&r, |p| p[1] >= b.min_lat, at_y(b.min_lat));
    clip_edge(&r, |p| p[1] <= b.max_lat, at_y(b.max_lat))
}

/// Clip a polyline to a rectangle, splitting where it leaves and re-enters.
pub fn clip_line(line: &[Pt], b: &BBox) -> Vec<Vec<Pt>> {
    let mut out: Vec<Vec<Pt>> = Vec::new();
    let mut cur: Vec<Pt> = Vec::new();
    for w in line.windows(2) {
        if let Some((p, q)) = clip_segment(w[0], w[1], b) {
            if cur.is_empty() || cur.last() != Some(&p) {
                if !cur.is_empty() {
                    out.push(std::mem::take(&mut cur));
                }
                cur.push(p);
            }
            cur.push(q);
        } else if !cur.is_empty() {
            out.push(std::mem::take(&mut cur));
        }
    }
    if cur.len() > 1 {
        out.push(cur);
    }
    out
}

/// Liang–Barsky segment clipping.
fn clip_segment(p: Pt, q: Pt, b: &BBox) -> Option<(Pt, Pt)> {
    let (dx, dy) = (q[0] - p[0], q[1] - p[1]);
    let mut t0 = 0.0f64;
    let mut t1 = 1.0f64;
    for (pk, qk) in [(-dx, p[0] - b.min_lon), (dx, b.max_lon - p[0]), (-dy, p[1] - b.min_lat), (dy, b.max_lat - p[1])] {
        if pk == 0.0 {
            if qk < 0.0 {
                return None;
            }
            continue;
        }
        let t = qk / pk;
        if pk < 0.0 {
            if t > t1 {
                return None;
            }
            t0 = t0.max(t);
        } else {
            if t < t0 {
                return None;
            }
            t1 = t1.min(t);
        }
    }
    if t0 > t1 {
        return None;
    }
    Some(([p[0] + t0 * dx, p[1] + t0 * dy], [p[0] + t1 * dx, p[1] + t1 * dy]))
}

/// Equirectangular projection with a latitude-corrected horizontal scale,
/// fitted so `bbox` fills a `w`×`h` canvas.
#[derive(Debug, Clone, Copy)]
pub struct Proj {
    pub bbox: BBox,
    kx: f64,
    ky: f64,
}

impl Proj {
    /// Expands `bbox` to the canvas aspect ratio (centred) and pads it.
    pub fn fit(mut bbox: BBox, w: f64, h: f64, pad_frac: f64, min_lon_span: f64) -> Proj {
        if bbox.is_empty() {
            bbox = BBox { min_lon: 34.0, min_lat: 29.5, max_lon: 37.0, max_lat: 33.5 };
        }
        let mid_lat = (bbox.min_lat + bbox.max_lat) / 2.0;
        let cos = mid_lat.to_radians().cos().max(0.2);
        let mut span_lon = (bbox.max_lon - bbox.min_lon).max(min_lon_span);
        let mut span_lat = (bbox.max_lat - bbox.min_lat).max(min_lon_span * cos * h / w);
        span_lon *= 1.0 + 2.0 * pad_frac;
        span_lat *= 1.0 + 2.0 * pad_frac;
        // Match the canvas aspect: width in "cos-degrees" vs height in degrees.
        let aspect = w / h;
        if span_lon * cos / span_lat > aspect {
            span_lat = span_lon * cos / aspect;
        } else {
            span_lon = span_lat * aspect / cos;
        }
        let c_lon = (bbox.min_lon + bbox.max_lon) / 2.0;
        let c_lat = mid_lat;
        let fitted = BBox { min_lon: c_lon - span_lon / 2.0, max_lon: c_lon + span_lon / 2.0, min_lat: c_lat - span_lat / 2.0, max_lat: c_lat + span_lat / 2.0 };
        Proj { bbox: fitted, kx: w / span_lon, ky: h / span_lat }
    }

    pub fn xy(&self, p: Pt) -> (f64, f64) {
        ((p[0] - self.bbox.min_lon) * self.kx, (self.bbox.max_lat - p[1]) * self.ky)
    }
}

/// Drop consecutive projected points closer than `tol` pixels.
pub fn thin(points: &[(f64, f64)], tol: f64) -> Vec<(f64, f64)> {
    let mut out: Vec<(f64, f64)> = Vec::with_capacity(points.len());
    for &p in points {
        if let Some(&(x, y)) = out.last() {
            if (p.0 - x).abs() < tol && (p.1 - y).abs() < tol {
                continue;
            }
        }
        out.push(p);
    }
    out
}
