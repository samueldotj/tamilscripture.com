//! Aquifer Open Bible Dictionary (Mission Mutual, CC BY-SA 4.0; an adaptation
//! of the Tyndale Open Bible Dictionary). ShareAlike source: it lives in its
//! own directory with its own licence and is never merged into a
//! public-domain file (feature_dictionary.md §2). Read from
//! `data/entities/aquifer/src/eng/json/*.content.json`.

use anyhow::{Context, Result};
use serde::Deserialize;
use std::collections::BTreeMap;
use std::path::Path;

use crate::articles::{fnv8, paragraphs, Article, Paragraph};

pub const KEY: &str = "aquifer";
pub const ATTRIBUTION: &str = "Aquifer Open Bible Dictionary © 2026 Mission Mutual, CC BY-SA 4.0; an adaptation of Tyndale Open Bible Dictionary © 2023 Tyndale House Publishers, CC BY-SA 4.0";

#[derive(Deserialize)]
struct Entry {
    #[serde(default)]
    title: String,
    #[serde(default)]
    index_reference: String,
    #[serde(default)]
    content: String,
    #[serde(default)]
    associations: Assoc,
}

#[derive(Deserialize, Default)]
struct Assoc {
    #[serde(default)]
    passage: Vec<Passage>,
    #[serde(default)]
    acai: Vec<Acai>,
}

#[derive(Deserialize)]
struct Passage {
    #[serde(default)]
    start_ref_usfm: String,
    #[serde(default)]
    end_ref_usfm: String,
}

/// ACAI entity hint: `person:Aaron`, `place:Damascus`.
#[derive(Deserialize)]
struct Acai {
    #[serde(default, rename = "type")]
    kind: String,
    #[serde(default)]
    preferred_label: String,
    #[serde(default)]
    confidence: f32,
}

pub fn load(dir: &Path) -> Result<Vec<Article>> {
    let json_dir = dir.join("src/eng/json");
    let mut files: Vec<_> = std::fs::read_dir(&json_dir)
        .with_context(|| format!("reading {}", json_dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|x| x == "json"))
        .collect();
    files.sort();
    let mut out = Vec::new();
    let mut seen: BTreeMap<String, usize> = BTreeMap::new();
    for path in files {
        let text = std::fs::read_to_string(&path)?;
        let entries: Vec<Entry> =
            serde_json::from_str(&text).with_context(|| format!("parsing {}", path.display()))?;
        for e in entries {
            let title = e.title.trim().to_string();
            if title.is_empty() || e.content.trim().is_empty() {
                continue;
            }
            let mut slug = slugify(if e.index_reference.is_empty() {
                &title
            } else {
                &e.index_reference
            });
            if slug.is_empty() {
                continue;
            }
            if let Some(n) = seen.get_mut(&slug) {
                *n += 1;
                slug = format!("{slug}-{n}");
            } else {
                seen.insert(slug.clone(), 1);
            }
            let id = format!("{KEY}/{slug}");
            let blocks = html_blocks(&e.content, &title);
            let mut n = 0;
            let mut paras: Vec<Paragraph> = Vec::new();
            for (heading, text) in blocks {
                let pieces = if heading {
                    vec![text]
                } else {
                    paragraphs(&text)
                };
                for p in pieces {
                    n += 1;
                    paras.push(Paragraph {
                        id: format!("{id}#p{n}-{}", fnv8(&p)),
                        text: p,
                        heading,
                        ta: None,
                        ta_source: None,
                    });
                }
            }
            if paras.is_empty() {
                continue;
            }
            let full: String = paras
                .iter()
                .map(|p| p.text.as_str())
                .collect::<Vec<_>>()
                .join("\n");
            let refs: Vec<String> = e
                .associations
                .passage
                .iter()
                .filter(|p| !p.start_ref_usfm.is_empty())
                .map(|p| {
                    if p.end_ref_usfm.is_empty() || p.end_ref_usfm == p.start_ref_usfm {
                        p.start_ref_usfm.clone()
                    } else {
                        format!("{}–{}", p.start_ref_usfm, p.end_ref_usfm)
                    }
                })
                .collect();
            let hints: Vec<(String, String)> = e
                .associations
                .acai
                .iter()
                .filter(|a| a.confidence >= 0.8 && matches!(a.kind.as_str(), "person" | "place"))
                .map(|a| (a.kind.clone(), a.preferred_label.trim().to_lowercase()))
                .filter(|(_, name)| !name.is_empty())
                .collect();
            out.push(Article {
                source: KEY.to_string(),
                id,
                slug,
                title,
                title_ta: None,
                lang: "en",
                licence: "CC BY-SA 4.0",
                attribution: ATTRIBUTION,
                entities: Vec::new(),
                hints,
                paragraphs: paras,
                refs,
                hash: fnv8(&full),
                also_in: Vec::new(),
            });
        }
    }
    Ok(out)
}

