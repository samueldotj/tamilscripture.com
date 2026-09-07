//! Bible reference parsing for English and Tamil input.
//!
//! Accepts `Gen 1:3`, `John 3:16-18`, `Jn 3`, `1 Cor 13`, `1co13.4-7`,
//! `யோவான் 3:16`, `யோவா 3`, `1 கொரி 13`, `சங் ௨௩`, slugs such as
//! `1-corinthians 13`, and USFM codes such as `JHN 3`. Separators between
//! chapter and verse may be `:`, `.`, `,` or a space; ranges use `-` or `–`.
//! Tamil digits are accepted. Matching is case-insensitive and ignores dots
//! and spaces inside the book name, so `1 Cor.` and `1cor` are the same.
//!
//! The book table is generated at compile time from `data/books.toml`.
//!
//! Input is expected in Unicode NFC. The table is built in NFC and callers
//! (the JS wrapper, the pipeline) normalise before calling, which keeps the
//! normalisation tables out of the wasm binary.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Book {
    pub code: &'static str,
    pub order: u32,
    pub testament: &'static str,
    pub chapters: u32,
    pub slug: &'static str,
    pub name_en: &'static str,
    pub name_ta: &'static str,
    /// Full names in every language and spelling (English, IRVTAM, TCV).
    pub names: &'static [&'static str],
    pub abbr_en: &'static [&'static str],
    pub abbr_ta: &'static [&'static str],
}

include!(concat!(env!("OUT_DIR"), "/books.rs"));

/// A parsed reference. `verse_end` is set only for a range.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Reference {
    pub book: &'static Book,
    pub chapter: u32,
    pub verse: Option<u32>,
    pub verse_end: Option<u32>,
}

impl Reference {
    /// `JHN.3.16`, `JHN.3.16-18` or `JHN.3`.
    pub fn id(&self) -> String {
        match (self.verse, self.verse_end) {
            (Some(v), Some(e)) => format!("{}.{}.{}-{}", self.book.code, self.chapter, v, e),
            (Some(v), None) => format!("{}.{}.{}", self.book.code, self.chapter, v),
            _ => format!("{}.{}", self.book.code, self.chapter),
        }
    }

    /// Canonical site path, e.g. `/irvtam/john/3/16-18`.
    pub fn path(&self, version_path: &str) -> String {
        let mut p = format!(
            "/{}/{}/{}",
            version_path.to_lowercase(),
            self.book.slug,
            self.chapter
        );
        match (self.verse, self.verse_end) {
            (Some(v), Some(e)) => p.push_str(&format!("/{v}-{e}")),
            (Some(v), None) => p.push_str(&format!("/{v}")),
            _ => {}
        }
        p
    }

    /// Human form in the given language: `John 3:16-18` or `யோவான் 3:16-18`.
    pub fn display(&self, lang: &str) -> String {
        let name = if lang == "ta" {
            self.book.name_ta
        } else {
            self.book.name_en
        };
        let mut s = format!("{name} {}", self.chapter);
        match (self.verse, self.verse_end) {
            (Some(v), Some(e)) => s.push_str(&format!(":{v}-{e}")),
            (Some(v), None) => s.push_str(&format!(":{v}")),
            _ => {}
        }
        s
    }
}

fn tamil_digit(c: char) -> Option<char> {
    match c {
        '\u{0BE6}'..='\u{0BEF}' => char::from_u32('0' as u32 + (c as u32 - 0x0BE6)),
        _ => None,
    }
}

/// Normalise for lookup: NFC, lowercase, drop spaces, dots and hyphens, ASCII digits.
fn key(s: &str) -> String {
    s.chars()
        .flat_map(|c| c.to_lowercase())
        .filter(|c| !c.is_whitespace() && *c != '.' && *c != '-')
        .map(|c| tamil_digit(c).unwrap_or(c))
        .collect()
}

fn lookup_exact(k: &str) -> Option<&'static Book> {
    VARIANTS
        .binary_search_by(|(v, _)| (*v).cmp(k))
        .ok()
        .map(|i| &BOOKS[VARIANTS[i].1 as usize])
}

