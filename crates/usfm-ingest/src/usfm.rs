//! A marker-level USFM 3 parser sized for the eBible.org dialect.
//!
//! Paragraph-level markers open blocks, `\c` and `\v` set position, inline
//! character markers are stripped to their text (except `\wj`, kept as a
//! span), footnotes and cross-references become notes anchored at a char
//! offset. Unknown markers are recorded in `ParsedBook::unknown` so the
//! validation step can report them instead of dropping text silently.

use crate::model::{Block, IntroBlock, Note, Segment, Span};
use std::collections::{BTreeMap, BTreeSet};
use unicode_normalization::UnicodeNormalization;

#[derive(Debug, Default)]
pub struct ParsedBook {
    pub code: String,
    pub header: String,
    pub title: String,
    pub intro: Vec<IntroBlock>,
    pub chapters: Vec<ParsedChapter>,
    pub unknown: BTreeSet<String>,
}

#[derive(Debug, Default)]
pub struct ParsedChapter {
    pub number: u32,
    pub label: Option<String>,
    pub blocks: Vec<Block>,
    pub bridges: BTreeMap<String, String>,
}

#[derive(Debug, Clone, PartialEq)]
enum Tok {
    Marker { name: String, closing: bool },
    Text(String),
}

fn tokenize(src: &str) -> Vec<Tok> {
    let mut out = Vec::new();
    let mut text = String::new();
    let mut chars = src.chars().peekable();
    while let Some(c) = chars.next() {
        if c != '\\' {
            text.push(if c == '\n' || c == '\r' || c == '\t' {
                ' '
            } else {
                c
            });
            continue;
        }
        let mut name = String::new();
        if chars.peek() == Some(&'+') {
            name.push('+');
            chars.next();
        }
        while let Some(&d) = chars.peek() {
            if d.is_ascii_alphanumeric() {
                name.push(d);
                chars.next();
            } else {
                break;
            }
        }
        let closing = chars.peek() == Some(&'*');
        if closing {
            chars.next();
        }
        if name.is_empty() {
            text.push('\\');
            continue;
        }
        if !text.is_empty() {
            out.push(Tok::Text(std::mem::take(&mut text)));
        }
        // One space after an opening marker is part of the syntax, not content.
        if !closing && chars.peek() == Some(&' ') {
            chars.next();
        }
        out.push(Tok::Marker { name, closing });
    }
    if !text.is_empty() {
        out.push(Tok::Text(text));
    }
    out
}

fn split_number(s: &str) -> (String, String) {
    let s = s.trim_start();
    match s.find(' ') {
        Some(i) => (s[..i].to_string(), s[i + 1..].to_string()),
        None => (s.to_string(), String::new()),
    }
}

/// Markers that open a new paragraph-level block carrying verse text.
fn para_style(name: &str) -> Option<&'static str> {
    Some(match name {
        "p" => "p",
        "m" => "m",
        "nb" => "nb",
        "pi" | "pi1" => "pi1",
        "pi2" => "pi2",
        "pi3" => "pi3",
        "pm" => "pm",
        "pmo" => "pmo",
        "pmc" => "pmc",
        "pr" => "pr",
        "pc" => "pc",
        "mi" => "mi",
        "cls" => "cls",
        "q" | "q1" => "q1",
        "q2" => "q2",
        "q3" => "q3",
        "q4" => "q4",
        "qr" => "qr",
        "qc" => "qc",
        "qm" | "qm1" => "qm1",
        "qm2" => "qm2",
        "qm3" => "qm3",
        "li" | "li1" => "li1",
        "li2" => "li2",
        "li3" => "li3",
        "li4" => "li4",
        "d" => "d",
        "ph" | "ph1" => "ph1",
        "lit" => "lit",
        "tr" => "tr",
        _ => return None,
    })
}

/// Heading-like markers: (kind, level).
fn heading_kind(name: &str) -> Option<(&'static str, u8)> {
    Some(match name {
        "s" | "s1" => ("s", 1),
        "s2" => ("s", 2),
        "s3" => ("s", 3),
        "ms" | "ms1" => ("ms", 1),
        "ms2" => ("ms", 2),
        "mr" => ("mr", 1),
        "r" => ("r", 1),
        "sr" => ("sr", 1),
        "sp" => ("sp", 1),
        "qa" => ("qa", 1),
        "sd" | "sd1" | "sd2" => ("sd", 1),
        _ => return None,
    })
}

