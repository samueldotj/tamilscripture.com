//! The Psalms explorer (docs/feature_psalms_explorer.md): validates the
//! hand-edited `data/psalms/{taxonomy,psalms,notes}.toml` and writes
//! `entities/psalms/index.json` (grid and filters) and `entities/psalms/{n}.json`
//! (the card). Psalter tunes (`data/psalter/`, rendered by tools/psalter) are
//! checked against their MusicXML and copied to `entities/psalter/{tune}/`.

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Theme {
    pub id: String,
    #[serde(skip_serializing)]
    pub order: u32,
    pub en: String,
    pub ta: String,
    pub color: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Genre {
    pub id: String,
    #[serde(skip_serializing)]
    pub order: u32,
    pub mood: String,
    pub en: String,
    pub ta: String,
    pub about_en: String,
    pub about_ta: String,
    #[serde(default, skip_serializing)]
    pub review: bool,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Collection {
    pub id: String,
    #[serde(skip_serializing)]
    pub order: u32,
    pub en: String,
    pub ta: String,
    pub psalms: Vec<u32>,
    pub basis: String,
    #[serde(default, skip_serializing)]
    pub review: bool,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Author {
    pub id: String,
    #[serde(skip_serializing)]
    pub order: u32,
    pub en: String,
    pub ta: String,
}

#[derive(Deserialize)]
struct Taxonomy {
    theme: Vec<Theme>,
    genre: Vec<Genre>,
    collection: Vec<Collection>,
    author: Vec<Author>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct NtAttribution {
    pub authors: Vec<String>,
    #[serde(rename = "ref")]
    pub reference: String,
}

#[derive(Debug, Clone, Deserialize)]
struct PsalmIn {
    theme: String,
    genres: Vec<String>,
    #[serde(default)]
    maybe: Vec<String>,
    authors: Vec<String>,
    #[serde(default)]
    nt: Option<NtAttribution>,
    #[serde(default)]
    review: bool,
}

#[derive(Deserialize)]
struct PsalmsFile {
    psalms: BTreeMap<String, PsalmIn>,
}

#[derive(Debug, Clone, Deserialize)]
struct NoteIn {
    title_ta: String,
    title_en: String,
    key: String,
    #[serde(default)]
    tags: Vec<String>,
    #[serde(default)]
    summary_ta: Option<String>,
    #[serde(default)]
    summary_en: Option<String>,
    #[serde(default)]
    review: bool,
}

/// One tune of `data/psalter/tunes.toml`; the card shows these fields.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Tune {
    pub id: String,
    pub name: String,
    pub meter: String,
    pub key: String,
    pub composer: String,
    pub source: String,
    #[serde(default, skip_serializing)]
    pub review: bool,
}

#[derive(Deserialize)]
struct TunesFile {
    tune: Vec<Tune>,
}

#[derive(Deserialize)]
struct PairingsFile {
    /// Version key ("23", "100-2", "119-5") → tune ids, the traditional pairing first.
    psalms: BTreeMap<String, Vec<String>>,
    /// Metre ("8.6.8.6") → tunes offered for a version with no traditional pairing.
    #[serde(default)]
    fallback: BTreeMap<String, Vec<String>>,
}

/// One version of a psalm in `data/psalter/scottish-1650/psalm-NNN.toml`.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Version {
    pub key: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub part: Option<u32>,
    pub label: String,
    pub meter: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub argument: String,
    pub stanzas: Vec<Vec<String>>,
    /// Tune ids to offer, filled from pairings.toml.
    #[serde(default)]
    pub tunes: Vec<String>,
    /// True when `tunes` are the metre's fallback rather than traditional pairings.
    #[serde(default)]
    pub fallback: bool,
}

#[derive(Deserialize)]
struct MetricalFile {
    psalm: u32,
    version: Vec<Version>,
}

/// The files `psalter render` writes for a tune and the build copies.
const RENDERED: [&str; 6] = ["incipit.svg", "full.svg", "incipit.draw.json", "full.draw.json", "events.json", "audio.mp3"];

fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes).iter().map(|b| format!("{b:02x}")).collect()
}

/// A tune's metre as a version spells it: "C.M." is "8.6.8.6".
fn meter_of(tune: &Tune) -> &str {
    match tune.meter.as_str() {
        "C.M." => "8.6.8.6",
        "L.M." => "8.8.8.8",
        "S.M." => "6.6.8.6",
        m => m,
    }
}

type Psalter = (BTreeMap<String, Tune>, BTreeMap<u32, Vec<Version>>);

