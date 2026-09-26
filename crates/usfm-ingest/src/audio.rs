//! Audio recordings: the committed output of `tools/audio` (docs/feature_audio_tool.md).
//!
//! ```text
//! {audio}/audio.toml                         base = "https://stream.tamilaudiobible.com"
//! {audio}/{VERSION}/{recording}/recording.toml
//! {audio}/{VERSION}/{recording}/chapters.tsv  book  chapter  ms  bytes  sha256
//! ```
//!
//! A version opts in with `[audio] recording = "r1"` in its `version.toml`; the
//! MP3s themselves live in R2 and are never read here.

use anyhow::{bail, Context, Result};
use serde::Deserialize;
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Deserialize)]
struct AudioToml {
    base: String,
}

/// `recording.toml`, the fields the site shows; the tool's own settings are ignored.
#[derive(Debug, Deserialize)]
struct RecordingToml {
    version: String,
    recording: String,
    #[serde(default)]
    narrator: String,
    #[serde(default)]
    publisher: String,
    licence: String,
    attribution: String,
    #[serde(default)]
    source_url: String,
    #[serde(default)]
    drama: bool,
}

/// One recording, loaded and checked, ready to annotate chapters.
#[derive(Debug)]
pub struct Recording {
    pub meta: crate::model::VersionAudio,
    base: String,
    /// (book code, chapter) -> duration in ms.
    chapters: BTreeMap<(String, u32), u64>,
    /// Every file read, for the build id.
    pub files: Vec<PathBuf>,
}

impl Recording {
    /// Load `{dir}/{code}/{recording}`. Row-level problems are returned as
    /// messages so the caller can report them with everything else.
    pub fn load(dir: &Path, code: &str, recording: &str) -> Result<(Self, Vec<String>)> {
        if !is_id(recording) {
            bail!("{code}: recording id {recording:?} must be lower-case letters, digits and -");
        }
        let audio_toml = dir.join("audio.toml");
        let base: AudioToml = toml::from_str(
            &fs::read_to_string(&audio_toml)
                .with_context(|| format!("reading {}", audio_toml.display()))?,
        )
        .with_context(|| format!("parsing {}", audio_toml.display()))?;
        let rec_dir = dir.join(code).join(recording);
        let rec_toml = rec_dir.join("recording.toml");
        let rec: RecordingToml =
            toml::from_str(&fs::read_to_string(&rec_toml).with_context(|| {
                format!("{code}: no recording {recording} ({})", rec_toml.display())
            })?)
            .with_context(|| format!("parsing {}", rec_toml.display()))?;
        let tsv = rec_dir.join("chapters.tsv");
        let text =
            fs::read_to_string(&tsv).with_context(|| format!("reading {}", tsv.display()))?;

        let mut problems = Vec::new();
        if rec.version != code || rec.recording != recording {
            problems.push(format!(
                "{}: says version {} recording {}, expected {code} {recording}",
                rec_toml.display(),
                rec.version,
                rec.recording
            ));
        }
        let (chapters, row_problems) = parse_chapters(&text);
        problems.extend(
            row_problems
                .into_iter()
                .map(|p| format!("{}:{p}", tsv.display())),
        );

        let mut files = vec![audio_toml, rec_toml, tsv];
        let timings = rec_dir.join("timings");
        if timings.is_dir() {
            let mut t: Vec<PathBuf> = fs::read_dir(&timings)?
                .filter_map(|e| e.ok().map(|e| e.path()))
                .collect();
            t.sort();
            files.extend(t);
        }
        Ok((
            Recording {
                meta: crate::model::VersionAudio {
                    recording: recording.to_string(),
                    narrator: rec.narrator,
                    publisher: rec.publisher,
                    licence: rec.licence,
                    attribution: rec.attribution,
                    source_url: rec.source_url,
                    drama: rec.drama,
                },
                base: base.base.trim_end_matches('/').to_string(),
                chapters,
                files,
            },
            problems,
        ))
    }

    /// Every (book, chapter) the recording has, for checking against the text.
    pub fn chapter_keys(&self) -> impl Iterator<Item = &(String, u32)> {
        self.chapters.keys()
    }