fn slugify(s: &str) -> String {
    let mut out = String::new();
    let mut dash = true;
    for c in s.to_lowercase().chars() {
        if c.is_ascii_alphanumeric() {
            out.push(c);
            dash = false;
        } else if !dash {
            out.push('-');
            dash = true;
        }
    }
    out.trim_end_matches('-').to_string()
}

/// Split simple article HTML into (is_heading, text) blocks. The `<h1>` that
/// repeats the title is dropped; `<h2>`–`<h4>` become heading blocks; `<p>`,
/// `<li>`, `<blockquote>` and table rows become body blocks. Other tags are
/// removed and entities decoded.
fn html_blocks(html: &str, title: &str) -> Vec<(bool, String)> {
    let mut blocks: Vec<(bool, String)> = Vec::new();
    let mut cur = String::new();
    let mut heading = false;
    let mut skip_h1 = false;
    let flush = |cur: &mut String, heading: bool, skip: bool, blocks: &mut Vec<(bool, String)>| {
        let t = cur.split_whitespace().collect::<Vec<_>>().join(" ");
        if !t.is_empty() && !skip {
            blocks.push((heading, t));
        }
        cur.clear();
    };
    let mut rest = html;
    while let Some(lt) = rest.find('<') {
        cur.push_str(&decode(&rest[..lt]));
        rest = &rest[lt..];
        let Some(gt) = rest.find('>') else { break };
        let tag = &rest[1..gt];
        rest = &rest[gt + 1..];
        let name: String = tag
            .trim_start_matches('/')
            .chars()
            .take_while(|c| c.is_ascii_alphanumeric())
            .collect::<String>()
            .to_lowercase();
        let closing = tag.starts_with('/');
        match name.as_str() {
            "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "p" | "li" | "blockquote" | "tr" | "div" => {
                flush(&mut cur, heading, skip_h1, &mut blocks);
                if closing {
                    heading = false;
                    skip_h1 = false;
                } else {
                    heading = name.starts_with('h') && name != "hr";
                    skip_h1 = name == "h1";
                }
            }
            "br" => cur.push(' '),
            "td" | "th" => cur.push(' '),
            _ => {}
        }
    }
    cur.push_str(&decode(rest));
    flush(&mut cur, heading, skip_h1, &mut blocks);
    // A leading heading identical to the title adds nothing.
    if let Some((true, t)) = blocks.first() {
        if t.eq_ignore_ascii_case(title) {
            blocks.remove(0);
        }
    }
    blocks
}

fn decode(s: &str) -> String {
    if !s.contains('&') {
        return s.to_string();
    }
    let mut out = String::with_capacity(s.len());
    let mut rest = s;
    while let Some(amp) = rest.find('&') {
        out.push_str(&rest[..amp]);
        rest = &rest[amp..];
        let Some(semi) = rest.find(';').filter(|&i| i <= 10) else {
            out.push('&');
            rest = &rest[1..];
            continue;
        };
        let ent = &rest[1..semi];
        let repl = match ent {
            "amp" => Some('&'),
            "lt" => Some('<'),
            "gt" => Some('>'),
            "quot" => Some('"'),
            "apos" => Some('\''),
            "nbsp" => Some(' '),
            _ => ent
                .strip_prefix('#')
                .and_then(|n| {
                    if let Some(h) = n.strip_prefix('x').or_else(|| n.strip_prefix('X')) {
                        u32::from_str_radix(h, 16).ok()
                    } else {
                        n.parse().ok()
                    }
                })
                .and_then(char::from_u32),
        };
        match repl {
            Some(c) => out.push(c),
            None => out.push_str(&rest[..=semi]),
        }
        rest = &rest[semi + 1..];
    }
    out.push_str(rest);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn blocks_from_html() {
        let html = r#"<h1>AARON</h1><p>Aaron was the brother of <data class="bible-ref">Moses</data>.</p><h2>Family &amp; Life</h2><p>He had four sons (<data>Exodus 6:23</data>).</p><ul><li>One</li><li>Two</li></ul>"#;
        let b = html_blocks(html, "Aaron");
        assert_eq!(
            b,
            vec![
                (false, "Aaron was the brother of Moses.".to_string()),
                (true, "Family & Life".to_string()),
                (false, "He had four sons (Exodus 6:23).".to_string()),
                (false, "One".to_string()),
                (false, "Two".to_string()),
            ]
        );
    }

    #[test]
    fn slugs() {
        assert_eq!(slugify("abelbethmaacah maachah"), "abelbethmaacah-maachah");
        assert_eq!(slugify("Abdon (place)"), "abdon-place");
        assert_eq!(decode("Aaron&apos;s &#8211; &#x2014;"), "Aaron's – —");
    }
}