/// A book name typed partially (`Gene`, `கொரிந்`) resolves if exactly one
/// full name or alias starts with it and the prefix is at least three chars.
fn lookup_prefix(k: &str) -> Option<&'static Book> {
    if k.chars().count() < 3 {
        return None;
    }
    let mut found: Option<&'static Book> = None;
    for b in BOOKS.iter() {
        let hit = b.names.iter().any(|n| key(n).starts_with(k));
        if hit {
            match found {
                Some(f) if f.code != b.code => return None,
                _ => found = Some(b),
            }
        }
    }
    found
}

pub fn find_book(name: &str) -> Option<&'static Book> {
    let k = key(name);
    if k.is_empty() {
        return None;
    }
    lookup_exact(&k).or_else(|| lookup_prefix(&k))
}

fn roman_ordinal(s: &str) -> Option<(u32, usize)> {
    for (pat, n) in [("iii", 3), ("ii", 2), ("i", 1)] {
        if s.starts_with(pat) {
            return Some((n, pat.len()));
        }
    }
    None
}

/// Split input into (book part, number part) and parse.
pub fn parse(input: &str) -> Option<Reference> {
    let s: String = input
        .chars()
        .map(|c| tamil_digit(c).unwrap_or(c))
        .map(|c| if c == '–' || c == '—' { '-' } else { c })
        .collect();
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    let lower = s.to_lowercase();
    let chars: Vec<char> = lower.chars().collect();

    // Optional ordinal: a leading 1-3 (or i/ii/iii) followed, after optional
    // space or dot, by a letter.
    let mut pos = 0;
    let mut ordinal = String::new();
    if let Some(&c) = chars.first() {
        let mut p = 0;
        let mut ord: Option<u32> = None;
        if ('1'..='3').contains(&c) {
            ord = c.to_digit(10);
            p = 1;
        } else if c == 'i' {
            // Roman ordinals need a separator after them ("I Cor", "II.Sam"),
            // otherwise "Isa" would read as "I" + "sa".
            let head: String = chars.iter().take(3).collect();
            if let Some((n, len)) = roman_ordinal(&head) {
                if chars.get(len).is_some_and(|c| matches!(c, ' ' | '.' | '-')) {
                    ord = Some(n);
                    p = len;
                }
            }
        }
        if let Some(n) = ord {
            while p < chars.len() && matches!(chars[p], ' ' | '.' | '-') {
                p += 1;
            }
            if p < chars.len() && chars[p].is_alphabetic() {
                ordinal = n.to_string();
                pos = p;
            }
        }
    }

    // Book part: up to the first digit.
    let start = pos;
    while pos < chars.len() && !chars[pos].is_ascii_digit() {
        pos += 1;
    }
    let book_part: String = chars[start..pos].iter().collect();
    let book_key = format!("{ordinal}{}", key(&book_part));
    let book = lookup_exact(&book_key).or_else(|| lookup_prefix(&book_key))?;

    // Number part: digit groups separated by : . , space or -.
    let rest: String = chars[pos..].iter().collect();
    let mut groups: Vec<u32> = Vec::new();
    let mut has_range = false;
    let mut cur = String::new();
    for c in rest.chars() {
        if c.is_ascii_digit() {
            cur.push(c);
        } else {
            if !cur.is_empty() {
                groups.push(cur.parse().ok()?);
                cur.clear();
            }
            match c {
                ':' | '.' | ',' | ' ' => {}
                '-' => has_range = true,
                _ => return None,
            }
        }
    }
    if !cur.is_empty() {
        groups.push(cur.parse().ok()?);
    }
    if groups.len() > 3 {
        return None;
    }

    let single_chapter = book.chapters == 1;
    let (chapter, verse, verse_end) = match groups.as_slice() {
        [] => (1, None, None),
        [a] if single_chapter => (1, Some(*a), None),
        [a] => (*a, None, None),
        [a, b] if single_chapter && has_range => (1, Some(*a), Some(*b)),
        [a, b] => (*a, Some(*b), None),
        [a, b, c] if has_range => (*a, Some(*b), Some(*c)),
        _ => return None,
    };
    if chapter == 0 || chapter > book.chapters {
        return None;
    }
    if let Some(v) = verse {
        if v == 0 {
            return None;
        }
    }
    if let (Some(v), Some(e)) = (verse, verse_end) {
        if e < v {
            return None;
        }
    }
    Some(Reference {
        book,
        chapter,
        verse,
        verse_end,
    })
}