fn intro_style(name: &str) -> Option<&'static str> {
    Some(match name {
        "is" | "is1" => "is1",
        "is2" => "is2",
        "ip" => "ip",
        "ipi" => "ipi",
        "im" => "im",
        "iot" => "iot",
        "io" | "io1" => "io1",
        "io2" => "io2",
        "io3" => "io3",
        "io4" => "io4",
        "ili" | "ili1" => "ili1",
        "ili2" => "ili2",
        "iq" | "iq1" => "iq1",
        "iq2" => "iq2",
        "imt" | "imt1" => "imt1",
        "imt2" => "imt2",
        "iex" => "iex",
        "ib" => "ib",
        _ => return None,
    })
}

/// Inline character markers whose text is kept and whose markup is dropped.
fn is_char_marker(name: &str) -> bool {
    matches!(
        name,
        "w" | "+w"
            | "wj"
            | "+wj"
            | "add"
            | "+add"
            | "nd"
            | "+nd"
            | "k"
            | "+k"
            | "tl"
            | "+tl"
            | "bk"
            | "+bk"
            | "qs"
            | "+qs"
            | "sc"
            | "+sc"
            | "it"
            | "+it"
            | "bd"
            | "+bd"
            | "bdit"
            | "+bdit"
            | "em"
            | "+em"
            | "no"
            | "+no"
            | "sls"
            | "+sls"
            | "pn"
            | "+pn"
            | "png"
            | "+png"
            | "ord"
            | "+ord"
            | "qt"
            | "+qt"
            | "sig"
            | "+sig"
            | "dc"
            | "+dc"
            | "ior"
            | "+ior"
            | "iqt"
            | "+iqt"
            | "wh"
            | "+wh"
            | "wg"
            | "+wg"
            | "wa"
            | "+wa"
            | "lik"
            | "+lik"
            | "liv"
            | "+liv"
            | "litl"
            | "+litl"
            | "va"
            | "+va"
            | "vp"
            | "+vp"
            | "ca"
            | "+ca"
            | "rq"
            | "+rq"
            | "ndx"
            | "+ndx"
            | "rb"
            | "+rb"
            | "pro"
            | "+pro"
            | "jmp"
            | "+jmp"
            | "xt"
            | "+xt"
            | "fv"
            | "+fv"
    )
}

/// Markers that carry attributes after a `|` in their text (USFM 3).
fn has_attributes(name: &str) -> bool {
    matches!(
        name.trim_start_matches('+'),
        "w" | "rb" | "jmp" | "fig" | "xt"
    )
}

/// Markers that are dropped together with their content.
fn is_dropped_with_content(name: &str) -> bool {
    matches!(
        name,
        "fig" | "va" | "+va" | "vp" | "+vp" | "ca" | "+ca" | "cp" | "ndx" | "+ndx" | "rq" | "+rq"
    )
}

/// Book-level metadata markers whose text is consumed but not rendered.
fn is_meta(name: &str) -> bool {
    matches!(
        name,
        "id" | "ide"
            | "usfm"
            | "rem"
            | "sts"
            | "h"
            | "h1"
            | "toc1"
            | "toc2"
            | "toc3"
            | "toca1"
            | "toca2"
            | "toca3"
            | "mt2"
            | "mt3"
            | "mt4"
            | "cp"
            | "ca"
            | "ie"
    )
}

struct Parser {
    book: ParsedBook,
    chapter: Option<ParsedChapter>,
    block: Option<(String, Vec<Segment>)>,
    seg: Option<Segment>,
    verse_id: Option<String>,
    /// Open inline markers, innermost last, with the segment text length at open.
    inline: Vec<(String, usize)>,
    note: Option<NoteState>,
    /// Text of a `\c` line waiting for its chapter number.
    pending: Pending,
    intro_open: Option<(String, String)>,
}

#[derive(Debug, PartialEq)]
enum Pending {
    None,
    Chapter,
    Verse,
    Label,
    Title,
    Meta,
    Heading(&'static str, u8, String),
    Dropped(String),
}

struct NoteState {
    /// Output kind: "f" or "x".
    kind: String,
    /// Marker name that closes this note: "f", "fe" or "x".
    close_name: String,
    caller: Option<String>,
    reference: Option<String>,
    text: String,
    at: usize,
    depth: usize,
    part: NotePart,
    pending_caller: bool,
}

#[derive(PartialEq)]
enum NotePart {
    Ref,
    Text,
    Skip,
}

impl Parser {
    fn new() -> Self {
        Parser {
            book: ParsedBook::default(),
            chapter: None,
            block: None,
            seg: None,
            verse_id: None,
            inline: Vec::new(),
            note: None,
            pending: Pending::None,
            intro_open: None,
        }
    }

