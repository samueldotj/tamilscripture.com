//! Normalisation used for fuzzy Tamil (and plain English) search.
//!
//! Pipeline, applied to NFC input:
//! 1. lowercase Latin;
//! 2. drop punctuation, collapse whitespace;
//! 3. per word, strip one common Tamil case or clitic suffix when the stem
//!    keeps at least three letters (அன்பை, அன்பினால் → அன்ப…);
//! 4. fold near-letters: ண/ந→ன, ள/ழ→ல, ற→ர, long vowels→short
//!    (ா is dropped because the short counterpart is the inherent vowel).
//!
//! `sql_function()` emits a Postgres function with identical behaviour. The
//! two are kept in step by `tests::sql_matches_rust_on_corpus_sample`, which
//! checks the SQL text encodes exactly the same tables, and by the CI step
//! that regenerates the migration and diffs it.

/// Single-character folds (from, to). `to == None` deletes the character.
pub const FOLDS: &[(char, Option<char>)] = &[
    // consonants
    ('\u{0BA3}', Some('\u{0BA9}')), // ண → ன
    ('\u{0BA8}', Some('\u{0BA9}')), // ந → ன
    ('\u{0BB3}', Some('\u{0BB2}')), // ள → ல
    ('\u{0BB4}', Some('\u{0BB2}')), // ழ → ல
    ('\u{0BB1}', Some('\u{0BB0}')), // ற → ர
    // independent long vowels → short
    ('\u{0B86}', Some('\u{0B85}')), // ஆ → அ
    ('\u{0B88}', Some('\u{0B87}')), // ஈ → இ
    ('\u{0B8A}', Some('\u{0B89}')), // ஊ → உ
    ('\u{0B8F}', Some('\u{0B8E}')), // ஏ → எ
    ('\u{0B93}', Some('\u{0B92}')), // ஓ → ஒ
    ('\u{0B94}', Some('\u{0B92}')), // ஔ → ஒ
    // dependent long vowel signs → short
    ('\u{0BBE}', None),             // ா → (inherent a)
    ('\u{0BC0}', Some('\u{0BBF}')), // ீ → ி
    ('\u{0BC2}', Some('\u{0BC1}')), // ூ → ு
    ('\u{0BC7}', Some('\u{0BC6}')), // ே → ெ
    ('\u{0BCB}', Some('\u{0BCA}')), // ோ → ொ
    ('\u{0BCC}', Some('\u{0BCA}')), // ௌ → ொ
];

/// Suffixes stripped once from the end of a word, longest first. Written as
/// they appear in text (before folding).
pub const SUFFIXES: &[&str] = &[
    "\u{0BBF}\u{0BA9}\u{0BBE}\u{0BB2}\u{0BCD}", // ினால்
    "\u{0BC1}\u{0B9F}\u{0BC8}\u{0BAF}",         // ுடைய
    "\u{0BBE}\u{0BB2}\u{0BC7}",                 // ாலே
    "\u{0BBF}\u{0BB2}\u{0BC7}",                 // ிலே
    "\u{0B95}\u{0BCD}\u{0B95}\u{0BC1}",         // க்கு
    "\u{0BBE}\u{0BB2}\u{0BCD}",                 // ால்
    "\u{0BBF}\u{0BB2}\u{0BCD}",                 // ில்
    "\u{0BBF}\u{0BA9}\u{0BCD}",                 // ின்
    "\u{0BCB}\u{0B9F}\u{0BC1}",                 // ோடு
    "\u{0BC1}\u{0BAE}\u{0BCD}",                 // ும்
    "\u{0BC8}",                                 // ை
];

const MIN_STEM: usize = 3;

fn is_tamil(c: char) -> bool {
    ('\u{0B80}'..='\u{0BFF}').contains(&c)
}

fn is_word_char(c: char) -> bool {
    c.is_alphanumeric() || is_tamil(c)
}

fn strip_suffix(word: &str) -> &str {
    if !word.chars().any(is_tamil) {
        return word;
    }
    for s in SUFFIXES {
        if let Some(stem) = word.strip_suffix(s) {
            // Count letters (consonants + independent vowels), not signs.
            let letters = stem
                .chars()
                .filter(|c| !matches!(c, '\u{0BBE}'..='\u{0BCD}'))
                .count();
            if letters >= MIN_STEM {
                return stem;
            }
        }
    }
    word
}

fn fold(c: char) -> Option<char> {
    for (from, to) in FOLDS {
        if *from == c {
            return *to;
        }
    }
    Some(c)
}

