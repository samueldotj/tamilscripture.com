//! Static outline maps as SVG. The SVG is inlined into pages, so colours come
//! from the site's CSS tokens (`.map .land` etc. in app.css) and labels in
//! both scripts are present, with CSS showing the interface language.

use crate::geo::{clip_line, clip_ring, thin, BBox, Layer, Proj, Pt};
use std::fmt::Write;

pub struct Base {
    pub land: Layer,
    pub lakes: Layer,
    pub rivers: Layer,
}

pub struct MapPoint {
    pub id: String,
    pub lon: f64,
    pub lat: f64,
    pub label_en: String,
    pub label_ta: Option<String>,
    pub href: String,
    pub emphasis: bool,
    /// Sort key for labelling priority (more mentions first).
    pub weight: u32,
    /// Stop number on a journey map.
    pub number: Option<u32>,
}

pub struct MapSpec<'a> {
    pub title: String,
    pub points: &'a [MapPoint],
    pub route: Option<&'a [Pt]>,
    pub w: f64,
    pub h: f64,
    /// Minimum longitude span in degrees, so a single place still shows context.
    pub min_span: f64,
    /// Drawn at panel size (360 wide): labels are set larger relative to the canvas.
    pub small: bool,
}

fn esc(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

fn fmt(v: f64) -> String {
    let s = format!("{v:.1}");
    s.trim_end_matches('0').trim_end_matches('.').to_string()
}

fn path_of(rings: &[Vec<(f64, f64)>], close: bool) -> String {
    let mut d = String::new();
    for ring in rings {
        if ring.len() < 2 {
            continue;
        }
        let _ = write!(d, "M{} {}", fmt(ring[0].0), fmt(ring[0].1));
        for p in &ring[1..] {
            let _ = write!(d, "L{} {}", fmt(p.0), fmt(p.1));
        }
        if close {
            d.push('Z');
        }
    }
    d
}

struct Rect {
    x: f64,
    y: f64,
    w: f64,
    h: f64,
}
impl Rect {
    fn hits(&self, o: &Rect) -> bool {
        self.x < o.x + o.w && o.x < self.x + self.w && self.y < o.y + o.h && o.y < self.y + self.h
    }
}

/// Rough text width: Latin ~0.55em, Tamil ~0.75em per letter (signs ~0.25em).
fn text_width(s: &str, px: f64) -> f64 {
    s.chars()
        .map(|c| {
            if ('\u{0B80}'..='\u{0BFF}').contains(&c) {
                if matches!(c, '\u{0BBE}'..='\u{0BCD}') {
                    0.25 * px
                } else {
                    0.75 * px
                }
            } else {
                0.55 * px
            }
        })
        .sum()
}

pub fn render(base: &Base, spec: &MapSpec) -> String {
    let mut bbox = BBox::empty();
    for p in spec.points {
        bbox.add([p.lon, p.lat]);
    }
    if let Some(r) = spec.route {
        for p in r {
            bbox.add(*p);
        }
    }
    let proj = Proj::fit(bbox, spec.w, spec.h, 0.14, spec.min_span);
    let view = proj.bbox;

    let px = if spec.small { 14.0 } else { 12.0 };
    let mut svg = String::new();
    let _ = write!(
        svg,
        "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 {} {}\" class=\"map\" data-size=\"{}\" role=\"img\" aria-label=\"{}\"><title>{}</title>",
        fmt(spec.w),
        fmt(spec.h),
        if spec.small { "small" } else { "large" },
        esc(&spec.title),
        esc(&spec.title)
    );
    let _ = write!(
        svg,
        "<rect class=\"water\" width=\"{}\" height=\"{}\"/>",
        fmt(spec.w),
        fmt(spec.h)
    );

    // Land
    let mut rings: Vec<Vec<(f64, f64)>> = Vec::new();
    for poly in &base.land.polygons {
        for ring in poly {
            let c = clip_ring(ring, &view);
            if c.len() >= 3 {
                rings.push(thin(
                    &c.iter().map(|p| proj.xy(*p)).collect::<Vec<_>>(),
                    0.6,
                ));
            }
        }
    }
    let _ = write!(
        svg,
        "<path class=\"land\" fill-rule=\"evenodd\" d=\"{}\"/>",
        path_of(&rings, true)
    );
    // Lakes
    let mut rings: Vec<Vec<(f64, f64)>> = Vec::new();
    for poly in &base.lakes.polygons {
        for ring in poly {
            let c = clip_ring(ring, &view);
            if c.len() >= 3 {
                rings.push(thin(
                    &c.iter().map(|p| proj.xy(*p)).collect::<Vec<_>>(),
                    0.6,
                ));
            }
        }
    }
    if !rings.is_empty() {
        let _ = write!(
            svg,
            "<path class=\"lake\" fill-rule=\"evenodd\" d=\"{}\"/>",
            path_of(&rings, true)
        );
    }
    // Rivers
    let mut lines: Vec<Vec<(f64, f64)>> = Vec::new();
    for line in &base.rivers.lines {
        for part in clip_line(line, &view) {
            lines.push(thin(
                &part.iter().map(|p| proj.xy(*p)).collect::<Vec<_>>(),
                0.6,
            ));
        }
    }
    if !lines.is_empty() {
        let _ = write!(
            svg,
            "<path class=\"river\" d=\"{}\"/>",
            path_of(&lines, false)
        );
    }
    // Route
    if let Some(r) = spec.route {
        let pts: Vec<(f64, f64)> = r.iter().map(|p| proj.xy(*p)).collect();
        let _ = write!(
            svg,
            "<path class=\"route\" d=\"{}\"/>",
            path_of(&[pts], false)
        );
    }

    // Places: emphasised first, then by weight, so labels favour what matters.
    let mut order: Vec<usize> = (0..spec.points.len()).collect();
    order.sort_by(|&a, &b| {
        let (pa, pb) = (&spec.points[a], &spec.points[b]);
        pb.emphasis
            .cmp(&pa.emphasis)
            .then_with(|| pb.weight.cmp(&pa.weight))
            .then_with(|| pa.id.cmp(&pb.id))
    });
    let mut taken: Vec<Rect> = Vec::new();
    let mut groups = String::new();
    for i in order {
        let p = &spec.points[i];
        let (x, y) = proj.xy([p.lon, p.lat]);
        let r = if p.emphasis { 6.0 } else { 4.5 };
        taken.push(Rect {
            x: x - r,
            y: y - r,
            w: 2.0 * r,
            h: 2.0 * r,
        });
        let label_ta = p.label_ta.clone().unwrap_or_default();
        let width = text_width(&p.label_en, px).max(text_width(&label_ta, px)) + 4.0;
        let height = px * 1.25;
        // Candidate anchors: right, left, above, below.
        let cands = [
            (
                x + r + 4.0,
                y + px * 0.38,
                "start",
                Rect {
                    x: x + r + 3.0,
                    y: y - height / 2.0,
                    w: width,
                    h: height,
                },
            ),
            (
                x - r - 4.0,
                y + px * 0.38,
                "end",
                Rect {
                    x: x - r - 3.0 - width,
                    y: y - height / 2.0,
                    w: width,
                    h: height,
                },
            ),
            (
                x,
                y - r - 5.0,
                "middle",
                Rect {
                    x: x - width / 2.0,
                    y: y - r - 5.0 - px,
                    w: width,
                    h: height,
                },
            ),
            (
                x,
                y + r + px + 2.0,
                "middle",
                Rect {
                    x: x - width / 2.0,
                    y: y + r + 3.0,
                    w: width,
                    h: height,
                },
            ),
        ];
        let mut placed = None;
        for (lx, ly, anchor, rect) in cands {
            let inside = rect.x >= 0.0
                && rect.y >= 0.0
                && rect.x + rect.w <= spec.w
                && rect.y + rect.h <= spec.h;
            if inside && !taken.iter().any(|t| t.hits(&rect)) {
                placed = Some((lx, ly, anchor, rect));
                break;
            }
        }
        let crowded = placed.is_none();
        let (lx, ly, anchor, rect) = placed.unwrap_or((
            x + r + 4.0,
            y + px * 0.38,
            "start",
            Rect {
                x: x + r + 3.0,
                y: y - height / 2.0,
                w: width,
                h: height,
            },
        ));
        if !crowded {
            taken.push(rect);
        }
        let _ = write!(
            groups,
            "<a href=\"{}\" class=\"place{}{}\" data-place=\"{}\"><title>{}</title><circle cx=\"{}\" cy=\"{}\" r=\"{}\"/>",
            esc(&p.href),
            if p.emphasis { " em" } else { "" },
            if crowded { " crowded" } else { "" },
            esc(&p.id),
            esc(&p.label_en),
            fmt(x),
            fmt(y),
            fmt(r)
        );
        if let Some(n) = p.number {
            let _ = write!(
                groups,
                "<text class=\"n\" x=\"{}\" y=\"{}\" text-anchor=\"middle\">{}</text>",
                fmt(x),
                fmt(y + 3.2),
                n
            );
        }
        if !label_ta.is_empty() {
            let _ = write!(
                groups,
                "<text class=\"ta\" lang=\"ta\" x=\"{}\" y=\"{}\" text-anchor=\"{}\">{}</text>",
                fmt(lx),
                fmt(ly),
                anchor,
                esc(&label_ta)
            );
        }
        let _ = write!(
            groups,
            "<text class=\"en{}\" lang=\"en\" x=\"{}\" y=\"{}\" text-anchor=\"{}\">{}</text></a>",
            if label_ta.is_empty() { " only" } else { "" },
            fmt(lx),
            fmt(ly),
            anchor,
            esc(&p.label_en)
        );
    }
    let _ = write!(svg, "<g class=\"places\">{groups}</g>");
    let _ = write!(
        svg,
        "<text class=\"credit\" x=\"{}\" y=\"{}\" text-anchor=\"end\">Natural Earth · OpenBible.info</text></svg>",
        fmt(spec.w - 6.0),
        fmt(spec.h - 6.0)
    );
    svg
}