    fn flush_seg(&mut self) {
        if let Some(mut seg) = self.seg.take() {
            trim_end_in_place(&mut seg.text);
            for sp in &mut seg.spans {
                sp.end = sp.end.min(seg.text.chars().count());
            }
            let empty = seg.text.is_empty() && seg.notes.is_empty();
            if !empty || seg.n.is_some() {
                if let Some((_, segs)) = &mut self.block {
                    segs.push(seg);
                }
            }
        }
    }

    fn flush_block(&mut self) {
        self.flush_seg();
        if let Some((style, segs)) = self.block.take() {
            if !segs.is_empty() || style == "b" {
                if let Some(ch) = &mut self.chapter {
                    ch.blocks.push(Block::Para {
                        style,
                        segments: segs,
                    });
                }
            }
        }
    }

    fn flush_intro(&mut self) {
        if let Some((style, text)) = self.intro_open.take() {
            let text = text.split_whitespace().collect::<Vec<_>>().join(" ");
            if !text.is_empty() {
                self.book.intro.push(IntroBlock { style, text });
            }
        }
    }

    fn flush_pending_heading(&mut self) {
        if let Pending::Heading(kind, level, text) =
            std::mem::replace(&mut self.pending, Pending::None)
        {
            let text = text.split_whitespace().collect::<Vec<_>>().join(" ");
            if let Some(ch) = &mut self.chapter {
                ch.blocks.push(Block::Heading {
                    kind: kind.to_string(),
                    level,
                    text,
                });
            }
        }
    }

    fn end_chapter(&mut self) {
        self.flush_block();
        self.flush_pending_heading();
        if let Some(ch) = self.chapter.take() {
            self.book.chapters.push(ch);
        }
    }

    fn open_block(&mut self, style: &str) {
        self.flush_block();
        self.flush_pending_heading();
        self.block = Some((style.to_string(), Vec::new()));
        // Continuation of the current verse into the new block.
        if let Some(id) = &self.verse_id {
            self.seg = Some(Segment {
                id: Some(id.clone()),
                ..Default::default()
            });
        } else if style != "b" {
            self.seg = Some(Segment::default());
        }
    }

    fn cur_seg(&mut self) -> &mut Segment {
        if self.block.is_none() {
            // Text before any paragraph marker inside a chapter: give it a plain block.
            self.block = Some(("p".to_string(), Vec::new()));
        }
        if self.seg.is_none() {
            self.seg = Some(Segment {
                id: self.verse_id.clone(),
                ..Default::default()
            });
        }
        self.seg.as_mut().unwrap()
    }

    fn push_text(&mut self, raw: &str) {
        if raw.is_empty() {
            return;
        }
        if self.chapter.is_none() {
            if let Some((_, buf)) = &mut self.intro_open {
                buf.push_str(raw);
            }
            return;
        }
        let seg = self.cur_seg();
        for c in raw.chars() {
            if c == ' ' && (seg.text.is_empty() || seg.text.ends_with(' ')) {
                continue;
            }
            seg.text.push(c);
        }
    }

    fn text_len(&mut self) -> usize {
        self.cur_seg().text.chars().count()
    }

    fn close_note(&mut self) {
        if let Some(note) = self.note.take() {
            let text = note.text.split_whitespace().collect::<Vec<_>>().join(" ");
            let n = Note {
                kind: note.kind,
                at: note.at,
                caller: note.caller,
                reference: note.reference,
                text,
            };
            self.cur_seg().notes.push(n);
        }
    }

