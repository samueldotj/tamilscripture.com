//! Output JSON shapes. These are the contract with the web app; change them
//! together with `apps/web/src/lib/content/types.ts`.

use serde::Serialize;

/// One chapter file: `content/{build}/{VERSION}/{BOOK}/{chapter}.json`.
#[derive(Debug, Serialize)]
pub struct ChapterJson {
    pub version: String,
    pub book: String,
    pub chapter: u32,
    pub build: String,
    /// Chapter label from `\cl`, if the translation supplies one.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub label: Option<String>,
    pub blocks: Vec<Block>,
    /// Maps every verse id inside a bridge to the segment id that carries it,
    /// e.g. `"JHN.3.18": "JHN.3.17"`.
    #[serde(skip_serializing_if = "std::collections::BTreeMap::is_empty")]
    pub bridges: std::collections::BTreeMap<String, String>,
    pub prev: Option<ChapterRef>,
    pub next: Option<ChapterRef>,
}

#[derive(Debug, Serialize, Clone)]
pub struct ChapterRef {
    pub book: String,
    pub chapter: u32,
}

#[derive(Debug, Serialize, Clone)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum Block {
    /// Section heading, major section, parallel reference, speaker, acrostic.
    Heading {
        kind: String,
        level: u8,
        text: String,
    },
    /// A paragraph, poetry line, list item or descriptive title carrying verse text.
    Para {
        style: String,
        segments: Vec<Segment>,
    },
    /// Blank line (`\b`).
    Break,
}

/// A run of text belonging to one verse inside one block. A verse that spans
/// several blocks appears as several segments with the same `id`; only the
/// first has `n` set, so verse numbers print once.
#[derive(Debug, Serialize, Clone, Default)]
pub struct Segment {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub n: Option<String>,
    pub text: String,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub notes: Vec<Note>,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub spans: Vec<Span>,
}

/// Footnote (`\f`) or translator cross-reference (`\x`) anchored at a char offset.
#[derive(Debug, Serialize, Clone)]
pub struct Note {
    pub kind: String,
    pub at: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub caller: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reference: Option<String>,
    pub text: String,
}

/// Inline styling worth keeping: currently only words of Jesus (`\wj`).
#[derive(Debug, Serialize, Clone)]
pub struct Span {
    pub kind: String,
    pub start: usize,
    pub end: usize,
}

/// `content/{build}/{VERSION}/{BOOK}/intro.json`
#[derive(Debug, Serialize)]
pub struct IntroJson {
    pub version: String,
    pub book: String,
    pub title: String,
    pub blocks: Vec<IntroBlock>,
}

#[derive(Debug, Serialize, Clone)]
pub struct IntroBlock {
    pub style: String,
    pub text: String,
}

/// `content/{build}/versions.json` entry.
#[derive(Debug, Serialize, Clone, serde::Deserialize)]
pub struct VersionMeta {
    pub code: String,
    pub lang: String,
    pub name: String,
    pub name_native: String,
    pub short: String,
    pub licence: String,
    pub attribution: String,
    pub source_url: String,
    #[serde(default)]
    pub ebible_id: String,
    /// Book codes present in this version's content; filled in by the pipeline.
    #[serde(default)]
    pub books: Vec<String>,
}

/// `content/manifest.json`
#[derive(Debug, Serialize)]
pub struct Manifest {
    pub build: String,
    pub versions: Vec<VersionMeta>,
    pub books: Vec<crate::books::Book>,
}

/// `content/{build}/xref/{BOOK}/{chapter}.json`: verse id -> targets sorted by votes.
pub type XrefChapter = std::collections::BTreeMap<String, Vec<XrefTarget>>;

#[derive(Debug, Serialize, Clone)]
pub struct XrefTarget {
    pub to: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub end: Option<String>,
    pub votes: i32,
}