/// Tunes, the 1650 metrical text and the pairings from `data/psalter/`, checked: every
/// tune was rendered from its current MusicXML, every pairing names a version and a tune
/// whose metre fits it. Empty when the directory is absent.
fn load_psalter(dir: &Path, problems: &mut Vec<String>) -> Result<Psalter> {
    if !dir.join("tunes.toml").exists() {
        return Ok((BTreeMap::new(), BTreeMap::new()));
    }
    let tunes: TunesFile = read_toml(&dir.join("tunes.toml"))?;
    let pairs: PairingsFile = read_toml(&dir.join("pairings.toml"))?;
    let tunes: BTreeMap<String, Tune> = tunes.tune.into_iter().map(|t| (t.id.clone(), t)).collect();
    for id in tunes.keys() {
        let src = dir.join("tunes").join(format!("{id}.musicxml"));
        let rendered = dir.join("rendered").join(id);
        let Ok(xml) = fs::read(&src) else {
            problems.push(format!("tune {id}: no {}", src.display()));
            continue;
        };
        let meta: Option<Value> = fs::read_to_string(rendered.join("render.json")).ok().and_then(|t| serde_json::from_str(&t).ok());
        match meta.as_ref().and_then(|m| m["source_sha256"].as_str()) {
            Some(h) if h == sha256_hex(&xml) => {}
            Some(_) => problems.push(format!("tune {id}: the MusicXML changed since it was rendered; run `psalter render {id}`")),
            None => problems.push(format!("tune {id}: not rendered; run `psalter render {id}`")),
        }
        for f in RENDERED {
            if !rendered.join(f).exists() {
                problems.push(format!("tune {id}: rendered/{id}/{f} is missing"));
            }
        }
    }

    let mut psalms: BTreeMap<u32, Vec<Version>> = BTreeMap::new();
    let text_dir = dir.join("scottish-1650");
    if text_dir.is_dir() {
        let mut files: Vec<_> = fs::read_dir(&text_dir)?.filter_map(|e| e.ok().map(|e| e.path())).filter(|p| p.extension().is_some_and(|x| x == "toml")).collect();
        files.sort();
        for path in files {
            let f: MetricalFile = read_toml(&path)?;
            psalms.insert(f.psalm, f.version);
        }
    }
    let keys: BTreeMap<String, (u32, usize)> = psalms
        .iter()
        .flat_map(|(n, vs)| vs.iter().enumerate().map(move |(i, v)| (v.key.clone(), (*n, i))))
        .collect();
    let fits = |id: &str, meter: &str, what: &str, problems: &mut Vec<String>| match tunes.get(id) {
        None => {
            problems.push(format!("pairings.toml: {what}: unknown tune {id}"));
            false
        }
        Some(t) if meter_of(t) != meter => {
            problems.push(format!("pairings.toml: {what}: {id} is {} but the version is {meter}", t.meter));
            false
        }
        Some(_) => true,
    };
    for (key, ids) in &pairs.psalms {
        let Some(&(n, i)) = keys.get(key) else {
            problems.push(format!("pairings.toml: {key} is not a version of any psalm"));
            continue;
        };
        let meter = psalms[&n][i].meter.clone();
        for id in ids {
            fits(id, &meter, key, problems);
        }
        psalms.get_mut(&n).unwrap()[i].tunes = ids.clone();
    }
    for (meter, ids) in &pairs.fallback {
        for id in ids {
            fits(id, meter, &format!("fallback {meter}"), problems);
        }
    }
    for v in psalms.values_mut().flatten() {
        if v.tunes.is_empty() {
            if let Some(ids) = pairs.fallback.get(&v.meter) {
                v.tunes = ids.clone();
                v.fallback = true;
            }
        }
    }
    Ok((tunes, psalms))
}

/// `psalms/{n}.json`.
#[derive(Serialize)]
struct Card<'a> {
    n: u32,
    summary_ta: Option<&'a str>,
    summary_en: Option<&'a str>,
    tags: &'a [String],
    nt: Option<&'a NtAttribution>,
    /// Every tune the versions name, with what the card shows of it.
    tunes: Vec<&'a Tune>,
    /// The psalm in the 1650 Scottish Psalter: one entry per version (or part of Psalm 119).
    metrical: &'a [Version],
}

fn read_toml<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T> {
    let text = fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    toml::from_str(&text).with_context(|| format!("parsing {}", path.display()))
}

