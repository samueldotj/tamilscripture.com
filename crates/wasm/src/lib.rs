//! JavaScript-facing API. Results are JSON strings to keep the binding surface
//! tiny; `packages/bible-wasm/index.ts` parses them into typed objects.

use serde::Serialize;
use wasm_bindgen::prelude::*;

#[derive(Serialize)]
struct RefOut<'a> {
    code: &'a str,
    slug: &'a str,
    chapter: u32,
    verse: Option<u32>,
    verse_end: Option<u32>,
    id: String,
    display_en: String,
    display_ta: String,
}

#[derive(Serialize)]
struct BookOut<'a> {
    code: &'a str,
    slug: &'a str,
    order: u32,
    testament: &'a str,
    chapters: u32,
    name_en: &'a str,
    name_ta: &'a str,
}

/// Parse a reference in English or Tamil. Returns a JSON object or `null`.
#[wasm_bindgen]
pub fn parse_reference(input: &str) -> Option<String> {
    let r = bible_ref::parse(input)?;
    let out = RefOut {
        code: r.book.code,
        slug: r.book.slug,
        chapter: r.chapter,
        verse: r.verse,
        verse_end: r.verse_end,
        id: r.id(),
        display_en: r.display("en"),
        display_ta: r.display("ta"),
    };
    serde_json::to_string(&out).ok()
}

/// Canonical site path for a reference under a version path such as `irvtam`
/// or `irvtam+bsb`. Returns `null` if the input is not a reference.
#[wasm_bindgen]
pub fn reference_path(input: &str, version_path: &str) -> Option<String> {
    bible_ref::parse(input).map(|r| r.path(version_path))
}

/// Books whose names or abbreviations start with the typed text, as a JSON array.
#[wasm_bindgen]
pub fn suggest_books(prefix: &str, limit: usize) -> String {
    let books: Vec<BookOut> = bible_ref::suggest(prefix, limit)
        .into_iter()
        .map(|b| BookOut {
            code: b.code,
            slug: b.slug,
            order: b.order,
            testament: b.testament,
            chapters: b.chapters,
            name_en: b.name_en,
            name_ta: b.name_ta,
        })
        .collect();
    serde_json::to_string(&books).unwrap_or_else(|_| "[]".into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn json_roundtrip() {
        let s = parse_reference("Jn 3:16-18").unwrap();
        assert!(s.contains("\"code\":\"JHN\""));
        assert!(s.contains("\"verse_end\":18"));
        assert_eq!(
            reference_path("சங் 23", "IRVTAM").unwrap(),
            "/irvtam/psalms/23"
        );
        assert!(reference_path("hello", "irvtam").is_none());
        assert!(suggest_books("யோ", 5).contains("JHN"));
    }
}
