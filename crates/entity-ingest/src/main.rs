//! entity-ingest: biblical places, people and dictionary articles for
//! tamilscripture.com (M6, M7).
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
//!   entities/people.json                 index of every person
//!   entities/person/{id}.json            one person
//!   entities/mentions/{BOOK}/{ch}.json   verse id → place and person ids, with summaries
//!   entities/articles/index.json         every dictionary article (title, source, hash)
//!   entities/articles/{source}/{id}.json one article with stable paragraph ids
//!   entities/journeys.json               journeys with resolved stops
//!   entities/geo/*.geojson               points, routes and the Natural Earth base
//!   entities/maps/**.svg                 static chapter, place and journey maps
//!   search/entities.csv                  id,type,slug,name_en,names_ta,alt_en,weight
//! `--draft-names` instead proposes Tamil forms into data/entities/names-ta.toml.

mod aquifer;
mod articles;
mod books;
mod church;
mod community;
mod corpus;
mod geo;
mod journeys;
mod names;
mod openbible;
mod stepbible;
mod svg;
mod tipnr;

use anyhow::{bail, Context, Result};
use books::Books;
use corpus::Corpus;
use names::{NameForm, NamesTa};
use openbible::Place;
use serde::Serialize;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

struct Args {
    books: PathBuf,
    entities: PathBuf,
    content: PathBuf,
    /// STEPBible tagged texts and lexicons, fetched by scripts/fetch-stepbible.mjs.
    stepbible: PathBuf,
    draft_names: bool,
    strict: bool,
}

fn parse_args() -> Result<Args> {
    let mut a = Args {
        books: PathBuf::from("data/books.toml"),
        entities: PathBuf::from("data/entities"),
        content: PathBuf::from("apps/web/static/content"),
        stepbible: PathBuf::from("data/cache/stepbible"),
        draft_names: false,
        strict: true,
    };
    let mut it = std::env::args().skip(1);
    while let Some(arg) = it.next() {
        match arg.as_str() {
            "--books" => a.books = it.next().context("--books needs a path")?.into(),
            "--entities" => a.entities = it.next().context("--entities needs a path")?.into(),
            "--content" => a.content = it.next().context("--content needs a path")?.into(),
            "--stepbible" => a.stepbible = it.next().context("--stepbible needs a path")?.into(),
            "--draft-names" => a.draft_names = true,
            "--lenient" => a.strict = false,
            "-h" | "--help" => {
                eprintln!("entity-ingest --books B --entities DIR --content DIR [--stepbible DIR] [--draft-names] [--lenient]");
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

fn round5(v: f64) -> f64 {
    (v * 1e5).round() / 1e5
}

/// `1Ch.24.25` → `1Ch 24:25`, the qualifier shown for same-named people.
fn ref_label(r: &str) -> String {
    let mut it = r.splitn(3, '.');
    match (it.next(), it.next(), it.next()) {
        (Some(b), Some(c), Some(v)) => format!("{b} {c}:{v}"),
        _ => r.to_string(),
    }
}

/// Per verse: place ids, person ids.
type VerseMentions = (Vec<String>, Vec<String>);

// ---- output shapes (mirrored in apps/web/src/lib/entities/types.ts) ----

#[derive(Serialize)]
struct NameTaOut {
    label: String,
    forms: Vec<String>,
    confidence: f32,
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    draft: bool,
    /// "community" when an accepted correction replaced the draft
    #[serde(skip_serializing_if = "Option::is_none")]
    provenance: Option<&'static str>,
}

fn names_ta_out(names: &NamesTa, name_en: &str) -> BTreeMap<String, NameTaOut> {
    names
        .get(name_en)
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
                            provenance: if f.owner {
                                Some("owner")
                            } else {
                                f.community.then_some("community")
                            },
                        },
                    )
                })
                .collect()
        })
        .unwrap_or_default()
}

fn all_ta_forms(names: &NamesTa, name_en: &str, lead_version: &str) -> String {
    // The first token is what the search box shows as the Tamil label, so the
    // display-worthy label of the lead (default Tamil) version leads; the rest
    // follow sorted.
    let Some(per) = names.get(name_en) else {
        return String::new();
    };
    let mut out: Vec<String> = Vec::new();
    let lead = per
        .get(lead_version)
        .filter(|f| f.display_ok())
        .or_else(|| per.values().find(|f| f.display_ok()))
        .map(|f| f.label.clone());
    if let Some(l) = &lead {
        out.push(l.clone());
    }
    let set: BTreeSet<String> = per
        .values()
        .flat_map(|f| std::iter::once(f.label.clone()).chain(f.forms.iter().cloned()))
        .filter(|s| Some(s) != lead.as_ref())
        .collect();
    out.extend(set);
    out.join(" ")
}

/// Tamil label for a name: the default Tamil version first, then any other,
/// only where the draft is trustworthy enough to show.
/// The form to show as "the" original-language name: the first "Named"
/// form with the most verses, else the first form with any text.
fn primary_form(forms: &[tipnr::NameForm]) -> Option<&tipnr::NameForm> {
    forms
        .iter()
        .filter(|f| !f.original.is_empty())
        .max_by_key(|f| (f.significance == "Named", f.verses.len()))
}

/// The inflected Tamil forms of a name that occur in the given verses, per
/// version, where the draft is trustworthy enough to show; the reader
/// underlines these words in the text. Only the chapter's own forms are kept,
/// which keeps each chapter's file small and the matching exact.
fn forms_ta(
    names: &NamesTa,
    name_en: &str,
    verse_ids: &[&String],
    corpora: &[Corpus],
) -> Option<BTreeMap<String, Vec<String>>> {
    let per = names.get(name_en)?;
    let out: BTreeMap<String, Vec<String>> = per
        .iter()
        .filter(|(_, f)| f.display_ok())
        .filter_map(|(v, f)| {
            let corpus = corpora.iter().find(|c| &c.version == v)?;
            let texts: Vec<&String> = verse_ids
                .iter()
                .filter_map(|id| corpus.verses.get(id.as_str()))
                .collect();
            let mut found: Vec<String> = std::iter::once(&f.label)
                .chain(f.forms.iter())
                .filter(|w| texts.iter().any(|t| t.contains(w.as_str())))
                .cloned()
                .collect();
            found.sort();
            found.dedup();
            (!found.is_empty()).then(|| (v.clone(), found))
        })
        .collect();
    (!out.is_empty()).then_some(out)
}

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