/// Number of verses in a psalm, from the lead version's chapter JSON, or None
/// when the chapter is not in this build (fixture builds).
fn verse_count(build_dir: &Path, version: &str, n: u32) -> Result<Option<u32>> {
    let path = build_dir.join(version).join("PSA").join(format!("{n}.json"));
    if !path.exists() {
        return Ok(None);
    }
    let v: Value = serde_json::from_str(&fs::read_to_string(&path)?)?;
    let mut max = 0;
    for b in v["blocks"].as_array().into_iter().flatten() {
        for s in b["segments"].as_array().into_iter().flatten() {
            if let Some(id) = s["id"].as_str() {
                if let Some(v) = id.rsplit('.').next().and_then(|x| x.parse::<u32>().ok()) {
                    max = max.max(v);
                }
            }
        }
    }
    Ok(Some(max))
}

/// "23:1" or "121:1-2" → (chapter, first verse, last verse).
fn parse_key(key: &str) -> Option<(u32, u32, u32)> {
    let (ch, vs) = key.split_once(':')?;
    let (a, b) = match vs.split_once('-') {
        Some((a, b)) => (a.parse().ok()?, b.parse().ok()?),
        None => {
            let a = vs.parse().ok()?;
            (a, a)
        }
    };
    Some((ch.parse().ok()?, a, b))
}