    /// The chapter's `audio` field, if the recording has it.
    pub fn chapter(
        &self,
        version: &str,
        book: &str,
        chapter: u32,
    ) -> Option<crate::model::ChapterAudio> {
        let ms = *self.chapters.get(&(book.to_string(), chapter))?;
        Some(crate::model::ChapterAudio {
            src: format!(
                "{}/{}",
                self.base,
                object_key(version, &self.meta.recording, book, chapter)
            ),
            ms,
            timed: false,
        })
    }
}

/// `IRVTAM/r1/JHN/JHN_003.mp3`: the R2 key, shared with `tools/audio`.
pub fn object_key(version: &str, recording: &str, book: &str, chapter: u32) -> String {
    format!("{version}/{recording}/{book}/{book}_{chapter:03}.mp3")
}

fn is_id(s: &str) -> bool {
    !s.is_empty()
        && s.bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
}

/// `chapters.tsv`: a header, then `book chapter ms bytes sha256` per row.
fn parse_chapters(text: &str) -> (BTreeMap<(String, u32), u64>, Vec<String>) {
    let mut out = BTreeMap::new();
    let mut problems = Vec::new();
    for (i, line) in text.lines().enumerate() {
        let n = i + 1;
        if i == 0 {
            if line.split('\t').collect::<Vec<_>>() != ["book", "chapter", "ms", "bytes", "sha256"]
            {
                problems.push(format!(
                    "{n}: header must be book, chapter, ms, bytes, sha256"
                ));
            }
            continue;
        }
        if line.is_empty() {
            continue;
        }
        let f: Vec<&str> = line.split('\t').collect();
        let parsed = (|| {
            if f.len() != 5 {
                return None;
            }
            let book = f[0];
            if book.len() != 3
                || !book
                    .bytes()
                    .all(|b| b.is_ascii_uppercase() || b.is_ascii_digit())
            {
                return None;
            }
            let chapter: u32 = f[1].parse().ok().filter(|&c| c > 0)?;
            let ms: u64 = f[2].parse().ok().filter(|&m| m > 0)?;
            f[3].parse::<u64>().ok().filter(|&b| b > 0)?;
            if f[4].len() != 64 || !f[4].bytes().all(|b| b.is_ascii_hexdigit()) {
                return None;
            }
            Some((book.to_string(), chapter, ms))
        })();
        match parsed {
            Some((book, chapter, ms)) => match out.entry((book.clone(), chapter)) {
                std::collections::btree_map::Entry::Occupied(_) => {
                    problems.push(format!("{n}: {book} {chapter} listed twice"))
                }
                std::collections::btree_map::Entry::Vacant(e) => {
                    e.insert(ms);
                }
            },
            None => problems.push(format!("{n}: malformed row {line:?}")),
        }
    }
    (out, problems)
}

#[cfg(test)]
mod tests {
    use super::*;

    const SHA: &str = "9f2c000000000000000000000000000000000000000000000000000000000abc";

    #[test]
    fn keys_pad_the_chapter() {
        assert_eq!(
            object_key("IRVTAM", "r1", "JHN", 3),
            "IRVTAM/r1/JHN/JHN_003.mp3"
        );
        assert_eq!(
            object_key("KJV", "r1", "PSA", 119),
            "KJV/r1/PSA/PSA_119.mp3"
        );
    }

    #[test]
    fn parses_rows_and_reports_bad_ones() {
        let tsv = format!(
            "book\tchapter\tms\tbytes\tsha256\nJHN\t3\t312480\t2499840\t{SHA}\nJHN\t3\t1\t1\t{SHA}\njhn\t4\t1\t1\t{SHA}\nJHN\t5\t0\t1\t{SHA}\n\n1JN\t1\t9000\t72000\t{SHA}\n"
        );
        let (rows, problems) = parse_chapters(&tsv);
        assert_eq!(rows.get(&("JHN".into(), 3)), Some(&312480));
        assert_eq!(rows.get(&("1JN".into(), 1)), Some(&9000));
        assert_eq!(rows.len(), 2);
        assert_eq!(problems.len(), 3, "{problems:?}");
        assert!(problems[0].starts_with("3: JHN 3 listed twice"));
    }

    #[test]
    fn rejects_a_wrong_header() {
        let (_, problems) = parse_chapters("book\tch\tms\n");
        assert_eq!(problems.len(), 1);
    }

    #[test]
    fn recording_ids() {
        assert!(is_id("r1"));
        assert!(is_id("r2-remaster"));
        assert!(!is_id("R1"));
        assert!(!is_id("../x"));
        assert!(!is_id(""));
    }
}
