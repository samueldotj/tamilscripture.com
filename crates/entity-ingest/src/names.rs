//! Tamil surface forms for English place and person names: one entry per
//! English name, shared by every Tamil version.
//!
//! `draft_one()` proposes forms by co-occurrence: a word stem that recurs
//! across the verses where the name occurs and is rare elsewhere is the name.
//! Tamil case suffixes (தமஸ்கு, தமஸ்குவில், தமஸ்குவுக்கு) are handled by
//! scoring shared prefixes of the normalised tokens rather than whole tokens,
//! so every inflection counts towards one candidate. Candidates are always
//! words present in the text. The draft is made from the lead Tamil version
//! (the IRV); `add_forms()` adds the other versions' inflections of the same
//! name. The reviewed file `data/entities/names-ta.toml` is the build input;
//! `validate()` refuses a form that occurs in none of the Tamil versions'
//! text for the name's verses.

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
    /// Verses of the lead version the name occurs in (evidence behind the draft).
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
    /// Set at build time when the draft for a descriptive name is really
    /// another name's word (see `mark_borrowed`); never saved.
    #[serde(skip)]
    pub borrowed: bool,
}

impl NameForm {
    /// Whether the label is trustworthy enough to show without review:
    /// reviewed, or well attested across several verses.
    pub fn display_ok(&self) -> bool {
        if self.community || self.owner {
            return true;
        }
        if self.borrowed {
            return false;
        }
        !self.review || (self.n >= 3 && self.confidence >= 0.4)
    }
}

/// A descriptive English name ("Queen of Sheba", "Canaanite woman", "A wife of
/// Eliphaz") rather than a proper name: it has a connective, or a later word in
/// lower case.
pub fn is_descriptive(name: &str) -> bool {
    let words: Vec<&str> = name.split_whitespace().collect();
    words.len() >= 2
        && words.iter().enumerate().any(|(i, w)| {
            matches!(w.to_lowercase().as_str(), "of" | "the" | "a" | "an")
                || (i > 0 && w.chars().next().is_some_and(char::is_lowercase))
        })
}

/// A descriptive name has no single Tamil word of its own, so when its drafted
/// label is another name's label, or one of that name's inflected forms, the
/// aligner picked up a neighbour: "Queen of Sheba" became சாலொமோன் (Solomon),
/// "Forum of Appius" a verb. Those drafts are hidden and the English name shows
/// until a reviewer supplies a Tamil one. Returns how many names were hidden.
pub fn mark_borrowed(names: &mut NamesTa) -> usize {
    // word → the names that use it as a label, or among their forms
    let mut used: HashMap<String, HashSet<String>> = HashMap::new();
    for (name, f) in names.iter() {
        for w in std::iter::once(&f.label).chain(f.forms.iter()) {
            used.entry(w.clone()).or_default().insert(name.clone());
        }
    }
    let mut marked = 0;
    for (name, f) in names.iter_mut() {
        if !is_descriptive(name) {
            continue;
        }
        let borrowed = used
            .get(&f.label)
            .is_some_and(|owners| owners.iter().any(|o| o != name));
        if borrowed {
            marked += 1;
            f.borrowed = true;
        }
    }
    marked
}

/// English name → its Tamil form, used for every Tamil version.
pub type NamesTa = BTreeMap<String, NameForm>;

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

/// One line per English name, so a reviewer edits one line per name.
pub fn save(path: &Path, names: &NamesTa) -> Result<()> {
    let mut out = String::new();
    for line in [
        "# Tamil names of biblical people and places: one entry per English name,",
        "# used for every Tamil version. Drafted by `entity-ingest --draft-names` from",
        "# the IRV verses where each name occurs; edit `label` (the base form shown on",
        "# maps and titles) and `forms` (every inflected form in the text), then delete",
        "# `review = true`. Every entry in `forms` must occur in the name's verses in",
        "# at least one Tamil version, or the build fails; `n` is the number of verses",
        "# the draft was made from. `translate verses NAME` (tools/translate) shows the",
        "# English and IRV verses side by side.",
        "# Licence: CC BY 4.0 (tamilscripture.com contributors).",
        "",
    ] {
        out.push_str(line);
        out.push('\n');
    }
    for (name, f) in names {
        out.push_str(&format!("{} = {}\n", toml_str(name), entry_line(f)));
    }
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(path, out).with_context(|| format!("writing {}", path.display()))
}