/// Books whose names or abbreviations start with the typed text, in canonical order.
pub fn suggest(prefix: &str, limit: usize) -> Vec<&'static Book> {
    let k = key(prefix);
    if k.is_empty() {
        return Vec::new();
    }
    BOOKS
        .iter()
        .filter(|b| {
            b.names
                .iter()
                .chain(b.abbr_en.iter())
                .chain(b.abbr_ta.iter())
                .any(|n| key(n).starts_with(&k))
                || key(b.slug).starts_with(&k)
        })
        .take(limit)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn check(input: &str, expected: &str) {
        let got = parse(input)
            .map(|r| r.id())
            .unwrap_or_else(|| "NONE".to_string());
        assert_eq!(got, expected, "input {input:?}");
    }

    #[test]
    fn english() {
        check("Gen 1:3", "GEN.1.3");
        check("John 3:16", "JHN.3.16");
        check("Jn 3", "JHN.3");
        check("jn3.16", "JHN.3.16");
        check("1 Cor 13", "1CO.13");
        check("1co13.4-7", "1CO.13.4-7");
        check("I Corinthians 13:4", "1CO.13.4");
        check("Ps 23", "PSA.23");
        check("Psalm 119:105", "PSA.119.105");
        check("Song of Songs 2:1", "SNG.2.1");
        check("1-corinthians 13", "1CO.13");
        check("JHN 3 16", "JHN.3.16");
        check("Jude 5", "JUD.1.5");
        check("Philemon 1:5", "PHM.1.5");
        check("Obadiah", "OBA.1");
        check("Genesis", "GEN.1");
        check("Gene 2", "GEN.2");
        check("Revelation 22:21", "REV.22.21");
    }

    #[test]
    fn tamil() {
        check("ஆதி 1:3", "GEN.1.3");
        check("யோவான் 3:16", "JHN.3.16");
        check("யோவா 3", "JHN.3");
        check("1 கொரி 13", "1CO.13");
        check("1 கொரி 13.4-7", "1CO.13.4-7");
        check("சங் ௨௩", "PSA.23");
        check("சங்கீதம் 23:1", "PSA.23.1");
        check("1 சாமுயேல் 17", "1SA.17");
        check("1சாமு 17:45", "1SA.17.45");
        check("வெளிப்படுத்தின விசேஷம் 21", "REV.21");
        check("வெளி. 21:4", "REV.21.4");
        check("3 யோவா 5", "3JN.1.5");
    }

    #[test]
    fn rejects() {
        check("", "NONE");
        check("hello world", "NONE");
        check("John 99", "NONE");
        check("John 3:0", "NONE");
        check("John 3:18-16", "NONE");
        check("Jn 3:16:17", "NONE");
        check("அன்பு", "NONE");
        check("J 3", "NONE");
    }

    #[test]
    fn paths_and_display() {
        let r = parse("Jn 3:16-18").unwrap();
        assert_eq!(r.path("IRVTAM"), "/irvtam/john/3/16-18");
        assert_eq!(r.display("en"), "John 3:16-18");
        assert_eq!(r.display("ta"), "யோவான் 3:16-18");
        assert_eq!(parse("Ps 23").unwrap().path("bsb"), "/bsb/psalms/23");
    }

    #[test]
    fn fixture_file() {
        let text = std::fs::read_to_string(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../data/fixtures/references.tsv"
        ))
        .unwrap();
        let mut n = 0;
        for line in text.lines() {
            if line.trim().is_empty() || line.starts_with('#') {
                continue;
            }
            let (input, expected) = line.split_once('\t').expect("tab-separated");
            check(input.trim(), expected.trim());
            n += 1;
        }
        assert!(n >= 50, "fixture has only {n} cases");
    }

    #[test]
    fn suggestions() {
        let s = suggest("யோ", 10);
        let codes: Vec<&str> = s.iter().map(|b| b.code).collect();
        assert!(codes.contains(&"JHN") && codes.contains(&"JOB") && codes.contains(&"JON"));
        assert_eq!(suggest("Gen", 5)[0].code, "GEN");
    }
}