/// Validates the psalms data and tunes and writes `{out}/psalms/` and
/// `{out}/psalter/`. Returns the number of entries still marked for review.
pub fn build(dir: &Path, psalter: &Path, build_dir: &Path, lead_version: &str, out: &Path) -> Result<usize> {
    let mut tax: Taxonomy = read_toml(&dir.join("taxonomy.toml"))?;
    let psalms: PsalmsFile = read_toml(&dir.join("psalms.toml"))?;
    let notes: BTreeMap<String, NoteIn> = read_toml(&dir.join("notes.toml"))?;
    tax.theme.sort_by_key(|t| t.order);
    tax.genre.sort_by_key(|t| t.order);
    tax.collection.sort_by_key(|t| t.order);
    tax.author.sort_by_key(|t| t.order);

    let mut problems: Vec<String> = Vec::new();
    let (tunes, metrical) = load_psalter(psalter, &mut problems)?;
    let themes: BTreeSet<&str> = tax.theme.iter().map(|t| t.id.as_str()).collect();
    let genres: BTreeSet<&str> = tax.genre.iter().map(|t| t.id.as_str()).collect();
    let authors: BTreeSet<&str> = tax.author.iter().map(|t| t.id.as_str()).collect();

    for c in &tax.collection {
        if let Some(n) = c.psalms.iter().find(|n| !(1..=150).contains(*n)) {
            problems.push(format!("collection {}: psalm {n} out of range", c.id));
        }
    }

    let mut by_n: BTreeMap<u32, &PsalmIn> = BTreeMap::new();
    for (k, p) in &psalms.psalms {
        match k.parse::<u32>() {
            Ok(n) if (1..=150).contains(&n) => {
                by_n.insert(n, p);
            }
            _ => problems.push(format!("psalms.toml: key {k} is not a psalm number")),
        }
    }
    for n in 1..=150 {
        if !by_n.contains_key(&n) {
            problems.push(format!("psalms.toml: psalm {n} is missing"));
        }
    }
    let mut theme_counts: BTreeMap<&str, u32> = BTreeMap::new();
    for (n, p) in &by_n {
        if !themes.contains(p.theme.as_str()) {
            problems.push(format!("psalm {n}: unknown theme {}", p.theme));
        }
        *theme_counts.entry(p.theme.as_str()).or_default() += 1;
        for g in p.genres.iter().chain(&p.maybe) {
            if !genres.contains(g.as_str()) {
                problems.push(format!("psalm {n}: unknown genre {g}"));
            }
        }
        let nt_authors = p.nt.iter().flat_map(|a| &a.authors);
        for a in p.authors.iter().chain(nt_authors) {
            if !authors.contains(a.as_str()) {
                problems.push(format!("psalm {n}: unknown author {a}"));
            }
        }
    }
    for t in &tax.theme {
        if !theme_counts.contains_key(t.id.as_str()) {
            problems.push(format!("theme {} has no psalms", t.id));
        }
    }
    for (k, note) in &notes {
        let Ok(n) = k.parse::<u32>() else {
            problems.push(format!("notes.toml: key {k} is not a psalm number"));
            continue;
        };
        match parse_key(&note.key) {
            Some((ch, a, b)) if ch == n && a >= 1 && a <= b => {
                if let Some(max) = verse_count(build_dir, lead_version, n)? {
                    if b > max {
                        problems.push(format!(
                            "notes.toml {n}: key {} past the last verse ({max})",
                            note.key
                        ));
                    }
                }
            }
            _ => problems.push(format!("notes.toml {n}: key {:?} is not a verse of psalm {n}", note.key)),
        }
    }
    if !problems.is_empty() {
        for p in &problems {
            eprintln!("psalms: {p}");
        }
        bail!("psalms: {} problems in {}", problems.len(), dir.display());
    }

    // Each psalm as a positional array:
    // [n, theme, genres, authors, title_ta, title_en, key, tune]
    let rows: Vec<Value> = by_n
        .iter()
        .map(|(n, p)| {
            let note = notes.get(&n.to_string());
            serde_json::json!([
                n,
                p.theme,
                p.genres,
                p.authors,
                note.map(|x| x.title_ta.as_str()),
                note.map(|x| x.title_en.as_str()),
                note.map(|x| x.key.clone()).unwrap_or_else(|| format!("{n}:1")),
                metrical.get(n).and_then(|vs| vs.first()).and_then(|v| v.tunes.first())
            ])
        })
        .collect();
    let index = serde_json::json!({
        "themes": tax.theme,
        "genres": tax.genre,
        "collections": tax.collection,
        "authors": tax.author,
        "psalms": rows,
    });
    let dir_out = out.join("psalms");
    crate::write_json(&dir_out.join("index.json"), &index)?;
    let empty: Vec<String> = Vec::new();
    for (n, p) in &by_n {
        let note = notes.get(&n.to_string());
        let card = Card {
            n: *n,
            summary_ta: note.and_then(|x| x.summary_ta.as_deref()),
            summary_en: note.and_then(|x| x.summary_en.as_deref()),
            tags: note.map(|x| x.tags.as_slice()).unwrap_or(&empty),
            nt: p.nt.as_ref(),
            tunes: {
                let mut seen = BTreeSet::new();
                metrical.get(n).into_iter().flatten().flat_map(|v| &v.tunes).filter(|id| seen.insert(id.as_str())).filter_map(|id| tunes.get(id)).collect()
            },
            metrical: metrical.get(n).map(Vec::as_slice).unwrap_or(&[]),
        };
        crate::write_json(&dir_out.join(format!("{n}.json")), &card)?;
    }
    for id in tunes.keys() {
        let from = psalter.join("rendered").join(id);
        let to = out.join("psalter").join(id);
        fs::create_dir_all(&to)?;
        for f in RENDERED {
            fs::copy(from.join(f), to.join(f)).with_context(|| format!("copying {}", from.join(f).display()))?;
        }
    }

    let review = by_n.values().filter(|p| p.review).count()
        + notes.values().filter(|x| x.review).count()
        + tax.genre.iter().filter(|g| g.review).count()
        + tax.collection.iter().filter(|c| c.review).count()
        + tunes.values().filter(|t| t.review).count();
    Ok(review)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keys() {
        assert_eq!(parse_key("23:1"), Some((23, 1, 1)));
        assert_eq!(parse_key("121:1-2"), Some((121, 1, 2)));
        assert_eq!(parse_key("121"), None);
        assert_eq!(parse_key("1:x"), None);
    }

    #[test]
    fn repository_data_is_valid() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        let tmp = std::env::temp_dir().join(format!("psalms-test-{}", std::process::id()));
        build(&root.join("data/psalms"), &root.join("data/psalter"), &tmp, "IRVTAM", &tmp).unwrap();
        let index: Value =
            serde_json::from_str(&fs::read_to_string(tmp.join("psalms/index.json")).unwrap())
                .unwrap();
        assert_eq!(index["psalms"].as_array().unwrap().len(), 150);
        assert_eq!(index["psalms"][22][7], "crimond");
        let p119: Value = serde_json::from_str(&fs::read_to_string(tmp.join("psalms/119.json")).unwrap()).unwrap();
        assert_eq!(p119["metrical"].as_array().unwrap().len(), 22);
        let p100: Value = serde_json::from_str(&fs::read_to_string(tmp.join("psalms/100.json")).unwrap()).unwrap();
        assert_eq!(p100["metrical"][0]["label"], "L.M.");
        assert_eq!(p100["metrical"][0]["tunes"][0], "old-hundredth");
        assert!(tmp.join("psalter/crimond/audio.mp3").exists());
        fs::remove_dir_all(&tmp).ok();
    }
}
