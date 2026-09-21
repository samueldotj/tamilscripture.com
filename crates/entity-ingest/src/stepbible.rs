//! STEPBible's word-tagged Hebrew and Greek texts and their brief lexicons
//! (docs/feature_concordance.md): every word of the Hebrew OT (TAHOT) and the
//! Greek NT (TAGNT) with its Strong's number, and TBESH/TBESG for meanings.
//! The files are fetched by `scripts/fetch-stepbible.mjs` and never committed.
//!
//! STEP numbers verses as the NRSV does; `map_verse` moves the few that differ
//! onto our verse ids, and the caller refuses any tagged verse left without one.

use crate::books::Books;
use anyhow::{Context, Result};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::Path;

/// One word of the original text, in its verse.
#[derive(Debug, Clone)]
pub struct Word {
    /// Our verse id, after versification mapping.
    pub verse: String,
    /// Hebrew or Greek as written, morpheme dividers removed.
    pub text: String,
    pub translit: String,
    pub gloss: String,
    /// The word's own Strong's numbers (STEP's grammar numbers left out).
    pub strongs: Vec<String>,
    pub morph: String,
}

/// A lexicon entry, keyed by the extended ("disambiguated") Strong's number.
#[derive(Debug, Clone, Default)]
pub struct Lexeme {
    pub lemma: String,
    pub translit: String,
    pub pos: String,
    pub gloss: String,
    pub def: String,
}

pub struct StepData {
    pub words: Vec<Word>,
    pub lexicon: HashMap<String, Lexeme>,
    /// Tagged verses whose book we have but whose verse we do not.
    pub unmapped: Vec<String>,
}

/// STEP's own numbers for prefixes, suffixes and punctuation, not Strong's words.
pub fn is_grammar(n: &str) -> bool {
    n.strip_prefix('H')
        .and_then(|d| d.get(..4))
        .and_then(|d| d.parse::<u32>().ok())
        .is_some_and(|d| (9000..=9099).contains(&d))
}

/// `Isa.9.1(8.23)#01=L` → ("Isa.9.1", "L"); the English (NRSV) reference comes
/// first, any other tradition's numbering follows in brackets.
fn split_ref(col: &str) -> Option<(&str, &str)> {
    let (left, right) = col.split_once('#')?;
    let reference = left.split(['(', '[', '{']).next()?;
    let kind = right.split_once('=').map(|(_, k)| k).unwrap_or("");
    Some((reference, kind))
}

/// Our verse id(s) for a STEP (NRSV-numbered) reference.
pub fn map_verse(books: &Books, reference: &str, ours: &HashSet<String>) -> Vec<String> {
    let mut parts = reference.split('.');
    let (Some(b), Some(c), Some(v)) = (parts.next(), parts.next(), parts.next()) else {
        return Vec::new();
    };
    let Some(book) = books.by_code(&b.to_ascii_uppercase()) else {
        return Vec::new();
    };
    let (Ok(ch), Ok(vn)) = (c.parse::<u32>(), v.parse::<u32>()) else {
        return Vec::new();
    };
    let id = |ch: u32, v: u32| format!("{}.{}.{}", book.code, ch, v);
    match (book.code.as_str(), ch, vn) {
        // A psalm's title is verse 0 in the NRSV and the Hebrew; our text
        // carries it with verse 1.
        ("PSA", _, 0) => vec![id(ch, 1)],
        // NRSV Revelation 12:18 is the first half of our 13:1.
        ("REV", 12, 18) if !ours.contains(&id(12, 18)) => vec![id(13, 1)],
        // NRSV 2 Corinthians 13:13 is our 13:13 and 13:14.
        ("2CO", 13, 13) if ours.contains(&id(13, 14)) => vec![id(13, 13), id(13, 14)],
        _ => vec![id(ch, vn)],
    }
}

fn clean(s: &str) -> String {
    s.replace(['/', '\\'], "").trim().to_string()
}

/// The numbers inside `{…}` in a TAHOT Strong's field, else every number
/// that is not a grammar number.
fn hebrew_strongs(field: &str) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    let mut rest = field;
    while let Some(open) = rest.find('{') {
        let Some(close) = rest[open..].find('}') else {
            break;
        };
        out.push(rest[open + 1..open + close].to_string());
        rest = &rest[open + close + 1..];
    }
    if out.is_empty() {
        out = field
            .split(['/', '\\'])
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty() && !is_grammar(s))
            .collect();
    }
    out.retain(|s| valid(s) && !is_grammar(s));
    out
}

pub fn valid(s: &str) -> bool {
    let mut c = s.chars();
    matches!(c.next(), Some('H' | 'G'))
        && s.len() >= 5
        && s[1..5].chars().all(|d| d.is_ascii_digit())
        && s[5..].chars().all(|d| d.is_ascii_alphabetic())
        && s.len() <= 6
}