#[derive(Serialize)]
struct DescriptionOut<'a> {
    #[serde(skip_serializing_if = "str::is_empty")]
    brief: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    short: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    article: &'a str,
    source: &'static str,
    licence: &'static str,
    url: &'static str,
}

#[derive(Serialize)]
struct ArticleRef<'a> {
    source: &'a str,
    id: &'a str,
    title: &'a str,
    paragraphs: usize,
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
    /// STEP Bible description when a TIPNR place matches.
    #[serde(skip_serializing_if = "Option::is_none")]
    description: Option<DescriptionOut<'a>>,
    /// People linked to this place through the TIPNR name forms (founders etc.) are
    /// not resolved yet; dictionary articles are.
    #[serde(skip_serializing_if = "Vec::is_empty")]
    articles: Vec<ArticleRef<'a>>,
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

#[derive(Serialize)]
struct RelationOut {
    id: String,
    name_en: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    name_ta: Option<String>,
    #[serde(skip_serializing_if = "str::is_empty")]
    brief: String,
}

#[derive(Serialize)]
struct OriginalForm<'a> {
    significance: &'a str,
    original: &'a str,
    script: &'a str,
    strongs: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    translated: &'a str,
    verses: usize,
}

#[derive(Serialize)]
struct PersonOut<'a> {
    id: &'a str,
    #[serde(rename = "type")]
    kind: &'static str,
    name_en: &'a str,
    /// First reference, shown when several people share the name.
    #[serde(skip_serializing_if = "Option::is_none")]
    qualifier: Option<String>,
    gender: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    description: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    tribe: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    summary: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    brief: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    short: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    article: &'a str,
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    uncertain: bool,
    names_ta: BTreeMap<String, NameTaOut>,
    forms: Vec<OriginalForm<'a>>,
    relations: BTreeMap<&'static str, Vec<RelationOut>>,
    verses: &'a [String],
    #[serde(skip_serializing_if = "Vec::is_empty")]
    articles: Vec<ArticleRef<'a>>,
    source: DescriptionSource,
}

#[derive(Serialize)]
struct DescriptionSource {
    name: &'static str,
    url: &'static str,
    licence: &'static str,
    attribution: &'static str,
}

#[derive(Serialize)]
struct PersonIndexEntry<'a> {
    id: &'a str,
    name_en: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    qualifier: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    name_ta: Option<String>,
    gender: &'a str,
    #[serde(skip_serializing_if = "str::is_empty")]
    brief: &'a str,
    mentions: usize,
}

#[derive(Serialize)]
struct ArticleIndexEntry<'a> {
    id: &'a str,
    source: &'a str,
    title: &'a str,
    hash: &'a str,
    paragraphs: usize,
    #[serde(skip_serializing_if = "<[String]>::is_empty")]
    entities: &'a [String],
}

