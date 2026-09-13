//! Tamil surface forms for English place names, per Tamil version.
//!
//! `draft_one()` proposes forms by co-occurrence: a word stem that recurs
//! across the verses where the name occurs and is rare elsewhere is the name.
//! Tamil case suffixes (தமஸ்கு, தமஸ்குவில், தமஸ்குவுக்கு) are handled by
//! scoring shared prefixes of the normalised tokens rather than whole tokens,
//! so every inflection counts towards one candidate. Candidates are always
//! words present in the text. The reviewed file `data/entities/names-ta.toml`
//! is the build input; `validate()` refuses a form that does not occur in the
//! name's verses.

use crate::corpus::{norm, tokens, Corpus};
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NameForm {
    /// Base form for labels and titles.
    pub label: String,
    /// Every inflected form as it occurs in the text.
    pub forms: Vec<String>,
    pub confidence: f32,
    /// Verses of this version the name occurs in (evidence behind the draft).
    #[serde(default)]
    pub n: u32,
    /// True until a reviewer has confirmed the entry.
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub review: bool,
    /// Set by an accepted correction from `overrides/names.toml` (never saved here).
    #[serde(skip)]
    pub community: bool,
    /// Owner-authored override (`owner = true` in the override file).
    #[serde(skip)]
    pub owner: bool,
}

impl NameForm {
    /// Whether the label is trustworthy enough to show without review:
    /// reviewed, or well attested across several verses.
    pub fn display_ok(&self) -> bool {
        !self.review || (self.n >= 3 && self.confidence >= 0.4)
    }
}

/// English name → version code → form.
pub type NamesTa = BTreeMap<String, BTreeMap<String, NameForm>>;

pub fn load(path: &Path) -> Result<NamesTa> {
    if !path.exists() {
        return Ok(NamesTa::new());
    }
    let text =
        std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    toml::from_str(&text).with_context(|| format!("parsing {}", path.display()))
}

fn toml_str(s: &str) -> String {
    format!("\"{}\"", s.replace('\\', "\\\\").replace('"', "\\\""))
}

/// Writes one `["Name"]` table per English name with an inline table per
/// version, so a reviewer edits one line per language.
pub fn save(path: &Path, names: &NamesTa) -> Result<()> {
    let mut out = String::new();
    out.push_str("# Tamil forms of biblical place names, per Tamil version.\n");
    out.push_str("# Drafted by `entity-ingest --draft-names` from the verses where each name\n");
    out.push_str("# occurs; edit `label` (the base form shown on maps) and `forms` (every\n");
    out.push_str("# inflected form in the text), then delete `review = true`. Every entry in\n");
    out.push_str("# `forms` must occur in that version's text for the name's verses, or the\n");
    out.push_str("# build fails; `n` is the number of verses the draft was made from.\n");
    out.push_str("# Licence: CC BY 4.0 (tamilscripture.com contributors).\n\n");
    for (name, versions) in names {
        out.push_str(&format!("[{}]\n", toml_str(name)));
        for (version, f) in versions {
            let forms: Vec<String> = f.forms.iter().map(|s| toml_str(s)).collect();
            out.push_str(&format!(
                "{version} = {{ label = {}, forms = [{}], confidence = {:.2}, n = {}{} }}\n",
                toml_str(&f.label),
                forms.join(", "),
                f.confidence,
                f.n,
                if f.review { ", review = true" } else { "" }
            ));
        }
        out.push('\n');
    }
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(path, out).with_context(|| format!("writing {}", path.display()))
}

fn is_tamil_word(s: &str) -> bool {
    s.chars().any(|c| ('\u{0B80}'..='\u{0BFF}').contains(&c))
}

fn char_prefix(s: &str, n: usize) -> &str {
    match s.char_indices().nth(n) {
        Some((i, _)) => &s[..i],
        None => s,
    }
}