fn parse_tahot(
    text: &str,
    books: &Books,
    ours: &HashSet<String>,
    have: &HashSet<String>,
    out: &mut Vec<Word>,
    unmapped: &mut Vec<String>,
) {
    for line in text.lines() {
        let cols: Vec<&str> = line.split('\t').collect();
        if cols.len() < 6 {
            continue;
        }
        let Some((reference, kind)) = split_ref(cols[0]) else {
            continue;
        };
        // "X" words are not in the Leningrad text; everything else (L, Q, R …) is.
        if kind.starts_with('X') {
            continue;
        }
        for verse in map_verse(books, reference, ours) {
            let book = verse.split('.').next().unwrap_or("");
            if !have.contains(book) {
                continue;
            }
            if !ours.contains(&verse) {
                unmapped.push(verse);
                continue;
            }
            out.push(Word {
                verse,
                text: clean(cols[1]),
                translit: clean(cols[2]),
                gloss: cols[3]
                    .replace("/ ", " ")
                    .replace('/', " ")
                    .trim()
                    .to_string(),
                strongs: hebrew_strongs(cols[4]),
                morph: cols[5].trim().to_string(),
            });
        }
    }
}

fn parse_tagnt(
    text: &str,
    books: &Books,
    ours: &HashSet<String>,
    have: &HashSet<String>,
    out: &mut Vec<Word>,
    unmapped: &mut Vec<String>,
) {
    for line in text.lines() {
        let cols: Vec<&str> = line.split('\t').collect();
        if cols.len() < 6 {
            continue;
        }
        let Some((reference, _)) = split_ref(cols[0]) else {
            continue;
        };
        // The words of the critical text (NA28) or the Received Text (TR);
        // readings found only elsewhere are left out.
        if !(cols[5].contains("NA28") || cols[5].contains("TR")) {
            continue;
        }
        let (greek, translit) = match cols[1].split_once(" (") {
            Some((g, t)) => (
                g.trim().to_string(),
                t.trim_end_matches(')').trim().to_string(),
            ),
            None => (cols[1].trim().to_string(), String::new()),
        };
        let (num, morph) = cols[3].split_once('=').unwrap_or((cols[3], ""));
        let strongs: Vec<String> = Some(num.trim().to_string())
            .filter(|s| valid(s))
            .into_iter()
            .collect();
        for verse in map_verse(books, reference, ours) {
            let book = verse.split('.').next().unwrap_or("");
            if !have.contains(book) {
                continue;
            }
            if !ours.contains(&verse) {
                unmapped.push(verse);
                continue;
            }
            out.push(Word {
                verse,
                text: greek.clone(),
                translit: translit.clone(),
                gloss: cols[2].trim().to_string(),
                strongs: strongs.clone(),
                morph: morph.trim().to_string(),
            });
        }
    }
}

/// Plain text from the lexicon's light HTML, line breaks kept, cut at a word.
fn definition(html: &str, max: usize) -> String {
    let with_breaks = html
        .replace("<br>", "\n")
        .replace("<BR>", "\n")
        .replace("<BR />", "\n")
        .replace("<br />", "\n")
        .replace("<lb />", "\n");
    let mut out = String::new();
    let mut in_tag = false;
    for c in with_breaks.chars() {
        match c {
            '<' => in_tag = true,
            '>' => in_tag = false,
            _ if !in_tag => out.push(c),
            _ => {}
        }
    }
    let lines: Vec<String> = out
        .lines()
        .map(|l| l.split_whitespace().collect::<Vec<_>>().join(" "))
        .filter(|l| !l.is_empty())
        .collect();
    let text = lines.join("\n");
    if text.chars().count() <= max {
        return text;
    }
    let cut: String = text.chars().take(max).collect();
    match cut.rfind(char::is_whitespace) {
        Some(i) => format!("{} …", &cut[..i]),
        None => format!("{cut} …"),
    }
}

fn parse_lexicon(text: &str, into: &mut HashMap<String, Lexeme>) {
    for line in text.lines() {
        let cols: Vec<&str> = line.split('\t').collect();
        if cols.len() < 8 || !valid(cols[0].trim()) {
            continue;
        }
        let key = cols[1].split_whitespace().next().unwrap_or("").to_string();
        if !valid(&key) || into.contains_key(&key) {
            continue;
        }
        into.insert(
            key,
            Lexeme {
                lemma: cols[3].trim().to_string(),
                translit: cols[4].trim().to_string(),
                pos: cols[5].trim().to_string(),
                gloss: cols[6].trim().to_string(),
                def: definition(cols[7], 1500),
            },
        );
    }
}

/// The lexicon entry for a tag: the exact extended number, else the plain
/// number, else its first extension.
pub fn lookup<'a>(lexicon: &'a HashMap<String, Lexeme>, n: &str) -> Option<&'a Lexeme> {
    lexicon
        .get(n)
        .or_else(|| lexicon.get(&n[..5]))
        .or_else(|| lexicon.get(&format!("{}G", &n[..5])))
}