fn entry_line(f: &NameForm) -> String {
    let forms: Vec<String> = f.forms.iter().map(|s| toml_str(s)).collect();
    format!(
        "{{ label = {}, forms = [{}], confidence = {:.2}, n = {}{} }}",
        toml_str(&f.label),
        forms.join(", "),
        f.confidence,
        f.n,
        if f.review { ", review = true" } else { "" }
    )
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
///
/// With `window`, each of the name's verses is read together with the verse
/// either side, since Tamil often carries a clause, and the name, across the
/// verse boundary (Esther 1:10–11).
pub fn draft_one(verse_ids: &[String], corpus: &Corpus, window: bool) -> Option<NameForm> {
    let texts: Vec<String> = verse_ids
        .iter()
        .filter(|v| corpus.verses.contains_key(*v))
        .map(|v| {
            if window {
                with_neighbours(std::slice::from_ref(v))
                    .iter()
                    .filter_map(|x| corpus.verses.get(x))
                    .map(String::as_str)
                    .collect::<Vec<_>>()
                    .join(" ")
            } else {
                corpus.verses[v].clone()
            }
        })
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
        borrowed: false,
    })
}

/// Adds to a draft the inflections another Tamil version uses for the same
/// name: words in that version's verses for the name that start with the
/// draft label's stem (the label less its last letter). Returns how many were
/// added.
pub fn add_forms(form: &mut NameForm, verse_ids: &[String], corpus: &Corpus) -> usize {
    let label = norm(&form.label);
    let len = label.chars().count();
    if len < 3 {
        return 0;
    }
    let stem = char_prefix(&label, (len - 1).max(3)).to_string();
    let mut added = 0;
    for v in verse_ids {
        let Some(t) = corpus.verses.get(v) else {
            continue;
        };
        for raw in tokens(t) {
            if is_tamil_word(&raw)
                && norm(&raw).starts_with(stem.as_str())
                && !form.forms.contains(&raw)
            {
                form.forms.push(raw);
                added += 1;
            }
        }
    }
    added
}