    fn handle_marker(&mut self, name: &str, closing: bool) {
        // Inside a footnote or cross-reference.
        if let Some(note) = &mut self.note {
            if closing && name == note.close_name.as_str() && note.depth == 0 {
                self.close_note();
                return;
            }
            // A note can never legitimately contain structure. If one reaches a
            // chapter, verse, paragraph or heading marker it was left unclosed in
            // the source: close it here, record the fault, and carry on.
            if !closing
                && (matches!(name, "c" | "v" | "b")
                    || para_style(name).is_some()
                    || heading_kind(name).is_some())
            {
                self.book
                    .unknown
                    .insert(format!("unterminated note before \\{name}"));
                self.close_note();
                self.handle_marker(name, closing);
                return;
            }
            if closing {
                if note.depth > 0 {
                    note.depth -= 1;
                }
                return;
            }
            // Note-internal markers are sometimes written with a stray `+`
            // (IRVTAM Isaiah 43:27 has `\+fr`); treat them as their plain form.
            let name = name
                .strip_prefix('+')
                .filter(|n| {
                    matches!(
                        *n,
                        "fr" | "ft"
                            | "fq"
                            | "fqa"
                            | "fk"
                            | "fl"
                            | "fp"
                            | "fw"
                            | "xo"
                            | "xt"
                            | "xq"
                            | "xk"
                            | "xta"
                            | "fv"
                    )
                })
                .unwrap_or(name);
            match name {
                "fr" | "xo" => note.part = NotePart::Ref,
                "ft" | "fq" | "fqa" | "fk" | "fl" | "fp" | "fw" | "xt" | "xq" | "xk" | "xta"
                | "fv" => {
                    note.part = NotePart::Text;
                    if matches!(name, "fq" | "fqa")
                        && !note.text.is_empty()
                        && !note.text.ends_with(' ')
                    {
                        note.text.push(' ');
                    }
                }
                "fm" | "xop" | "xot" | "xnt" | "xdc" | "fdc" => note.part = NotePart::Skip,
                n if n.starts_with('+') => note.depth += 1,
                _ => {
                    note.depth += 1;
                    self.book.unknown.insert(format!("{name} (in note)"));
                }
            }
            return;
        }

        if closing {
            if let Some(pos) = self.inline.iter().rposition(|(n, _)| n == name) {
                let (n, start) = self.inline.remove(pos);
                if n == "wj" || n == "+wj" {
                    let end = self.text_len();
                    self.cur_seg().spans.push(Span {
                        kind: "wj".into(),
                        start,
                        end,
                    });
                }
            } else if matches!(name, "f" | "x" | "fe") {
                // Stray closer, ignore.
            } else if !is_char_marker(name) && !is_dropped_with_content(name) {
                self.book.unknown.insert(format!("{name}*"));
            }
            if let Pending::Dropped(ref d) = self.pending {
                if d == name {
                    self.pending = Pending::None;
                }
            }
            return;
        }

        // Opening markers.
        match name {
            "id" => self.pending = Pending::Meta,
            "c" => {
                self.end_chapter();
                self.flush_intro();
                self.verse_id = None;
                self.inline.clear();
                self.chapter = Some(ParsedChapter::default());
                self.pending = Pending::Chapter;
            }
            "cl" => self.pending = Pending::Label,
            "v" => {
                self.flush_pending_heading();
                self.flush_seg();
                self.pending = Pending::Verse;
            }
            "mt" | "mt1" => self.pending = Pending::Title,
            "b" => {
                self.flush_block();
                self.flush_pending_heading();
                if let Some(ch) = &mut self.chapter {
                    ch.blocks.push(Block::Break);
                }
                self.block = None;
                // Keep the verse open so the next paragraph continues it.
            }
            "f" | "x" | "fe" => {
                let at = self.text_len();
                // Drop a space that only separated the note from following text.
                self.note = Some(NoteState {
                    kind: if name == "x" { "x".into() } else { "f".into() },
                    close_name: name.into(),
                    caller: None,
                    reference: None,
                    text: String::new(),
                    at,
                    depth: 0,
                    part: NotePart::Skip,
                    pending_caller: true,
                });
            }
            _ if is_dropped_with_content(name) => self.pending = Pending::Dropped(name.to_string()),
            _ if is_char_marker(name) => {
                let at = self.text_len();
                self.inline.push((name.to_string(), at));
            }
            _ if is_meta(name) => self.pending = Pending::Meta,
            _ => {
                if let Some(style) = para_style(name) {
                    self.open_block(style);
                } else if let Some((kind, level)) = heading_kind(name) {
                    self.flush_block();
                    self.flush_pending_heading();
                    // Headings end the running verse's block but not the verse itself.
                    self.pending = Pending::Heading(kind, level, String::new());
                } else if let Some(style) = intro_style(name) {
                    self.flush_intro();
                    self.intro_open = Some((style.to_string(), String::new()));
                } else {
                    self.book.unknown.insert(name.to_string());
                    self.pending = Pending::Meta;
                }
            }
        }
    }