/// Draft a form for one name from the verses it occurs in. `None` when the
/// corpus has none of those verses.
pub fn draft_one(verse_ids: &[String], corpus: &Corpus) -> Option<NameForm> {
    let texts: Vec<&String> = verse_ids
        .iter()
        .filter_map(|v| corpus.verses.get(v))
        .collect();
    if texts.is_empty() {
        return None;
    }
    let n = texts.len() as f32;
    // Per verse: normalised tokens; per normalised token: raw spellings.
    let mut verse_norms: Vec<HashSet<String>> = Vec::with_capacity(texts.len());
    let mut raws: HashMap<String, BTreeMap<String, u32>> = HashMap::new();
    for t in &texts {
        let mut set = HashSet::new();
        for raw in tokens(t) {
            if !is_tamil_word(&raw) || raw.chars().count() < 2 {
                continue;
            }
            let k = norm(&raw);
            if k.is_empty() {
                continue;
            }
            *raws.entry(k.clone()).or_default().entry(raw).or_insert(0) += 1;
            set.insert(k);
        }
        verse_norms.push(set);
    }
    // Candidate prefixes: every prefix (≥ 4 chars, or the whole token) of
    // every normalised token in the name's verses.
    let mut candidates: HashSet<String> = HashSet::new();
    for set in &verse_norms {
        for k in set {
            let len = k.chars().count();
            for l in 4.min(len)..=len {
                candidates.insert(char_prefix(k, l).to_string());
            }
        }
    }
    let big_n = corpus.n_verses.max(1) as f32;
    let mut scored: Vec<(f32, String)> = Vec::new();
    for p in candidates {
        let covered = verse_norms
            .iter()
            .filter(|set| set.iter().any(|k| k.starts_with(p.as_str())))
            .count() as f32;
        let coverage = covered / n;
        let df = corpus.prefix_df(&p).max(1) as f32;
        let idf = ((big_n / df).ln().max(0.0) / 6.0).min(1.0);
        let short_penalty = if p.chars().count() < 5 { 0.8 } else { 1.0 };
        scored.push((coverage * idf * short_penalty, p));
    }
    // Best score; on ties the longer (more specific) prefix, then lexical.
    scored.sort_by(|a, b| {
        b.0.partial_cmp(&a.0)
            .unwrap()
            .then_with(|| b.1.chars().count().cmp(&a.1.chars().count()))
            .then_with(|| a.1.cmp(&b.1))
    });
    let (score, stem) = scored.first().cloned()?;
    // Runner-up that is not a prefix relative of the winner.
    let runner = scored
        .iter()
        .find(|(_, p)| !(p.starts_with(stem.as_str()) || stem.starts_with(p.as_str())))
        .map(|(s, _)| *s)
        .unwrap_or(0.0);

    // Inflections start with the stem; the bare base form may be a hair shorter
    // than the stem the scoring preferred (மோசே next to the stem மோசேய).
    let stem_len = stem.chars().count();
    let mut forms: BTreeMap<String, u32> = BTreeMap::new();
    for (k, spellings) in &raws {
        let klen = k.chars().count();
        let base_of_stem = stem.starts_with(k.as_str()) && klen >= 4 && stem_len - klen <= 2;
        if k.starts_with(stem.as_str()) || base_of_stem {
            for (raw, c) in spellings {
                *forms.entry(raw.clone()).or_insert(0) += c;
            }
        }
    }
    if forms.is_empty() {
        return None;
    }
    let total: u32 = forms.values().sum();
    let floor = ((total as f32 * 0.05).ceil() as u32).max(2);
    // Label: the shortest well-attested spelling (the nominative is shortest
    // and usually common); fall back to the shortest spelling of all.
    let attested: Vec<(&String, &u32)> = forms.iter().filter(|(_, c)| **c >= floor).collect();
    let mut pool: Vec<(&String, &u32)> = if attested.is_empty() {
        forms.iter().collect()
    } else {
        attested
    };
    // A vocative (…ே) is never the base form when any other spelling is
    // attested — unless the ே-final form is itself the dominant spelling, as
    // with names that simply end in ே (மோசே).
    let top = pool.iter().map(|(_, c)| **c).max().unwrap_or(0);
    let is_vocative = |s: &str, c: u32| s.ends_with('\u{0BC7}') && c * 2 < top;
    if pool.iter().any(|(s, c)| !is_vocative(s, **c)) {
        pool.retain(|(s, c)| !is_vocative(s, **c));
    }
    let label = pool
        .iter()
        .min_by(|a, b| {
            a.0.chars()
                .count()
                .cmp(&b.0.chars().count())
                .then_with(|| b.1.cmp(a.1))
                .then_with(|| a.0.cmp(b.0))
        })
        .map(|(raw, _)| (*raw).clone())?;

    let mut confidence = score;
    if texts.len() == 1 {
        confidence = confidence.min(0.5);
    }
    let review =
        confidence < 0.7 || texts.len() < 3 || (runner > 0.0 && runner / score.max(1e-6) > 0.85);
    let mut list: Vec<(u32, String)> = forms.into_iter().map(|(r, c)| (c, r)).collect();
    list.sort_by(|a, b| b.0.cmp(&a.0).then_with(|| a.1.cmp(&b.1)));
    Some(NameForm {
        label,
        forms: list.into_iter().map(|(_, r)| r).collect(),
        confidence,
        n: texts.len() as u32,
        review,
        community: false,
        owner: false,
    })
}

/// Checks that every inflected form occurs in the version's text for the
/// name's verses. The label itself may be a base form a reviewer chose that
/// the text never uses uninflected. Verses absent from the corpus (fixture
/// builds) are not checked.
pub fn validate(name: &str, form: &NameForm, verse_ids: &[String], corpus: &Corpus) -> Vec<String> {
    let mut problems = Vec::new();
    let texts: Vec<&String> = verse_ids
        .iter()
        .filter_map(|v| corpus.verses.get(v))
        .collect();
    // A partial corpus (fixture build) cannot judge forms drawn from chapters
    // it does not have; only a full corpus validates.
    if texts.is_empty() || texts.len() < verse_ids.len() {
        return problems;
    }
    let mut present = HashSet::new();
    for t in &texts {
        for raw in tokens(t) {
            present.insert(raw);
        }
    }
    for f in form.forms.iter() {
        let nfc: String = unicode_normalization::UnicodeNormalization::nfc(f.as_str()).collect();
        if !present.contains(&nfc) {
            problems.push(format!(
                "{name} [{}]: form {f:?} does not occur in the name's verses",
                corpus.version
            ));
        }
    }
    problems
}