/// NFC with runs of whitespace as one space, for matching phrases.
fn squash(s: &str) -> String {
    let nfc: String = unicode_normalization::UnicodeNormalization::nfc(s).collect();
    nfc.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// The verses and the verse either side of each. Tamil puts the verb last and
/// often moves a clause across a verse boundary: the IRV names Esther's seven
/// chamberlains in 1:11 where the English has them in 1:10.
pub fn with_neighbours(verse_ids: &[String]) -> Vec<String> {
    let mut out = Vec::with_capacity(verse_ids.len() * 3);
    for id in verse_ids {
        out.push(id.clone());
        let mut parts = id.rsplitn(2, '.');
        if let (Some(v), Some(chapter)) = (parts.next(), parts.next()) {
            if let Ok(n) = v.parse::<u32>() {
                if n > 1 {
                    out.push(format!("{chapter}.{}", n - 1));
                }
                out.push(format!("{chapter}.{}", n + 1));
            }
        }
    }
    out
}

/// Checks that every inflected form occurs in the name's verses, or the verse
/// either side, in at least one Tamil version. The label itself may be a base
/// form a reviewer chose that the text never uses uninflected. A corpus missing some of the verses
/// (fixture builds) cannot judge; with no complete corpus nothing is checked.
pub fn validate(
    name: &str,
    form: &NameForm,
    verse_ids: &[String],
    corpora: &[Corpus],
) -> Vec<String> {
    let mut present = HashSet::new();
    // Whole verse texts too, for a form of several words (a reviewer's
    // "பரிசுத்த ஸ்தலத்திற்குள்" for Holy Place), matched as a phrase.
    let mut phrases: Vec<String> = Vec::new();
    let mut judged = false;
    for corpus in corpora {
        let texts: Vec<&String> = verse_ids
            .iter()
            .filter_map(|v| corpus.verses.get(v))
            .collect();
        if texts.is_empty() || texts.len() < verse_ids.len() {
            continue;
        }
        judged = true;
        for t in with_neighbours(verse_ids)
            .iter()
            .filter_map(|v| corpus.verses.get(v))
        {
            for raw in tokens(t) {
                present.insert(raw);
            }
            phrases.push(squash(t));
        }
    }
    if !judged {
        return Vec::new();
    }
    form.forms
        .iter()
        .filter(|f| {
            let nfc = squash(f);
            if nfc.contains(' ') {
                !phrases.iter().any(|t| t.contains(&nfc))
            } else {
                !present.contains(&nfc)
            }
        })
        .map(|f| {
            format!("{name}: form {f:?} does not occur in the name's verses in any Tamil version")
        })
        .collect()
}

#[cfg(test)]
mod borrowed_tests {
    use super::*;

    fn form(label: &str, forms: &[&str]) -> NameForm {
        NameForm {
            label: label.into(),
            forms: forms.iter().map(|f| f.to_string()).collect(),
            confidence: 0.8,
            n: 10,
            review: false,
            community: false,
            owner: false,
            borrowed: false,
        }
    }

    #[test]
    fn forms_are_checked_as_words_or_phrases_in_nearby_verses() {
        let corpus = Corpus {
            version: "IRVTAM".into(),
            verses: [
                (
                    "EXO.26.33".to_string(),
                    "அது பரிசுத்த ஸ்தலத்திற்கும் இடையே".to_string(),
                ),
                (
                    "EXO.26.34".to_string(),
                    "மகா பரிசுத்த  ஸ்தலத்திலே வைப்பாயாக".to_string(),
                ),
            ]
            .into_iter()
            .collect(),
            df_sorted: Default::default(),
            n_verses: 2,
        };
        let verses = ["EXO.26.33".to_string()];
        let ok = form(
            "பரிசுத்த ஸ்தலம்",
            &["பரிசுத்த ஸ்தலத்திற்கும்", "மகா பரிசுத்த ஸ்தலத்திலே", "ஸ்தலத்திலே"],
        );
        assert!(validate("Holy Place", &ok, &verses, std::slice::from_ref(&corpus)).is_empty());
        let bad = form("பரிசுத்த", &["பரிசுத்த இடம்", "ஸ்தலம்"]);
        assert_eq!(
            validate("Holy Place", &bad, &verses, std::slice::from_ref(&corpus)).len(),
            2
        );
    }

    #[test]
    fn neighbours_stay_in_the_chapter() {
        let got = with_neighbours(&["EST.1.10".to_string(), "GEN.1.1".to_string()]);
        assert_eq!(
            got,
            ["EST.1.10", "EST.1.9", "EST.1.11", "GEN.1.1", "GEN.1.2"]
        );
    }

    #[test]
    fn descriptive_names() {
        assert!(is_descriptive("Queen of Sheba"));
        assert!(is_descriptive("Canaanite woman"));
        assert!(is_descriptive("A wife of Eliphaz"));
        assert!(!is_descriptive("Mary Magdalene"));
        assert!(!is_descriptive("Jerusalem"));
    }

    #[test]
    fn a_descriptive_name_using_another_names_word_is_hidden() {
        let mut names = NamesTa::new();
        names.insert("Solomon".into(), form("சாலொமோன்", &["சாலொமோன்", "சாலொமோனின்"]));
        names.insert("Queen of Sheba".into(), form("சாலொமோன்", &["சாலொமோன்"]));
        names.insert("Eliphaz".into(), form("எலிப்பாஸ்", &["எலிப்பாஸ்", "எலிப்பாசின்"]));
        names.insert("A wife of Eliphaz".into(), form("எலிப்பாசின்", &["எலிப்பாசின்"]));
        names.insert("Mary Magdalene".into(), form("மரியாள்", &["மரியாள்"]));
        names.insert("Mary".into(), form("மரியாள்", &["மரியாள்"]));
        assert_eq!(mark_borrowed(&mut names), 2);
        assert!(!names["Queen of Sheba"].display_ok());
        assert!(!names["A wife of Eliphaz"].display_ok());
        // Proper names keep their Tamil, even when shared.
        assert!(names["Solomon"].display_ok());
        assert!(names["Mary Magdalene"].display_ok());
    }
}
