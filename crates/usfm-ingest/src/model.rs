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
    /// The chapter's recording, when the version has one (docs/feature_audio.md).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub audio: Option<ChapterAudio>,
}

/// `audio` in a chapter file: where the MP3 is and how long it runs.
#[derive(Debug, Serialize, Clone, PartialEq)]
pub struct ChapterAudio {
    pub src: String,
    pub ms: u64,
    /// Verse start times exist in `{chapter}.audio.json` beside the chapter
    /// (stage 2, docs/feature_audio_tool.md T7); false until then.
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    pub timed: bool,
}

/// `content/{build}/{VERSION}/{BOOK}/{chapter}.audio.json`: each verse's start
/// in the recording, `[verse, ms]` in order, fetched only when playback starts.
#[derive(Debug, Serialize)]
pub struct AudioTimingsJson<'a> {
    pub verses: &'a [(u32, u64)],
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

/// A version: `version.toml` as written, plus what the pipeline fills in.
/// Adding a version takes only its directory (USFM files and this file), R-3.6.
#[derive(Debug, Serialize, Clone, serde::Deserialize)]
pub struct VersionMeta {
    pub code: String,
    /// BCP 47 language code of the text (`ta`, `en`, `ml`, ...).
    pub lang: String,
    /// The language's name in English and in itself ("Tamil", "தமிழ்").
    #[serde(default)]
    pub language: String,
    #[serde(default)]
    pub language_native: String,
    /// The language's name in Tamil, for the Tamil interface ("ஆங்கிலம்").
    #[serde(default)]
    pub language_ta: String,
    pub name: String,
    pub name_native: String,
    pub short: String,
    pub licence: String,
    pub attribution: String,
    pub source_url: String,
    #[serde(default)]
    pub ebible_id: String,
    /// Place in pickers and in the manifest, lowest first.
    #[serde(default = "default_order")]
    pub order: u32,
    /// The version a reader of this language gets unless they choose; the
    /// first default (by order) is the site's default version.
    #[serde(default)]
    pub default: bool,
    /// Book codes present in this version's content; filled in by the pipeline.
    #[serde(default)]
    pub books: Vec<String>,
    /// Book names from the USFM `\h` headers, for languages that books.toml
    /// does not name (it carries Tamil and English); filled in by the pipeline.
    #[serde(default, skip_serializing_if = "std::collections::BTreeMap::is_empty")]
    pub book_names: std::collections::BTreeMap<String, String>,
    /// `[audio] recording = "r1"` names the live recording; the pipeline fills
    /// in the rest from that recording's `recording.toml`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub audio: Option<VersionAudio>,
}

/// A version's live recording, for the player's credits and `/about`.
#[derive(Debug, Serialize, Clone, Default, serde::Deserialize)]
pub struct VersionAudio {
    pub recording: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub narrator: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub publisher: String,
    #[serde(default)]
    pub licence: String,
    #[serde(default)]
    pub attribution: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub source_url: String,
    /// Several voices with music under them, rather than one narrator.
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub drama: bool,
}

fn default_order() -> u32 {
    100
}

/// `content/manifest.json`
#[derive(Debug, Serialize)]
pub struct Manifest {
    pub build: String,
    /// The site's default version: the first `default = true` version by order.
    pub default_version: String,
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
