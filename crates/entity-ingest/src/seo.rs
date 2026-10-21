//! Which entity pages search engines are asked to index (docs/design.md ADR-17).
//!
//! A dictionary article about one person or place is shown in full on that
//! page, which is its canonical home; the article page points there. An
//! article about several (Easton's "Beriah" is four men) stays the canonical
//! page, and each person's page carries an excerpt of it. A page is indexed
//! when its Tamil text, as the server renders it, reaches `MIN_TA_WORDS`.
//! The web pages render by the same rules: keep the two in step.

use crate::articles::Article;

/// Tamil words a page needs before it is put forward for indexing.
pub const MIN_TA_WORDS: usize = 40;

/// Whitespace-separated words an excerpt of a shared article keeps
/// (`excerpt` in apps/web/src/lib/entities/seo.ts).
pub const EXCERPT_WORDS: usize = 30;

/// Pages whose dictionary text is chosen by hand (`CHOSEN_ENTRIES` in
/// apps/web/src/lib/entities/load.ts): they own no article and are indexed.
pub const CHOSEN: [&str; 1] = ["person/jesus"];

/// Runs of Tamil script: a word, for counting, the way a reader would see it.
pub fn ta_words(s: &str) -> usize {
    let mut n = 0;
    let mut inside = false;
    for c in s.chars() {
        let tamil = ('\u{0B80}'..='\u{0BFF}').contains(&c);
        if tamil && !inside {
            n += 1;
        }
        inside = tamil;
    }
    n
}

/// Tamil words of the whole article: its title and every paragraph.
pub fn article_words(a: &Article) -> usize {
    a.title_ta.as_deref().map(ta_words).unwrap_or(0)
        + a.paragraphs
            .iter()
            .filter_map(|p| p.ta.as_deref())
            .map(ta_words)
            .sum::<usize>()
}

/// The opening of an article as a page that does not own it shows it: the first
/// `EXCERPT_WORDS` words of its paragraphs (Easton's often opens on a two-word
/// meaning), Tamil where there is Tamil.
pub fn excerpt(a: &Article) -> String {
    a.paragraphs
        .iter()
        .filter(|p| !p.heading)
        .flat_map(|p| p.ta.as_deref().unwrap_or(&p.text).split_whitespace())
        .take(EXCERPT_WORDS)
        .collect::<Vec<_>>()
        .join(" ")
}

/// The page an article belongs to: the one person or place it is the name entry of.
pub fn owner(a: &Article, name_of: impl Fn(&str) -> Option<String>) -> Option<String> {
    let [only] = a.entities.as_slice() else {
        return None;
    };
    if CHOSEN.contains(&only.as_str()) {
        return None;
    }
    let name = name_of(only)?;
    (name.to_lowercase() == a.title.to_lowercase()).then(|| only.clone())
}

/// Tamil words of a person or place page. `entries` are its name entries (the
/// articles titled with its name); `own` is this page's key. Its own entries
/// count in full, the others as excerpts; `summary` (the one-line description
/// and short paragraph) is shown, and counts, only when it owns none.
pub fn entity_words(own: &str, entries: &[&Article], summary: &[Option<&str>]) -> usize {
    let mut owns = false;
    let mut n = 0;
    for a in entries {
        if a.canonical.as_deref() == Some(own) {
            owns = true;
            n += a.ta_words;
        } else {
            n += ta_words(&excerpt(a));
        }
    }
    if !owns {
        n += summary.iter().flatten().map(|s| ta_words(s)).sum::<usize>();
    }
    n
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::articles::Paragraph;

    fn article(title: &str, entities: &[&str], ta: &[&str]) -> Article {
        Article {
            source: "eastons".into(),
            id: format!("eastons/{}", title.to_lowercase()),
            slug: title.to_lowercase(),
            title: title.into(),
            title_ta: None,
            lang: "en",
            licence: "PD",
            attribution: "",
            entities: entities.iter().map(|s| s.to_string()).collect(),
            hints: vec![],
            paragraphs: ta
                .iter()
                .enumerate()
                .map(|(i, t)| Paragraph {
                    id: format!("p{i}"),
                    text: "English".into(),
                    heading: false,
                    ta: Some(t.to_string()),
                    ta_source: Some("draft"),
                })
                .collect(),
            refs: vec![],
            hash: String::new(),
            also_in: vec![],
            canonical: None,
            index: false,
            ta_words: 0,
        }
    }

    #[test]
    fn counts_tamil_runs_only() {
        assert_eq!(ta_words("அப்பத்தின் வீடு."), 2);
        assert_eq!(ta_words("பெத்லெகேம்-யூதா (1 சாமுவேல் 17:12)"), 3);
        assert_eq!(ta_words("House of bread"), 0);
    }

    #[test]
    fn owner_is_the_one_entity_of_the_same_name() {
        let names = |k: &str| match k {
            "person/rehabiah" => Some("Rehabiah".to_string()),
            "person/jesus" => Some("Jesus".to_string()),
            _ => Some("Other".to_string()),
        };
        let one = article("Rehabiah", &["person/rehabiah"], &[]);
        assert_eq!(owner(&one, names).as_deref(), Some("person/rehabiah"));
        let shared = article("Rehabiah", &["person/rehabiah", "person/x"], &[]);
        assert_eq!(owner(&shared, names), None);
        let other_title = article("Levites", &["person/rehabiah"], &[]);
        assert_eq!(owner(&other_title, names), None);
        let chosen = article("Jesus", &["person/jesus"], &[]);
        assert_eq!(owner(&chosen, names), None);
    }

    #[test]
    fn entity_counts_own_entries_in_full_and_shared_as_excerpts() {
        let long = ["சொல் ".repeat(50)];
        let mut own = article(
            "Beriah",
            &["person/a"],
            &long.iter().map(String::as_str).collect::<Vec<_>>(),
        );
        own.canonical = Some("person/a".into());
        own.ta_words = article_words(&own);
        let shared = article(
            "Beriah",
            &["person/a", "person/b"],
            &long.iter().map(String::as_str).collect::<Vec<_>>(),
        );
        let brief = "லேவியன் ஒருவன்";
        assert_eq!(entity_words("person/a", &[&own], &[Some(brief)]), 50);
        assert_eq!(
            entity_words("person/b", &[&shared], &[Some(brief), None]),
            EXCERPT_WORDS + 2
        );
        assert_eq!(entity_words("person/c", &[], &[Some(brief)]), 2);
    }
}