/// Loads everything, or `None` when the files have not been fetched.
pub fn load(dir: &Path, books: &Books, ours: &HashSet<String>) -> Result<Option<StepData>> {
    let names = [
        "TAHOT-1-Gen-Deu.txt",
        "TAHOT-2-Jos-Est.txt",
        "TAHOT-3-Job-Sng.txt",
        "TAHOT-4-Isa-Mal.txt",
        "TAGNT-1-Mat-Jhn.txt",
        "TAGNT-2-Act-Rev.txt",
        "TBESH.txt",
        "TBESG.txt",
    ];
    if names.iter().any(|n| !dir.join(n).exists()) {
        return Ok(None);
    }
    let read =
        |n: &str| std::fs::read_to_string(dir.join(n)).with_context(|| format!("reading {n}"));
    // Books present in our text (the fixture build has three).
    let have: HashSet<String> = ours
        .iter()
        .filter_map(|v| v.split('.').next().map(str::to_string))
        .collect();
    let mut words = Vec::new();
    let mut unmapped = Vec::new();
    for n in &names[..4] {
        parse_tahot(&read(n)?, books, ours, &have, &mut words, &mut unmapped);
    }
    for n in &names[4..6] {
        parse_tagnt(&read(n)?, books, ours, &have, &mut words, &mut unmapped);
    }
    let mut lexicon = HashMap::new();
    parse_lexicon(&read("TBESH.txt")?, &mut lexicon);
    parse_lexicon(&read("TBESG.txt")?, &mut lexicon);
    unmapped.sort();
    unmapped.dedup();
    Ok(Some(StepData {
        words,
        lexicon,
        unmapped,
    }))
}

/// File name for a Strong's number. STEP continues its disambiguating letters
/// in lower case (H1121A and H1121a are different words), which collide on
/// case-insensitive file systems, so a lower-case letter gets an underscore.
pub fn file_name(n: &str) -> String {
    match n.chars().last() {
        Some(c) if c.is_ascii_lowercase() => format!("{}_{c}", &n[..n.len() - 1]),
        _ => n.to_string(),
    }
}

/// Canonical sort key for a verse id.
pub fn verse_key(books: &Books, v: &str) -> u32 {
    let mut it = v.split('.');
    let order = it
        .next()
        .and_then(|c| books.by_code(c))
        .map(|b| b.order)
        .unwrap_or(99);
    let ch: u32 = it.next().and_then(|x| x.parse().ok()).unwrap_or(0);
    let vs: u32 = it.next().and_then(|x| x.parse().ok()).unwrap_or(0);
    order * 1_000_000 + ch * 1000 + vs
}

/// Per Strong's number: the verses it occurs in, in canonical order, with the
/// surface form it takes in each, and how many words carry it.
pub struct Occurrences {
    pub verses: Vec<(u32, String, String)>,
    pub count: usize,
}

pub fn occurrences(books: &Books, words: &[Word]) -> BTreeMap<String, Occurrences> {
    let mut out: BTreeMap<String, Occurrences> = BTreeMap::new();
    let mut seen: HashSet<(String, String)> = HashSet::new();
    for w in words {
        for n in &w.strongs {
            let o = out.entry(n.clone()).or_insert(Occurrences {
                verses: Vec::new(),
                count: 0,
            });
            o.count += 1;
            if seen.insert((n.clone(), w.verse.clone())) {
                o.verses
                    .push((verse_key(books, &w.verse), w.verse.clone(), w.text.clone()));
            }
        }
    }
    for o in out.values_mut() {
        o.verses.sort_by_key(|(k, _, _)| *k);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn references_and_numbers() {
        assert_eq!(split_ref("Isa.9.1(8.23)#01=L"), Some(("Isa.9.1", "L")));
        assert_eq!(split_ref("Mat.15.6{15.5}#01=k"), Some(("Mat.15.6", "k")));
        assert_eq!(hebrew_strongs("H9003/{H7225G}"), vec!["H7225G"]);
        assert_eq!(hebrew_strongs("{H0168G}/H9023\\H9016"), vec!["H0168G"]);
        assert_eq!(hebrew_strongs("H0853"), vec!["H0853"]);
        assert!(is_grammar("H9016") && !is_grammar("H0853") && !is_grammar("G9016"));
        assert!(valid("G3972G") && valid("H0085") && !valid("G2532_a"));
        assert_eq!(file_name("H1121a"), "H1121_a");
        assert_eq!(file_name("H1121A"), "H1121A");
    }

    #[test]
    fn definitions_are_plain_and_cut() {
        assert_eq!(
            definition("1) father<br>2) <b>ancestor</b>", 100),
            "1) father\n2) ancestor"
        );
        assert!(definition(&"word ".repeat(400), 30).ends_with('…'));
    }
}
