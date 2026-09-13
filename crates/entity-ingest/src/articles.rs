//! Dictionary articles with stable paragraph ids (feature_dictionary.md §3).
//! Sources: Easton's Bible Dictionary from the NEUU dataset; STEP Bible's
//! TIPNR descriptions are attached to entities directly and are not articles.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::path::Path;

#[derive(Debug, Clone, Serialize)]
pub struct Paragraph {
    pub id: String,
    pub text: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct Article {
    pub source: String,
    /// `eastons/damascus`
    pub id: String,
    pub slug: String,
    pub title: String,
    pub lang: &'static str,
    pub licence: &'static str,
    pub attribution: &'static str,
    /// `{type}/{id}` of linked entities, filled in by the build
    pub entities: Vec<String>,
    pub paragraphs: Vec<Paragraph>,
    /// Scripture references as `Book 1:2` strings from the source
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub refs: Vec<String>,
    /// FNV-1a of the full source text, for draft staleness checks
    pub hash: String,
}

#[derive(Debug, Deserialize)]
struct BlockEntry {
    source: String,
    id: String,
    #[allow(dead_code)]
    reason: Option<String>,
}
#[derive(Debug, Deserialize, Default)]
struct BlockFile {
    #[serde(default)]
    block: Vec<BlockEntry>,
}

pub fn load_blocklist(path: &Path) -> Result<Vec<(String, String)>> {
    if !path.exists() {
        return Ok(Vec::new());
    }
    let f: BlockFile = toml::from_str(&std::fs::read_to_string(path)?)
        .with_context(|| format!("parsing {}", path.display()))?;
    Ok(f.block.into_iter().map(|b| (b.source, b.id)).collect())
}

pub fn fnv8(s: &str) -> String {
    let mut h: u64 = 0xcbf29ce484222325;
    for b in s.as_bytes() {
        h ^= *b as u64;
        h = h.wrapping_mul(0x100000001b3);
    }
    format!("{:016x}", h)[..8].to_string()
}

/// Split an entry into reviewable paragraphs: at numbered senses `(1.)`,
/// then at sentence ends when a piece runs past ~700 characters.
pub fn paragraphs(text: &str) -> Vec<String> {
    let text = text.split_whitespace().collect::<Vec<_>>().join(" ");
    // Sense markers like "(1.)" "(2.)" start a new paragraph (keep the marker).
    let mut pieces: Vec<String> = Vec::new();
    let mut cur = String::new();
    let chars: Vec<char> = text.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        if chars[i] == '(' {
            // look ahead for digits followed by ".)"
            let mut k = i + 1;
            while k < chars.len() && chars[k].is_ascii_digit() {
                k += 1;
            }
            if k > i + 1
                && k + 1 < chars.len()
                && chars[k] == '.'
                && chars[k + 1] == ')'
                && !cur.trim().is_empty()
            {
                pieces.push(cur.trim().to_string());
                cur = String::new();
            }
        }
        cur.push(chars[i]);
        i += 1;
    }
    if !cur.trim().is_empty() {
        pieces.push(cur.trim().to_string());
    }
    // Long pieces: cut at sentence boundaries into ~700-character paragraphs.
    let mut out = Vec::new();
    for piece in pieces {
        if piece.chars().count() <= 900 {
            out.push(piece);
            continue;
        }
        let mut para = String::new();
        let mut sentence = String::new();
        let pc: Vec<char> = piece.chars().collect();
        for (n, c) in pc.iter().enumerate() {
            sentence.push(*c);
            let end = matches!(c, '.' | '?' | '!')
                && pc.get(n + 1).is_none_or(|nx| nx.is_whitespace())
                && !sentence.trim_end().ends_with("B.C.")
                && !sentence.trim_end().ends_with("A.D.");
            if end {
                if para.chars().count() + sentence.chars().count() > 700 && !para.is_empty() {
                    out.push(para.trim().to_string());
                    para = String::new();
                }
                para.push_str(&sentence);
                sentence.clear();
            }
        }
        para.push_str(&sentence);
        if !para.trim().is_empty() {
            out.push(para.trim().to_string());
        }
    }
    out
}

/// Easton's Bible Dictionary from `data/entities/eastons/src/{a..z}.json`.
pub fn load_eastons(dir: &Path) -> Result<Vec<Article>> {
    let mut out = Vec::new();
    let mut entries = std::fs::read_dir(dir.join("src"))
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| {
            p.extension().is_some_and(|x| x == "json")
                && !p
                    .file_name()
                    .is_some_and(|n| n.to_string_lossy().starts_with('_'))
        })
        .collect::<Vec<_>>();
    entries.sort();
    let mut seen_slugs: BTreeMap<String, usize> = BTreeMap::new();
    for path in entries {
        let text = std::fs::read_to_string(&path)?;
        let d: Value =
            serde_json::from_str(&text).with_context(|| format!("parsing {}", path.display()))?;
        let Some(map) = d.as_object() else { continue };
        for (_key, e) in map {
            let title = e["name"].as_str().unwrap_or("").trim().to_string();
            if title.is_empty() {
                continue;
            }
            let mut slug = e["slug"].as_str().unwrap_or("").to_string();
            if slug.is_empty() {
                slug = title
                    .to_lowercase()
                    .chars()
                    .map(|c| if c.is_ascii_alphanumeric() { c } else { '-' })
                    .collect();
            }
            if let Some(n) = seen_slugs.get_mut(&slug) {
                *n += 1;
                slug = format!("{slug}-{n}");
            } else {
                seen_slugs.insert(slug.clone(), 1);
            }
            let full: Vec<String> = e["definitions"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(|d| d["text"].as_str().map(|s| s.trim().to_string()))
                .filter(|s| !s.is_empty())
                .collect();
            let full_text = full.join("\n");
            if full_text.is_empty() {
                continue;
            }
            let id = format!("eastons/{slug}");
            let mut n = 0;
            let paragraphs = full
                .iter()
                .flat_map(|d| paragraphs(d))
                .map(|p| {
                    n += 1;
                    Paragraph {
                        id: format!("{id}#p{n}-{}", fnv8(&p)),
                        text: p,
                    }
                })
                .collect();
            let refs = e["scripture_refs"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(|r| r["reference"].as_str().map(String::from))
                .collect();
            out.push(Article {
                source: "eastons".to_string(),
                id,
                slug,
                title,
                lang: "en",
                licence: "PD",
                attribution:
                    "Easton's Bible Dictionary (1897), public domain; dataset by NEUU, CC BY 4.0",
                entities: Vec::new(),
                paragraphs,
                refs,
                hash: fnv8(&full_text),
            });
        }
    }
    out.sort_by(|a, b| {
        a.title
            .to_lowercase()
            .cmp(&b.title.to_lowercase())
            .then_with(|| a.id.cmp(&b.id))
    });
    Ok(out)
}