    fn handle_text(&mut self, raw: String) {
        if let Some(note) = &mut self.note {
            let mut t = raw.as_str();
            if note.pending_caller {
                let (caller, rest) = split_number(t);
                note.caller = Some(caller);
                note.pending_caller = false;
                if rest.is_empty() {
                    return;
                }
                // `rest` borrows from a temporary; copy it out.
                let rest = rest.clone();
                match note.part {
                    NotePart::Ref => append_ref(note, &rest),
                    NotePart::Text => note.text.push_str(&rest),
                    NotePart::Skip => {}
                }
                return;
            }
            if let Some(i) = t.find('|') {
                t = &t[..i];
            }
            match note.part {
                NotePart::Ref => append_ref(note, t),
                NotePart::Text => note.text.push_str(t),
                NotePart::Skip => {}
            }
            return;
        }

        match std::mem::replace(&mut self.pending, Pending::None) {
            Pending::Chapter => {
                let (num, rest) = split_number(&raw);
                if let Some(ch) = &mut self.chapter {
                    ch.number = num.parse().unwrap_or(0);
                }
                self.push_text(&rest);
            }
            Pending::Verse => {
                let (num, rest) = split_number(&raw);
                let chapter = self.chapter.as_ref().map(|c| c.number).unwrap_or(0);
                let first = num
                    .split(['-', ','])
                    .next()
                    .unwrap_or("")
                    .trim_end_matches(|c: char| c.is_ascii_alphabetic())
                    .to_string();
                let id = format!("{}.{}.{}", self.book.code, chapter, first);
                if let Some((a, b)) = num.split_once('-') {
                    if let (Ok(a), Ok(b)) = (a.parse::<u32>(), b.parse::<u32>()) {
                        if let Some(ch) = &mut self.chapter {
                            for v in a..=b {
                                ch.bridges.insert(
                                    format!("{}.{}.{}", self.book.code, chapter, v),
                                    id.clone(),
                                );
                            }
                        }
                    }
                }
                self.verse_id = Some(id.clone());
                if self.block.is_none() {
                    self.block = Some(("p".to_string(), Vec::new()));
                }
                self.seg = Some(Segment {
                    id: Some(id),
                    n: Some(num),
                    ..Default::default()
                });
                self.push_text(&rest);
            }
            Pending::Label => {
                if let Some(ch) = &mut self.chapter {
                    ch.label = Some(raw.trim().to_string());
                }
            }
            Pending::Title => {
                if self.book.title.is_empty() {
                    self.book.title = raw.trim().to_string();
                }
            }
            Pending::Meta => {
                if self.book.code.is_empty() {
                    let (code, _) = split_number(&raw);
                    self.book.code = code;
                }
            }
            Pending::Heading(kind, level, mut text) => {
                text.push_str(&raw);
                self.pending = Pending::Heading(kind, level, text);
            }
            Pending::Dropped(name) => {
                self.pending = Pending::Dropped(name);
            }
            Pending::None => {
                let mut t = raw.as_str();
                if let Some((top, _)) = self.inline.last() {
                    if has_attributes(top) {
                        if let Some(i) = t.find('|') {
                            t = &t[..i];
                        }
                    }
                }
                self.push_text(t);
            }
        }
    }
}

fn append_ref(note: &mut NoteState, t: &str) {
    let r = note.reference.get_or_insert_with(String::new);
    r.push_str(t);
    *r = r.trim().to_string();
}

fn trim_end_in_place(s: &mut String) {
    let trimmed = s.trim_end().len();
    s.truncate(trimmed);
}

pub fn parse(src: &str) -> ParsedBook {
    let src: String = src.trim_start_matches('\u{feff}').nfc().collect();
    let mut p = Parser::new();
    for tok in tokenize(&src) {
        match tok {
            Tok::Marker { name, closing } => p.handle_marker(&name, closing),
            Tok::Text(t) => p.handle_text(t),
        }
    }
    p.end_chapter();
    p.flush_intro();
    let mut book = p.book;
    book.header = book.header.trim().to_string();
    book
}

#[cfg(test)]
mod tests {
    use super::*;