const STEP: DescriptionSource = DescriptionSource {
    name: "STEP Bible",
    url: "https://www.stepbible.org",
    licence: "CC BY 4.0",
    attribution: "Names, relations and descriptions from TIPNR by STEP Bible / Tyndale House Cambridge, CC BY 4.0",
};

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
    // The site's default version, from the version configs (R-3.6).
    let default_version = manifest["default_version"]
        .as_str()
        .context("manifest.default_version (rebuild with the current usfm-ingest)")?
        .to_string();
    let build_dir = args.content.join(&build);
    let mut tamil_versions: Vec<String> = manifest["versions"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|v| v["lang"].as_str() == Some("ta"))
        .filter_map(|v| v["code"].as_str().map(String::from))
        .collect();
    // The default Tamil version (the site default when it is Tamil, else the
    // first Tamil version marked default) leads for labels.
    let lead_ta: String = manifest["versions"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|v| v["lang"].as_str() == Some("ta"))
        .filter_map(|v| {
            v["code"]
                .as_str()
                .map(|c| (c, v["default"].as_bool().unwrap_or(false)))
        })
        .find(|&(c, d)| c == default_version || d)
        .map(|(c, _)| c.to_string())
        .or_else(|| tamil_versions.first().cloned())
        .unwrap_or_default();
    tamil_versions.sort_by_key(|v| if *v == lead_ta { 0 } else { 1 });

    let places = openbible::load(&args.entities.join("openbible-geo/ancient.jsonl"), &books)?;
    eprintln!(
        "places: {} ({} located)",
        places.len(),
        places.iter().filter(|p| p.lon.is_some()).count()
    );
    let tipnr = tipnr::load(&args.entities.join("tipnr/TIPNR.txt"), &books)?;
    let person_slug = tipnr::person_slugs(&tipnr.people);
    eprintln!(
        "people: {} (TIPNR), place descriptions: {}",
        tipnr.people.len(),
        tipnr.places.len()
    );

    // Verses per English name string (same-named places and people share Tamil forms).
    let mut verses_by_name: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for p in &places {
        verses_by_name
            .entry(p.name_en.clone())
            .or_default()
            .extend(p.verses.iter().cloned());
    }
    for p in &tipnr.people {
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
    let mut names = names::load(&names_path)?;
    if names.is_empty() {
        eprintln!(
            "warning: {} missing or empty; maps carry English labels only",
            names_path.display()
        );
    }
    let mut problems: Vec<String> = Vec::new();
    for (name, per) in &names {
        let Some(verses) = verses_by_name.get(name) else {
            problems.push(format!("{name}: not a place or person name in the sources"));
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
    let borrowed = names::mark_borrowed(&mut names);
    eprintln!(
        "names: {borrowed} descriptive names drafted with another name's word; shown in English"
    );
    // Accepted corrections (exported from the review queue) win over drafts.
    // They are applied after the corpus check: reviewers verified them.
    let overrides = community::load_overrides(&args.entities.join("overrides"))?;
    let names_overridden = community::apply_names(&mut names, &overrides);

    let out = build_dir.join("entities");
    let base = svg::Base {
        land: geo::load_layer(&args.entities.join("geo/base/land.geojson"))?,
        lakes: geo::load_layer(&args.entities.join("geo/base/lakes.geojson"))?,
        rivers: geo::load_layer(&args.entities.join("geo/base/rivers.geojson"))?,
    };
    for f in [
        "land",
        "coast",
        "lakes",
        "rivers",
        "world",
        "LICENSE",
        "SOURCE.md",
    ] {
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
    // Polity borders for the atlas timeline, built by scripts/build-polities.py
    // and passed through as they are.
    for f in ["polities.geojson", "SOURCE.md"] {
        let src = args.entities.join("geo/polities").join(f);
        if src.exists() {
            fs::create_dir_all(out.join("geo/polities"))?;
            fs::copy(&src, out.join("geo/polities").join(f))?;
        }
    }

    let by_id: BTreeMap<&str, &Place> = places.iter().map(|p| (p.id.as_str(), p)).collect();

    // ---- dictionary articles, linked to entities by name ----
    let blocklist = articles::load_blocklist(&args.entities.join("blocklist.toml"))?;
    let mut all_articles: Vec<articles::Article> = Vec::new();
    for (dir, src) in [
        ("eastons", &articles::EASTONS),
        ("smiths", &articles::SMITHS),
    ] {
        let dir = args.entities.join(dir);
        if dir.join("src").exists() {
            all_articles.extend(articles::load_neuu(&dir, src)?);
        }
    }
    let aquifer_dir = args.entities.join("aquifer");
    if aquifer_dir.join("src/eng/json").exists() {
        all_articles.extend(aquifer::load(&aquifer_dir)?);
    }
    let before = all_articles.len();
    all_articles.retain(|a| {
        !blocklist
            .iter()
            .any(|(s, i)| s == &a.source && (i == &a.slug || i == &a.id))
    });
    eprintln!(
        "articles: {} ({} blocked)",
        all_articles.len(),
        before - all_articles.len()
    );
    // name (lowercase) → entity refs
    let mut entity_by_name: HashMap<String, Vec<String>> = HashMap::new();
    for p in &places {
        entity_by_name
            .entry(p.name_en.to_lowercase())
            .or_default()
            .push(format!("place/{}", p.id));
    }
    for p in &tipnr.people {
        entity_by_name
            .entry(p.name_en.to_lowercase())
            .or_default()
            .push(format!("person/{}", person_slug[&p.key]));
    }
    let mut articles_by_entity: HashMap<String, Vec<usize>> = HashMap::new();
    for (i, a) in all_articles.iter_mut().enumerate() {
        // Source hints (Aquifer's ACAI ids) first, filtered by kind; else the title.
        let mut ents: Vec<String> = Vec::new();
        for (kind, name) in &a.hints {
            if let Some(found) = entity_by_name.get(name) {
                let prefix = format!("{kind}/");
                ents.extend(found.iter().filter(|e| e.starts_with(&prefix)).cloned());
            }
        }
        if ents.is_empty() {
            if let Some(found) = entity_by_name.get(&a.title.to_lowercase()) {
                ents = found.clone();
            }
        }
        ents.sort();
        ents.dedup();
        if !ents.is_empty() {
            a.entities = ents.clone();
            for e in ents {
                articles_by_entity.entry(e).or_default().push(i);
            }
        }
    }
    // Tamil drafts from outside the repository, then accepted corrections.
    let drafts = community::load_drafts(&args.entities.join("drafts/ta"))?;
    let label_of = |title: &str| label_ta(&names, title, &tamil_versions);
    let report = community::apply_articles(&mut all_articles, &drafts, &overrides, &label_of);
    eprintln!(
        "community: {} name corrections; {} drafts ({} stale) covering {} paragraphs; {} paragraph corrections",
        names_overridden, report.drafts, report.stale_drafts, report.draft_paragraphs, report.overridden
    );
    for x in &report.invalid {
        eprintln!("warning: draft rejected {x}");
    }
    for x in &report.unmatched {
        eprintln!("warning: draft paragraph no longer in source: {x}");
    }
    for x in &report.orphans {
        eprintln!("warning: orphaned correction (paragraph re-segmented): {x}");
    }
    for x in &report.glossary_misses {
        eprintln!("warning: draft does not use the accepted name: {x}");
    }
    // ---- the same headword across dictionaries ----
    // Easton's leads: it is the concise public-domain source, and an entry that
    // opened on the ShareAlike one would carry that licence into everything
    // quoting it. Computed after the Tamil is applied so a preview can be Tamil.
    const ENTRY_ORDER: [&str; 3] = ["eastons", "smiths", "aquifer"];
    let source_rank = |src: &str| {
        ENTRY_ORDER
            .iter()
            .position(|s| *s == src)
            .unwrap_or(ENTRY_ORDER.len())
    };
    let mut by_headword: BTreeMap<String, Vec<usize>> = BTreeMap::new();
    for (i, a) in all_articles.iter().enumerate() {
        by_headword
            .entry(articles::headword_key(&a.title))
            .or_default()
            .push(i);
    }
    let mut siblings: Vec<Vec<articles::Sibling>> = vec![Vec::new(); all_articles.len()];
    for ids in by_headword.values() {
        if ids.len() < 2 {
            continue;
        }
        let mut ordered = ids.clone();
        ordered.sort_by_key(|&i| (source_rank(&all_articles[i].source), i));
        for &i in &ordered {
            siblings[i] = ordered
                .iter()
                .filter(|&&j| j != i)
                .map(|&j| {
                    let a = &all_articles[j];
                    let (preview, preview_ta) = articles::preview_of(a);
                    articles::Sibling {
                        source: a.source.clone(),
                        id: a.id.clone(),
                        title: a.title.clone(),
                        title_ta: a.title_ta.clone(),
                        paragraphs: a.paragraphs.len(),
                        preview,
                        preview_ta,
                    }
                })
                .collect();
        }
    }
    let shared = siblings.iter().filter(|s| !s.is_empty()).count();
    for (i, s) in siblings.into_iter().enumerate() {
        all_articles[i].also_in = s;
    }
    println!(
        "dictionary: {shared} of {} articles share a headword with another dictionary",
        all_articles.len()
    );

    let article_refs = |key: &str| -> Vec<ArticleRef<'_>> {
        articles_by_entity
            .get(key)
            .map(|ix| {
                ix.iter()
                    .map(|&i| {
                        let a = &all_articles[i];
                        ArticleRef {
                            source: &a.source,
                            id: &a.id,
                            title: &a.title,
                            paragraphs: a.paragraphs.len(),
                        }
                    })
                    .collect()
            })
            .unwrap_or_default()
    };
    for a in &all_articles {
        write_json(&out.join("articles").join(format!("{}.json", a.id)), a)?;
    }
    let article_index: Vec<ArticleIndexEntry> = all_articles
        .iter()
        .map(|a| ArticleIndexEntry {
            id: &a.id,
            source: &a.source,
            title: &a.title,
            hash: &a.hash,
            paragraphs: a.paragraphs.len(),
            entities: &a.entities,
        })
        .collect();
    write_json(&out.join("articles/index.json"), &article_index)?;

    // ---- TIPNR place descriptions matched to OpenBible places ----
    let mut tipnr_places_by_name: HashMap<String, Vec<&tipnr::TipnrPlace>> = HashMap::new();
    for tp in &tipnr.places {
        tipnr_places_by_name
            .entry(tp.name_en.to_lowercase())
            .or_default()
            .push(tp);
    }
    let description_for = |p: &Place| -> Option<&tipnr::TipnrPlace> {
        let cands = tipnr_places_by_name.get(&p.name_en.to_lowercase())?;
        if cands.len() == 1 {
            return Some(cands[0]);
        }
        let mine: BTreeSet<&String> = p.verses.iter().collect();
        cands
            .iter()
            .map(|tp| (tp.verses.iter().filter(|v| mine.contains(v)).count(), *tp))
            .filter(|(n, _)| *n > 0)
            .max_by_key(|(n, tp)| (*n, std::cmp::Reverse(tp.name_en.clone())))
            .map(|(_, tp)| tp)
    };

    // Journeys resolve stops to places.
    let journeys_in = journeys::load(&args.entities.join("geo/journeys.toml"))?;
    let routes_dir = args.entities.join("geo/ubs-routes-sa/GeoJsonRoutes");
    let mut journeys_out: Vec<journeys::JourneyOut> = Vec::new();
    // Drawn route lines per journey (same index as journeys_out); empty → straight legs.
    let mut journey_routes: Vec<Vec<Vec<geo::Pt>>> = Vec::new();
    let mut journeys_by_place: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for j in &journeys_in {
        let mut stops = Vec::new();
        let mut bbox = geo::BBox::empty();
        let lines = journeys::load_routes(&routes_dir, &j.id, &j.routes)?;
        for l in &lines {
            for p in l {
                bbox.add(*p);
            }
        }
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
            route_source: (!lines.is_empty()).then_some(journeys::UBS_ROUTES.key),
            route_attribution: (!lines.is_empty()).then_some(journeys::UBS_ROUTES.attribution),
        });
        journey_routes.push(lines);
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

    // ---- people ----
    let person_by_key: HashMap<&str, &tipnr::Person> =
        tipnr.people.iter().map(|p| (p.key.as_str(), p)).collect();
    let name_count: HashMap<String, usize> =
        tipnr.people.iter().fold(HashMap::new(), |mut m, p| {
            *m.entry(p.name_en.to_lowercase()).or_insert(0) += 1;
            m
        });
    let relation = |keys: &[String]| -> Vec<RelationOut> {
        keys.iter()
            .filter_map(|k| person_by_key.get(k.as_str()))
            .map(|q| RelationOut {
                id: person_slug[&q.key].clone(),
                name_en: q.name_en.clone(),
                name_ta: label_ta(&names, &q.name_en, &tamil_versions),
                brief: q.brief.clone(),
            })
            .collect()
    };
    let mut people_index = Vec::new();
    let mut csv = String::from("id,type,slug,name_en,names_ta,alt_en,weight\n");
    for p in &tipnr.people {
        let slug = &person_slug[&p.key];
        let qualifier = if name_count[&p.name_en.to_lowercase()] > 1 {
            Some(ref_label(&p.first_ref))
        } else {
            None
        };
        let mut relations: BTreeMap<&'static str, Vec<RelationOut>> = BTreeMap::new();
        for (k, list) in [
            ("parents", &p.parents),
            ("siblings", &p.siblings),
            ("partners", &p.partners),
            ("children", &p.children),
        ] {
            let r = relation(list);
            if !r.is_empty() {
                relations.insert(k, r);
            }
        }
        let person_out = PersonOut {
            id: slug,
            kind: "person",
            name_en: &p.name_en,
            qualifier: qualifier.clone(),
            gender: &p.gender,
            description: &p.description,
            tribe: &p.tribe,
            summary: &p.summary,
            brief: &p.brief,
            short: &p.short,
            article: &p.article,
            uncertain: p.uncertain,
            names_ta: names_ta_out(&names, &p.name_en),
            forms: p
                .forms
                .iter()
                .map(|f| OriginalForm {
                    significance: &f.significance,
                    original: &f.original,
                    script: &f.script,
                    strongs: &f.strongs,
                    translated: &f.translated,
                    verses: f.verses.len(),
                })
                .collect(),
            relations,
            verses: &p.verses,
            articles: article_refs(&format!("person/{slug}")),
            source: STEP,
        };
        write_json(
            &out.join("person").join(format!("{slug}.json")),
            &person_out,
        )?;
        people_index.push(PersonIndexEntry {
            id: slug,
            name_en: &p.name_en,
            qualifier,
            name_ta: label_ta(&names, &p.name_en, &tamil_versions),
            gender: &p.gender,
            brief: &p.brief,
            mentions: p.verses.len(),
        });
        let weight = ((1 + p.verses.len()) as f64).ln();
        csv.push_str(&format!(
            "{},person,{},{},{},{},{:.3}\n",
            csv_field(&format!("person/{slug}")),
            csv_field(slug),
            csv_field(&p.name_en),
            csv_field(&all_ta_forms(&names, &p.name_en, &lead_ta)),
            csv_field(&p.brief),
            weight
        ));
    }
    write_json(&out.join("people.json"), &people_index)?;

    // ---- mentions per chapter: verse → place and person ids, with summaries ----
    #[derive(Default)]
    struct ChapterMentions {
        verses: BTreeMap<String, VerseMentions>,
        places: BTreeSet<String>,
        people: BTreeSet<String>,
    }
    let mut mentions: BTreeMap<(u32, u32), ChapterMentions> = BTreeMap::new();
    let chapter_of = |v: &str| -> Option<(u32, u32)> {
        let mut it = v.split('.');
        let (code, ch) = (it.next()?, it.next()?);
        let book = books.by_code(code)?;
        Some((book.order, ch.parse().ok()?))
    };
    for p in &places {
        for v in &p.verses {
            if let Some(k) = chapter_of(v) {
                let m = mentions.entry(k).or_default();
                m.verses.entry(v.clone()).or_default().0.push(p.id.clone());
                m.places.insert(p.id.clone());
            }
        }
    }
    for p in &tipnr.people {
        let slug = &person_slug[&p.key];
        for v in &p.verses {
            if let Some(k) = chapter_of(v) {
                let m = mentions.entry(k).or_default();
                m.verses.entry(v.clone()).or_default().1.push(slug.clone());
                m.people.insert(slug.clone());
            }
        }
    }
    let person_by_slug: HashMap<&str, &tipnr::Person> = tipnr
        .people
        .iter()
        .map(|p| (person_slug[&p.key].as_str(), p))
        .collect();
    // ---- Strong's concordance for names ----
    // TIPNR gives every name form with its Strong's number and the verses it
    // occurs in, so clicking a Strong's number can list every verse the word
    // is used in. People and places that share a word share its page.
    #[derive(Default)]
    struct StrongsWord {
        script: String,
        words: BTreeSet<String>,
        renderings: BTreeSet<String>,
        people: BTreeSet<String>,
        places: BTreeSet<String>,
        verses: BTreeSet<String>,
    }
    let mut strongs: BTreeMap<String, StrongsWord> = BTreeMap::new();
    let valid = |s: &str| {
        s.len() >= 2
            && (s.starts_with('H') || s.starts_with('G'))
            && s.chars().all(|c| c.is_ascii_alphanumeric())
    };
    let mut add_forms = |forms: &[tipnr::NameForm], person: Option<&str>, place: Option<&str>| {
        for f in forms.iter().filter(|f| valid(&f.strongs)) {
            let w = strongs.entry(f.strongs.clone()).or_default();
            w.script = f.script.clone();
            if !f.original.is_empty() {
                w.words.insert(f.original.clone());
            }
            for r in f.translated.split(';') {
                // TIPNR marks untranslated occurrences as "[ ]"; only real words count.
                let r = r
                    .split('=')
                    .next()
                    .unwrap_or("")
                    .trim()
                    .trim_matches(['[', ']', ' ']);
                if r.chars().any(char::is_alphabetic) {
                    w.renderings.insert(r.to_string());
                }
            }
            if let Some(id) = person {
                w.people.insert(id.to_string());
            }
            if let Some(id) = place {
                w.places.insert(id.to_string());
            }
            w.verses.extend(f.verses.iter().cloned());
        }
    };
    for p in &tipnr.people {
        add_forms(&p.forms, Some(person_slug[&p.key].as_str()), None);
    }
    for p in &places {
        if let Some(tp) = description_for(p) {
            add_forms(&tp.forms, None, Some(p.id.as_str()));
        }
    }
    // ---- The concordance (docs/feature_concordance.md) ----
    // With STEP's tagged texts fetched, every Strong's number of the Hebrew OT
    // and Greek NT gets a file with all its verses; without them (a build that
    // skipped the fetch), the name words from TIPNR alone, in the same shape.
    let place_by_id: HashMap<&str, &Place> = places.iter().map(|p| (p.id.as_str(), p)).collect();
    let ours: HashSet<String> = corpora
        .iter()
        .find(|c| c.version == default_version)
        .or(corpora.first())
        .map(|c| c.verses.keys().cloned().collect())
        .unwrap_or_default();
    let step = stepbible::load(&args.stepbible, &books, &ours)?;
    if let Some(s) = &step {
        if !s.unmapped.is_empty() {
            let sample: Vec<&String> = s.unmapped.iter().take(10).collect();
            let msg = format!(
                "{} tagged verses have no verse in our text: {sample:?}",
                s.unmapped.len()
            );
            if args.strict {
                bail!(msg);
            }
            eprintln!("warning: {msg}");
        }
    } else {
        eprintln!(
            "warning: {} has no STEPBible files (run node scripts/fetch-stepbible.mjs); concordance covers names only",
            args.stepbible.display()
        );
    }
    let names_for = |w: &StrongsWord| -> Vec<Value> {
        let people = w
            .people
            .iter()
            .filter_map(|id| person_by_slug.get(id.as_str()).map(|p| (id, *p)))
            .map(|(id, p)| serde_json::json!({ "kind": "person", "id": id, "name_en": p.name_en, "name_ta": label_ta(&names, &p.name_en, &tamil_versions), "brief": p.brief }));
        let places = w
            .places
            .iter()
            .filter_map(|id| place_by_id.get(id.as_str()))
            .map(|p| serde_json::json!({ "kind": "place", "id": p.id, "name_en": p.name_en, "name_ta": label_ta(&names, &p.name_en, &tamil_versions) }));
        people.chain(places).collect()
    };
    // (verse sort key, verse id, surface form) per number, and how many words carry it.
    let mut occ: BTreeMap<String, stepbible::Occurrences> = match &step {
        Some(s) => stepbible::occurrences(&books, &s.words),
        None => BTreeMap::new(),
    };
    for (num, w) in &strongs {
        if occ.contains_key(num) || stepbible::is_grammar(num) {
            continue;
        }
        let form = w.words.iter().next().cloned().unwrap_or_default();
        let mut verses: Vec<(u32, String, String)> = w
            .verses
            .iter()
            .filter(|v| ours.is_empty() || ours.contains(*v))
            .map(|v| (stepbible::verse_key(&books, v), v.clone(), form.clone()))
            .collect();
        verses.sort_by_key(|(k, _, _)| *k);
        let count = verses.len();
        occ.insert(num.clone(), stepbible::Occurrences { verses, count });
    }
    let empty = StrongsWord::default();
    // Tamil glosses (concordance C5): an accepted correction wins over a draft.
    let gloss_drafts = community::load_gloss_drafts(&args.entities.join("drafts/lexicon-ta.toml"))?;
    let gloss_ta = |num: &str| -> (Option<String>, Option<&'static str>) {
        if let Some(o) = overrides.lexicon.get(num) {
            return (
                Some(o.ta.clone()),
                Some(if o.owner { "owner" } else { "community" }),
            );
        }
        match gloss_drafts.get(num) {
            Some(t) => (Some(t.clone()), Some("draft")),
            None => (None, None),
        }
    };
    let mut strongs_index: Vec<Value> = Vec::new();
    for (num, o) in &occ {
        if o.verses.is_empty() || stepbible::is_grammar(num) {
            continue;
        }
        let lex = step
            .as_ref()
            .and_then(|s| stepbible::lookup(&s.lexicon, num));
        let tip = strongs.get(num).unwrap_or(&empty);
        let lemma = lex
            .map(|l| l.lemma.clone())
            .or_else(|| tip.words.iter().next().cloned())
            .unwrap_or_default();
        let script = if num.starts_with('G') { "el" } else { "he" };
        // Verse keys delta-encoded, and each verse's surface form as an index
        // into a forms table: even the Greek article's 7,000 verses stay small.
        let mut forms: Vec<String> = Vec::new();
        let mut form_ix: HashMap<String, usize> = HashMap::new();
        let (mut v, mut fi, mut last) = (Vec::new(), Vec::new(), 0u32);
        let mut books_count: Vec<(String, usize)> = Vec::new();
        for (k, id, form) in &o.verses {
            v.push(k - last);
            last = *k;
            let ix = *form_ix.entry(form.clone()).or_insert_with(|| {
                forms.push(form.clone());
                forms.len() - 1
            });
            fi.push(ix);
            let code = id.split('.').next().unwrap_or("").to_string();
            match books_count.last_mut() {
                Some((c, n)) if *c == code => *n += 1,
                _ => books_count.push((code, 1)),
            }
        }
        let gloss = lex.map(|l| l.gloss.clone()).unwrap_or_else(|| {
            tip.renderings
                .iter()
                .cloned()
                .collect::<Vec<_>>()
                .join(", ")
        });
        write_json(
            &out.join("strongs")
                .join(format!("{}.json", stepbible::file_name(num))),
            &serde_json::json!({
                "s": num, "script": script, "lemma": lemma,
                "translit": lex.map(|l| l.translit.clone()).unwrap_or_default(),
                "pos": lex.map(|l| l.pos.clone()).unwrap_or_default(),
                "gloss": gloss, "def": lex.map(|l| l.def.clone()).unwrap_or_default(),
                "count": o.count, "books": books_count, "v": v, "f": forms, "fi": fi,
                "gloss_ta": gloss_ta(num).0, "gloss_ta_source": gloss_ta(num).1,
                "names": names_for(tip), "renderings": tip.renderings
            }),
        )?;
        strongs_index.push(serde_json::json!([
            num,
            lemma,
            lex.map(|l| l.translit.clone()).unwrap_or_default(),
            gloss,
            o.verses.len(),
            gloss_ta(num).0.unwrap_or_default()
        ]));
    }
    write_json(&out.join("strongs/index.json"), &strongs_index)?;

    // The original words of every chapter, for the reader's மூலம் view.
    let mut chapters_written = 0usize;
    if let Some(s) = &step {
        let mut by_chapter: BTreeMap<(u32, u32), BTreeMap<u32, Vec<Value>>> = BTreeMap::new();
        for w in &s.words {
            let mut it = w.verse.split('.');
            let (Some(code), Some(ch), Some(vn)) = (it.next(), it.next(), it.next()) else {
                continue;
            };
            let (Some(book), Ok(ch), Ok(vn)) =
                (books.by_code(code), ch.parse::<u32>(), vn.parse::<u32>())
            else {
                continue;
            };
            by_chapter
                .entry((book.order, ch))
                .or_default()
                .entry(vn)
                .or_default()
                .push(serde_json::json!([
                    w.text,
                    w.translit,
                    w.gloss,
                    w.strongs.first().cloned().unwrap_or_default(),
                    w.morph
                ]));
        }
        for ((order, ch), verses) in &by_chapter {
            let book = &books.list[(*order - 1) as usize];
            let verses: BTreeMap<String, &Vec<Value>> =
                verses.iter().map(|(v, w)| (v.to_string(), w)).collect();
            write_json(
                &out.join("original")
                    .join(&book.code)
                    .join(format!("{ch}.json")),
                &serde_json::json!({ "book": book.code, "chapter": ch, "lang": if *order <= 39 { "he" } else { "el" }, "verses": verses }),
            )?;
            chapters_written += 1;
        }
    }
    eprintln!(
        "concordance: {} Strong's numbers{}; original words for {} chapters",
        strongs_index.len(),
        if step.is_some() { "" } else { " (names only)" },
        chapters_written
    );

    for ((order, ch), m) in &mentions {
        let book = &books.list[(*order - 1) as usize];
        let mut entries: Vec<(&String, &VerseMentions)> = m.verses.iter().collect();
        entries.sort_by_key(|(k, _)| {
            k.rsplit('.')
                .next()
                .and_then(|v| v.parse::<u32>().ok())
                .unwrap_or(0)
        });
        let verses: Vec<Value> = entries
            .iter()
            .map(|(k, (pl, pe))| serde_json::json!({ "verse": k, "places": pl, "people": pe }))
            .collect();
        let verses_of = |id: &str, place: bool| -> Vec<&String> {
            m.verses
                .iter()
                .filter(|(_, (pl, pe))| {
                    if place {
                        pl.iter().any(|x| x == id)
                    } else {
                        pe.iter().any(|x| x == id)
                    }
                })
                .map(|(k, _)| k)
                .collect()
        };
        let place_summary: BTreeMap<&str, Value> = m
            .places
            .iter()
            .filter_map(|id| by_id.get(id.as_str()))
            .map(|p| {
                (
                    p.id.as_str(),
                    serde_json::json!({
                        "name_en": p.name_en, "qualifier": p.qualifier, "name_ta": label_ta(&names, &p.name_en, &tamil_versions),
                        "forms": forms_ta(&names, &p.name_en, &verses_of(&p.id, true), &corpora),
                        "type": p.types.first().cloned().unwrap_or_default(), "precision": p.precision,
                        "lat": p.lat.map(round5), "lon": p.lon.map(round5), "mentions": p.verses.len(),
                        "article": articles_by_entity.get(&format!("place/{}", p.id)).and_then(|ix| ix.first()).map(|&i| all_articles[i].id.clone())
                    }),
                )
            })
            .collect();
        let people_summary: BTreeMap<&str, Value> = m
            .people
            .iter()
            .filter_map(|id| person_by_slug.get(id.as_str()).map(|p| (id.as_str(), *p)))
            .map(|(id, p)| {
                (
                    id,
                    serde_json::json!({
                        "name_en": p.name_en, "qualifier": if name_count[&p.name_en.to_lowercase()] > 1 { Some(ref_label(&p.first_ref)) } else { None },
                        "name_ta": label_ta(&names, &p.name_en, &tamil_versions), "forms": forms_ta(&names, &p.name_en, &verses_of(id, false), &corpora),
                        "gender": p.gender, "brief": p.brief, "mentions": p.verses.len(),
                        "article": articles_by_entity.get(&format!("person/{id}")).and_then(|ix| ix.first()).map(|&i| all_articles[i].id.clone()),
                        "original": primary_form(&p.forms).map(|f| serde_json::json!({ "text": f.original, "script": f.script, "strongs": f.strongs }))
                    }),
                )
            })
            .collect();
        write_json(
            &out.join("mentions")
                .join(&book.code)
                .join(format!("{ch}.json")),
            &serde_json::json!({ "book": book.code, "chapter": ch, "verses": verses, "places": place_summary, "people": people_summary, "map": !place_summary.values().all(|p| p["lat"].is_null()) }),
        )?;
    }

    // ---- place files and index ----
    let mut index_entries = Vec::new();
    let located: Vec<&Place> = places.iter().filter(|p| p.lon.is_some()).collect();
    for p in &places {
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
        let desc = description_for(p);
        let out_place = PlaceOut {
            id: &p.id,
            kind: "place",
            name_en: &p.name_en,
            qualifier: &p.qualifier,
            article: &p.article,
            alt_en: &p.alt_en,
            names_ta: names_ta_out(&names, &p.name_en),
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
            description: desc.map(|tp| DescriptionOut { brief: &tp.brief, short: &tp.short, article: &tp.article, source: STEP.name, licence: STEP.licence, url: STEP.url }),
            articles: article_refs(&format!("place/{}", p.id)),
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
        index_entries.push(IndexEntry {
            id: &p.id,
            name_en: &p.name_en,
            qualifier: &p.qualifier,
            name_ta: label_ta(&names, &p.name_en, &tamil_versions),
            place_type,
            lat: p.lat.map(round5),
            lon: p.lon.map(round5),
            precision: &p.precision,
            mentions: p.verses.len(),
        });
        let weight = ((1 + p.verses.len()) as f64).ln();
        csv.push_str(&format!(
            "{},place,{},{},{},{},{:.3}\n",
            csv_field(&format!("place/{}", p.id)),
            csv_field(&p.id),
            csv_field(&format!(
                "{}{}",
                p.name_en,
                p.qualifier
                    .as_ref()
                    .map(|q| format!(" {q}"))
                    .unwrap_or_default()
            )),
            csv_field(&all_ta_forms(&names, &p.name_en, &lead_ta)),
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
    for a in &all_articles {
        csv.push_str(&format!(
            "{},article,{},{},,,{:.3}\n",
            csv_field(&format!("article/{}", a.id)),
            csv_field(&a.id),
            csv_field(&a.title),
            ((1 + a.paragraphs.len()) as f64).ln()
        ));
    }
    write_text(&build_dir.join("search/entities.csv"), &csv)?;

    // ---- GeoJSON for the explore map ----
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
        .zip(&journey_routes)
        .map(|(j, lines)| {
            let geometry = if lines.is_empty() {
                serde_json::json!({ "type": "LineString", "coordinates": j.stops.iter().map(|s| [s.lon, s.lat]).collect::<Vec<_>>() })
            } else {
                serde_json::json!({ "type": "MultiLineString", "coordinates": lines.iter().map(|l| l.iter().map(|p| [round5(p[0]), round5(p[1])]).collect::<Vec<_>>()).collect::<Vec<_>>() })
            };
            serde_json::json!({
                "type": "Feature",
                "properties": { "id": j.id, "name_en": j.name_en, "name_ta": j.name_ta, "period": j.period, "route_source": j.route_source },
                "geometry": geometry
            })
        })
        .collect();
    write_json(
        &out.join("geo/journeys.geojson"),
        &serde_json::json!({ "type": "FeatureCollection", "features": jfeats }),
    )?;

    // ---- the early church: fathers, councils and sees ----
    if let Some(ch) = church::load(&args.entities.join("church/church.json"))? {
        // Tamil for a city the gazetteer knows comes from the aligned names, the
        // same as everywhere else; the church data only names its own sites.
        let place_ta: BTreeMap<&str, String> = places
            .iter()
            .filter(|p| p.lat.is_some())
            .filter_map(|p| {
                label_ta(&names, &p.name_en, &tamil_versions).map(|t| (p.id.as_str(), t))
            })
            .collect();
        // A place the New Testament names had a church from the apostolic age.
        let nt_places: BTreeSet<&str> = places
            .iter()
            .filter(|p| {
                p.verses.iter().any(|v| {
                    v.split('.')
                        .next()
                        .and_then(|code| books.by_code(code))
                        .is_some_and(|b| b.testament == "NT")
                })
            })
            .map(|p| p.id.as_str())
            .collect();
        let gaz = church::Gazetteer {
            new_testament: nt_places,
            places: places
                .iter()
                .filter(|p| p.lat.is_some())
                .map(|p| {
                    (
                        p.id.as_str(),
                        (
                            p.name_en.as_str(),
                            place_ta.get(p.id.as_str()).map(String::as_str),
                            p.lat.unwrap(),
                            p.lon.unwrap(),
                        ),
                    )
                })
                .collect(),
        };
        let mut church_problems: Vec<String> = Vec::new();
        let resolved = ch.resolve(&gaz, &mut church_problems);
        for p in &church_problems {
            eprintln!("{p}");
        }
        let cfeats: Vec<Value> = resolved
            .entries
            .iter()
            .map(|e| {
                serde_json::json!({
                    "type": "Feature",
                    "properties": {
                        "id": e.id, "type": e.kind, "name_en": e.name_en, "name_ta": e.name_ta,
                        "place": e.place, "year": e.year, "born": e.born, "died": e.died,
                        "tradition": e.tradition, "rank": e.rank, "kind": e.kind_of_council
                    },
                    "geometry": { "type": "Point", "coordinates": [round5(e.lon), round5(e.lat)] }
                })
            })
            .collect();
        write_json(
            &out.join("geo/church.geojson"),
            &serde_json::json!({ "type": "FeatureCollection", "features": cfeats }),
        )?;
        write_json(&out.join("church.json"), &resolved)?;
        let n_f = resolved
            .entries
            .iter()
            .filter(|e| e.kind == "father")
            .count();
        let n_c = resolved
            .entries
            .iter()
            .filter(|e| e.kind == "council")
            .count();
        let n_s = resolved.entries.iter().filter(|e| e.kind == "see").count();
        println!("church: {n_f} fathers, {n_c} councils, {n_s} sees");
    }

    // ---- static maps ----
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
    for ((order, ch), m) in &mentions {
        let book = &books.list[(*order - 1) as usize];
        let pts: Vec<svg::MapPoint> = m
            .places
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
                routes: &[],
                credit_extra: None,
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
        let spec = svg::MapSpec {
            title,
            points: &pts,
            routes: &[],
            credit_extra: None,
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
    for (j, lines) in journeys_out.iter().zip(&journey_routes) {
        let straight: Vec<geo::Pt> = j.stops.iter().map(|s| [s.lon, s.lat]).collect();
        let routes: Vec<Vec<geo::Pt>> = if lines.is_empty() {
            vec![straight]
        } else {
            lines.clone()
        };
        let mut seen = BTreeSet::new();
        let pts: Vec<svg::MapPoint> = j
            .stops
            .iter()
            .enumerate()
            .filter(|(_, s)| seen.insert(s.place.clone()))
            .map(|(i, s)| point_of(by_id[s.place.as_str()], true, Some(i as u32 + 1)))
            .collect();
        let spec = svg::MapSpec {
            title: format!("{} · {}", j.name_ta, j.name_en),
            points: &pts,
            routes: &routes,
            credit_extra: (!lines.is_empty()).then_some(" · Routes: UBS/Ritmeyer CC BY-SA 4.0"),
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

    let described = places
        .iter()
        .filter(|p| description_for(p).is_some())
        .count();
    eprintln!(
        "entities: {} places ({described} with STEP descriptions), {} people, {} articles ({} linked), {} chapters with mentions, {} journeys, {} maps → {}",
        places.len(),
        tipnr.people.len(),
        all_articles.len(),
        all_articles.iter().filter(|a| !a.entities.is_empty()).count(),
        mentions.len(),
        journeys_out.len(),
        n_maps,
        out.display()
    );
    Ok(())
}