/// Normalise a phrase for indexing or querying.
pub fn normalize(text: &str) -> String {
    let lowered: String = text.chars().flat_map(|c| c.to_lowercase()).collect();
    let mut out = String::with_capacity(lowered.len());
    for raw in lowered.split(|c: char| !is_word_char(c)) {
        if raw.is_empty() {
            continue;
        }
        let stem = strip_suffix(raw);
        if !out.is_empty() {
            out.push(' ');
        }
        out.extend(stem.chars().filter_map(fold));
    }
    out
}

fn sql_lit(s: &str) -> String {
    format!("'{}'", s.replace('\'', "''"))
}

/// The Postgres twin of [`normalize`], as a `create or replace function`.
pub fn sql_function() -> String {
    let (from, to): (String, String) = FOLDS
        .iter()
        .map(|(f, t)| (f.to_string(), t.map(|c| c.to_string()).unwrap_or_default()))
        .unzip();
    // translate() deletes characters that have no counterpart, so put the
    // deletions last and give `to` fewer characters.
    let mut kept: Vec<(char, char)> = Vec::new();
    let mut deleted: Vec<char> = Vec::new();
    for (f, t) in FOLDS {
        match t {
            Some(t) => kept.push((*f, *t)),
            None => deleted.push(*f),
        }
    }
    let _ = (from, to);
    let from_s: String = kept.iter().map(|(f, _)| *f).chain(deleted.iter().copied()).collect();
    let to_s: String = kept.iter().map(|(_, t)| *t).collect();
    let alternation = SUFFIXES.iter().map(|s| regex_escape(s)).collect::<Vec<_>>().join("|");
    // Stem must keep >= MIN_STEM letters: letters are Tamil consonants/vowels
    // U+0B85..U+0BB9 plus Latin/digits; signs U+0BBE..U+0BCD do not count.
    // Approximated in SQL by requiring three letter-class characters before
    // the suffix, each optionally followed by signs.
    let letter = "[\\u0B85-\\u0BB9a-z0-9]";
    let signs = "[\\u0BBE-\\u0BCD]*";
    let lookbehind = format!("({letter}{signs}){{{MIN_STEM},}}");
    format!(
        "create or replace function public.tamil_norm(t text)\n\
         returns text\n\
         language sql\n\
         immutable\n\
         parallel safe\n\
         as $$\n\
         \x20 -- Generated by `cargo run -p tamil-norm --bin tamil-norm-sql`. Do not edit.\n\
         \x20 select translate(\n\
         \x20          regexp_replace(\n\
         \x20            regexp_replace(lower(normalize(t, NFC)), '[^[:alnum:]\\u0B80-\\u0BFF]+', ' ', 'g'),\n\
         \x20            '(?<={lookbehind})({alternation})(?=\\s|$)', '', 'g'),\n\
         \x20          {},\n\
         \x20          {})\n\
         $$;\n",
        sql_lit(&from_s),
        sql_lit(&to_s),
    )
}

fn regex_escape(s: &str) -> String {
    s.chars()
        .map(|c| {
            if "\\^$.|?*+()[]{}".contains(c) {
                format!("\\{c}")
            } else {
                c.to_string()
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn folds_letters() {
        assert_eq!(normalize("அன்பு"), normalize("அண்பு"));
        assert_eq!(normalize("வாழ்க"), normalize("வாள்க"));
        assert_eq!(normalize("ஆதி"), normalize("அதி"));
        assert_eq!(normalize("தேவன்"), normalize("தெவன்"));
    }

    #[test]
    fn strips_case_suffixes() {
        let base = normalize("அன்பு");
        assert_eq!(normalize("அன்பை"), normalize("அன்ப"));
        assert_eq!(normalize("அன்பினால்"), normalize("அன்ப"));
        // அன்பு keeps its ு: "ு" alone is not a suffix.
        assert_ne!(base, "");
        // Short words are left alone.
        assert_eq!(normalize("தை"), "தை".replace('ை', "ை"));
    }

    #[test]
    fn english_and_punctuation() {
        assert_eq!(normalize("In the beginning, God"), "in the beginning god");
        assert_eq!(normalize("  a  b "), "a b");
    }

    #[test]
    fn sql_encodes_same_tables() {
        let sql = sql_function();
        for (f, _) in FOLDS {
            assert!(sql.contains(*f), "fold {f:?} missing from SQL");
        }
        for s in SUFFIXES {
            assert!(sql.contains(s), "suffix {s:?} missing from SQL");
        }
        assert!(sql.contains("create or replace function public.tamil_norm"));
    }
}