    const SAMPLE: &str = "\\id JHN  \n\\h யோவான் \n\\toc1 யோவான் \n\\mt1 யோவான் \n\\is1 Intro heading \n\\ip Intro para. \n\\c 3 \n\\cl அதிகாரம் 3 \n\\s1 Heading one \n\\p\n\\v 1 First \\w verse|strong=\"G1\"\\w* text\\f + \\fr 3:1 \\ft A note\\f* after.\n\\v 2 \\wj Red letters\\wj* and more\n\\q1 poetry continues verse two\n\\v 3-4 Bridged\n\\b\n\\p\n\\v 5 Five\n";

    #[test]
    fn parses_structure() {
        let b = parse(SAMPLE);
        assert_eq!(b.code, "JHN");
        assert_eq!(b.title, "யோவான்");
        assert_eq!(b.intro.len(), 2);
        assert_eq!(b.chapters.len(), 1);
        let ch = &b.chapters[0];
        assert_eq!(ch.number, 3);
        assert_eq!(ch.label.as_deref(), Some("அதிகாரம் 3"));
        assert!(b.unknown.is_empty(), "unknown markers: {:?}", b.unknown);
        match &ch.blocks[0] {
            Block::Heading { kind, level, text } => {
                assert_eq!(
                    (kind.as_str(), *level, text.as_str()),
                    ("s", 1, "Heading one")
                )
            }
            other => panic!("expected heading, got {other:?}"),
        }
        let Block::Para { style, segments } = &ch.blocks[1] else {
            panic!()
        };
        assert_eq!(style, "p");
        assert_eq!(segments.len(), 2);
        let v1 = &segments[0];
        assert_eq!(v1.id.as_deref(), Some("JHN.3.1"));
        assert_eq!(v1.n.as_deref(), Some("1"));
        assert_eq!(v1.text, "First verse text after.");
        assert_eq!(v1.notes.len(), 1);
        assert_eq!(v1.notes[0].reference.as_deref(), Some("3:1"));
        assert_eq!(v1.notes[0].text, "A note");
        assert_eq!(v1.notes[0].at, "First verse text".chars().count());
        let v2 = &segments[1];
        assert_eq!(v2.text, "Red letters and more");
        assert_eq!(v2.spans[0].start, 0);
        assert_eq!(v2.spans[0].end, 11);
        let Block::Para { style, segments } = &ch.blocks[2] else {
            panic!()
        };
        assert_eq!(style, "q1");
        assert_eq!(segments[0].id.as_deref(), Some("JHN.3.2"));
        assert!(
            segments[0].n.is_none(),
            "continuation must not repeat the verse number"
        );
        assert_eq!(segments[0].text, "poetry continues verse two");
        assert_eq!(segments[1].n.as_deref(), Some("3-4"));
        assert_eq!(
            ch.bridges.get("JHN.3.4").map(String::as_str),
            Some("JHN.3.3")
        );
        assert!(matches!(ch.blocks[3], Block::Break));
        let Block::Para { segments, .. } = &ch.blocks[4] else {
            panic!()
        };
        assert_eq!(segments[0].text, "Five");
    }

    #[test]
    fn kjv_style_markup() {
        let src = "\\id GEN\n\\c 1\n\\p\n\\v 1 \\w In|strong=\"H7225\"\\w* the \\nd Lord\\nd* \\add was\\add* there\\f + \\fr 1.1 \\ft Heb. note\\f*.\n";
        let b = parse(src);
        let Block::Para { segments, .. } = &b.chapters[0].blocks[0] else {
            panic!()
        };
        assert_eq!(segments[0].text, "In the Lord was there.");
        assert!(b.unknown.is_empty());
    }

    #[test]
    fn nested_plus_markers_and_xref() {
        let src = "\\id MAT\n\\c 4\n\\p\n\\v 4 \\wj \\+w Man|strong=\"G444\"\\+w* shall\\wj*\\x - \\xo 4:4 \\xt Deut 8:3\\x* live.\n";
        let b = parse(src);
        let Block::Para { segments, .. } = &b.chapters[0].blocks[0] else {
            panic!()
        };
        assert_eq!(segments[0].text, "Man shall live.");
        assert_eq!(segments[0].spans[0].kind, "wj");
        assert_eq!(segments[0].spans[0].end, "Man shall".chars().count());
        assert_eq!(segments[0].notes[0].kind, "x");
        assert_eq!(segments[0].notes[0].text, "Deut 8:3");
        assert!(b.unknown.is_empty(), "{:?}", b.unknown);
    }
}
