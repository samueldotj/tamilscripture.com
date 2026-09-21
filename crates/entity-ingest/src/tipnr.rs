//! STEP Bible TIPNR (Translators Individualised Proper Names with all
//! References), CC BY 4.0. A tab-separated text file: records start after a
//! `$=====KIND` line; the first line is the header (38 columns), then
//! `– Significance` sub-records with the original-language forms and their
//! verse lists, then `@Brief=`, `@Short=`, `@Article=` descriptions.
//!
//! People become entities of their own; place records only lend their
//! descriptions to the OpenBible places they match.

use crate::books::Books;
use anyhow::{Context, Result};
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

#[derive(Debug, Clone)]
pub struct NameForm {
    /// Named, Greek, Spelled, Group, Aramaic …
    pub significance: String,
    /// e.g. `H0175` (disambiguated Strong's)
    pub strongs: String,
    /// Original-language spelling
    pub original: String,
    /// `he` or `el`
    pub script: String,
    /// English rendering(s) as given, e.g. `Bethlehem =ESV,NIV; Beth-lehem =KJV`
    pub translated: String,
    pub verses: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct Person {
    /// `Name@Ref` without the last-book suffix, e.g. `Zechariah@1Ch.24.25`
    pub key: String,
    pub name_en: String,
    /// First reference in TIPNR form, e.g. `1Ch.24.25`
    pub first_ref: String,
    /// male · female · group
    pub gender: String,
    pub description: String,
    pub parents: Vec<String>,
    pub siblings: Vec<String>,
    pub partners: Vec<String>,
    pub children: Vec<String>,
    pub tribe: String,
    /// Plain-text summary (markup stripped)
    pub summary: String,
    pub brief: String,
    pub short: String,
    pub article: String,
    pub forms: Vec<NameForm>,
    /// Verse ids `GEN.1.1`, canonical order, unique
    pub verses: Vec<String>,
    pub uncertain: bool,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct TipnrPlace {
    pub name_en: String,
    pub description: String,
    pub brief: String,
    pub short: String,
    pub article: String,
    pub forms: Vec<NameForm>,
    pub verses: Vec<String>,
}

pub struct Tipnr {
    pub people: Vec<Person>,
    pub places: Vec<TipnrPlace>,
}

/// `Exo.7.10a` → `EXO.7.10`; None when the book is unknown.
fn verse_id(books: &Books, r: &str) -> Option<(u32, u32, u32, String)> {
    let r = r.trim();
    let mut parts = r.split('.');
    let (b, c, v) = (parts.next()?, parts.next()?, parts.next()?);
    let code = b.to_ascii_uppercase();
    let book = books.by_code(&code)?;
    let ch: u32 = c.parse().ok()?;
    let digits: String = v.chars().take_while(|c| c.is_ascii_digit()).collect();
    let vn: u32 = digits.parse().ok()?;
    Some((book.order, ch, vn, format!("{}.{}.{}", book.code, ch, vn)))
}

/// Strip `<ref="…">`, `<strong="…">`, `<br>` and other tags to plain text.
pub fn strip_markup(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut in_tag = false;
    for c in s.chars() {
        match c {
            '<' => in_tag = true,
            '>' => in_tag = false,
            _ if !in_tag => out.push(c),
            _ => {}
        }
    }
    // `<br>` became nothing; collapse whitespace and stray ") " artefacts.
    let collapsed: Vec<&str> = out.split_whitespace().collect();
    collapsed.join(" ").replace(" )", ")").replace("( ", "(")
}

/// `Amram@Exo.6.18-1Ch(d)` → `Amram@Exo.6.18`
fn relation_key(token: &str) -> Option<String> {
    let t = token.trim();
    if t.is_empty() {
        return None;
    }
    // drop annotations like (d), (a), (f), (?)
    let t = t.split('(').next().unwrap_or(t).trim();
    let (name, rest) = t.split_once('@')?;
    let first = rest.split('-').next().unwrap_or(rest);
    if name.is_empty() || first.is_empty() {
        return None;
    }
    Some(format!("{name}@{first}"))
}

/// A TIPNR identifier as a reader should see it: underscores are word gaps, a
/// leading "a"/"an" is dropped ("a_wife_of_Eliphaz" is "Wife of Eliphaz"), and
/// the designation starts a line, so it starts upper.
fn display_name(ident: &str) -> String {
    let spaced = ident.replace('_', " ");
    let spaced = spaced
        .strip_prefix("a ")
        .or_else(|| spaced.strip_prefix("an "))
        .map(str::to_string)
        .unwrap_or(spaced);
    let mut chars = spaced.chars();
    match chars.next() {
        Some(first) if first.is_lowercase() => {
            first.to_uppercase().collect::<String>() + chars.as_str()
        }
        _ => spaced,
    }
}

fn relation_list(field: &str) -> Vec<String> {
    field.split([',', '+']).filter_map(relation_key).collect()
}

pub fn load(path: &Path, books: &Books) -> Result<Tipnr> {
    let text =
        std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    let lines: Vec<&str> = text.lines().collect();
    let mut people = Vec::new();
    let mut places = Vec::new();
    let mut i = 0;
    while i < lines.len() {
        let line = lines[i];
        if !line.starts_with("$=====") {
            i += 1;
            continue;
        }
        let kind = line.trim_start_matches(['$', '=']).trim().to_string();
        // Collect the record: lines until the next `$` line.
        let mut j = i + 1;
        let mut rec: Vec<&str> = Vec::new();
        while j < lines.len() && !lines[j].starts_with('$') {
            if !lines[j].trim().is_empty() {
                rec.push(lines[j]);
            }
            j += 1;
        }
        i = j;
        let Some(head_line) = rec.first() else {
            continue;
        };
        let head: Vec<&str> = head_line.split('\t').collect();
        // Skip the column-description header rows and the excluded kinds.
        if head[0].starts_with("UnifiedName") || head[0].starts_with("UniqueName") {
            continue;
        }
        let is_person = kind.starts_with("PERSON");
        let is_place = kind == "PLACE";
        if !is_person && !is_place {
            continue;
        }
        let Some((ident, _strong)) = head[0].split_once('=') else {
            continue;
        };
        let uncertain = ident.contains("(?)");
        let ident = ident.replace("(?)", "");
        let Some((name_en, rest)) = ident.split_once('@') else {
            continue;
        };
        // TIPNR joins a designation's words with underscores ("a_wife_of_Eliphaz",
        // "Queen_of_Sheba"). Those are for its own keys, not for reading.
        let display = display_name(name_en);
        let first_ref = rest.split('-').next().unwrap_or(rest).to_string();
        let col = |n: usize| head.get(n).map(|s| s.trim()).unwrap_or("");

        let mut forms = Vec::new();
        let mut verses: BTreeSet<(u32, u32, u32, String)> = BTreeSet::new();
        let (mut brief, mut short, mut article) = (String::new(), String::new(), String::new());
        for l in &rec[1..] {
            if let Some(rest) = l.strip_prefix("@Brief=") {
                brief = rest.trim().to_string();
            } else if let Some(rest) = l.strip_prefix("@Short=") {
                short = strip_markup(rest.split('\t').next().unwrap_or("").trim());
            } else if let Some(rest) = l.strip_prefix("@Article=") {
                article = strip_markup(rest.trim()).replace("<BR>", "\n");
            } else if l.starts_with("– ") {
                let f: Vec<&str> = l.split('\t').collect();
                let significance = f[0].trim_start_matches("– ").trim().to_string();
                if significance == "Total" || significance == "Significance" {
                    continue;
                }
                let strong_field = f.get(2).map(|s| s.trim()).unwrap_or("");
                let (strongs, original) = match strong_field.split_once('=') {
                    Some((s, o)) => (s.split('«').next().unwrap_or(s).to_string(), o.to_string()),
                    None => (strong_field.to_string(), String::new()),
                };
                let script = if strongs.starts_with('G') { "el" } else { "he" }.to_string();
                let translated = f.get(3).map(|s| s.trim()).unwrap_or("").to_string();
                let mut vs = Vec::new();
                for r in f.get(4).map(|s| s.split(';')).into_iter().flatten() {
                    if let Some(t) = verse_id(books, r) {
                        vs.push(t.3.clone());
                        verses.insert(t);
                    }
                }
                forms.push(NameForm {
                    significance,
                    strongs,
                    original,
                    script,
                    translated,
                    verses: vs,
                });
            }
        }
        // Article may contain <BR> separators that strip_markup removed; keep
        // the STEP text as paragraphs split on the original <BR>.
        let article = if article.is_empty() {
            rec.iter()
                .find_map(|l| l.strip_prefix("@Article="))
                .map(|a| {
                    a.trim()
                        .split("<BR>")
                        .map(strip_markup)
                        .filter(|p| !p.is_empty())
                        .collect::<Vec<_>>()
                        .join("\n")
                })
                .unwrap_or_default()
        } else {
            article
        };
        let verses: Vec<String> = verses.into_iter().map(|(_, _, _, id)| id).collect();

        if is_person {
            let gender = match col(8) {
                "Female" => "female",
                "Group" => "group",
                _ => "male",
            }
            .to_string();
            people.push(Person {
                key: format!("{name_en}@{first_ref}"),
                name_en: display,
                first_ref,
                gender,
                description: col(1).to_string(),
                parents: relation_list(col(2)),
                siblings: relation_list(col(3)),
                partners: relation_list(col(4)),
                children: relation_list(col(5)),
                tribe: col(6).trim_start_matches('>').trim().to_string(),
                summary: strip_markup(col(7).trim_start_matches('#')),
                brief,
                short,
                article,
                forms,
                verses,
                uncertain,
            });
        } else {
            places.push(TipnrPlace {
                name_en: display,
                description: col(1).to_string(),
                brief,
                short,
                article,
                forms,
                verses,
            });
        }
    }
    people.sort_by(|a, b| {
        a.name_en
            .cmp(&b.name_en)
            .then_with(|| a.first_ref.cmp(&b.first_ref))
    });
    Ok(Tipnr { people, places })
}

/// Unique slug per person: the bare name when only one person carries it,
/// otherwise the name plus the first reference (`zechariah-1ch-24-25`).
pub fn person_slugs(people: &[Person]) -> BTreeMap<String, String> {
    let mut count: BTreeMap<String, usize> = BTreeMap::new();
    for p in people {
        *count.entry(p.name_en.to_lowercase()).or_insert(0) += 1;
    }
    let slugify = |s: &str| -> String {
        let mut out = String::new();
        let mut dash = false;
        for c in s.chars() {
            if c.is_ascii_alphanumeric() {
                out.push(c.to_ascii_lowercase());
                dash = false;
            } else if !dash && !out.is_empty() {
                out.push('-');
                dash = true;
            }
        }
        out.trim_end_matches('-').to_string()
    };
    let mut used: BTreeSet<String> = BTreeSet::new();
    let mut slugs = BTreeMap::new();
    for p in people {
        let base = slugify(&p.name_en);
        let mut slug = if count[&p.name_en.to_lowercase()] == 1 {
            base.clone()
        } else {
            format!("{base}-{}", slugify(&p.first_ref))
        };
        while !used.insert(slug.clone()) {
            slug.push_str("-x");
        }
        slugs.insert(p.key.clone(), slug);
    }
    slugs
}
