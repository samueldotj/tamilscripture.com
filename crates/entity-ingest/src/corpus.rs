//! Verse text of one version, read back from the chapter JSON that
//! `usfm-ingest` wrote, plus the token statistics the name aligner needs.

use anyhow::{Context, Result};
use serde_json::Value;
use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::Path;
use unicode_normalization::UnicodeNormalization;

pub struct Corpus {
    pub version: String,
    /// verse id → text (bridged verses share the bridge's text)
    pub verses: HashMap<String, String>,
    /// normalised token → number of verses containing it, ordered for prefix sums
    pub df_sorted: BTreeMap<String, u32>,
    pub n_verses: u32,
}

impl Corpus {
    /// Upper bound on the number of verses containing a token starting with
    /// `prefix` (verses with two such tokens count twice).
    pub fn prefix_df(&self, prefix: &str) -> u32 {
        let mut end = prefix.to_string();
        end.push('\u{10FFFF}');
        self.df_sorted.range(prefix.to_string()..end).map(|(_, c)| *c).sum()
    }
}

pub fn is_word_char(c: char) -> bool {
    c.is_alphanumeric() || ('\u{0B80}'..='\u{0BFF}').contains(&c)
}

/// Raw word tokens (NFC), in order, punctuation dropped.
pub fn tokens(text: &str) -> Vec<String> {
    text.nfc()
        .collect::<String>()
        .split(|c: char| !is_word_char(c))
        .filter(|t| !t.is_empty())
        .map(String::from)
        .collect()
}

pub fn norm(token: &str) -> String {
    tamil_norm::normalize(token)
}

impl Corpus {
    /// Loads every `{dir}/{VERSION}/{BOOK}/{n}.json` that exists. Missing
    /// chapters (fixture builds) are simply absent from `verses`.
    pub fn load(build_dir: &Path, version: &str, books: &[crate::books::Book]) -> Result<Corpus> {
        let mut verses: HashMap<String, String> = HashMap::new();
        for book in books {
            for ch in 1..=book.chapters {
                let path = build_dir.join(version).join(&book.code).join(format!("{ch}.json"));
                if !path.exists() {
                    continue;
                }
                let text = std::fs::read_to_string(&path).with_context(|| format!("reading {}", path.display()))?;
                let d: Value = serde_json::from_str(&text).with_context(|| format!("parsing {}", path.display()))?;
                let mut by_id: BTreeMap<String, String> = BTreeMap::new();
                for block in d["blocks"].as_array().into_iter().flatten() {
                    if block["type"].as_str() != Some("para") {
                        continue;
                    }
                    for seg in block["segments"].as_array().into_iter().flatten() {
                        let (Some(id), Some(t)) = (seg["id"].as_str(), seg["text"].as_str()) else { continue };
                        let e = by_id.entry(id.to_string()).or_default();
                        if !e.is_empty() {
                            e.push(' ');
                        }
                        e.push_str(t);
                    }
                }
                if let Some(bridges) = d["bridges"].as_object() {
                    for (verse, seg) in bridges {
                        if let Some(t) = by_id.get(seg.as_str().unwrap_or("")) {
                            verses.entry(verse.clone()).or_insert_with(|| t.clone());
                        }
                    }
                }
                verses.extend(by_id);
            }
        }
        let mut df_sorted: BTreeMap<String, u32> = BTreeMap::new();
        for text in verses.values() {
            let set: HashSet<String> = tokens(text).iter().map(|t| norm(t)).filter(|n| !n.is_empty()).collect();
            for n in set {
                *df_sorted.entry(n).or_insert(0) += 1;
            }
        }
        let n_verses = verses.len() as u32;
        Ok(Corpus { version: version.to_string(), verses, df_sorted, n_verses })
    }
}
