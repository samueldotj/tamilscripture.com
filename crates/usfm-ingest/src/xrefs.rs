//! OpenBible.info cross-references: TSV `From Verse\tTo Verse\tVotes` with
//! ids like `Gen.1.1` and ranges like `Ps.121.1-Ps.121.2`.

use crate::books::Books;
use crate::model::{XrefChapter, XrefTarget};
use anyhow::{bail, Context, Result};
use std::collections::BTreeMap;
use std::path::Path;

/// (book code, chapter) -> chapter map.
pub type XrefIndex = BTreeMap<(String, u32), XrefChapter>;

fn to_id(books: &Books, ob: &str) -> Result<(String, u32, String)> {
    let mut parts = ob.split('.');
    let (Some(b), Some(c), Some(v)) = (parts.next(), parts.next(), parts.next()) else {
        bail!("bad reference {ob}");
    };
    let book = books
        .by_openbible(b)
        .with_context(|| format!("unknown OpenBible book {b} in {ob}"))?;
    let ch: u32 = c.parse().with_context(|| format!("bad chapter in {ob}"))?;
    Ok((book.code.clone(), ch, format!("{}.{}.{}", book.code, ch, v)))
}

pub fn load(path: &Path, books: &Books) -> Result<XrefIndex> {
    let text =
        std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    let mut index: XrefIndex = BTreeMap::new();
    for (lineno, line) in text.lines().enumerate().skip(1) {
        if line.trim().is_empty() {
            continue;
        }
        let cols: Vec<&str> = line.split('\t').collect();
        if cols.len() < 3 {
            bail!("line {}: expected 3 columns", lineno + 1);
        }
        let (from_book, from_ch, from_id) = to_id(books, cols[0].trim())?;
        let (to_start, to_end) = match cols[1].trim().split_once('-') {
            Some((a, b)) => (a, Some(b)),
            None => (cols[1].trim(), None),
        };
        let (_, _, to_id_start) = to_id(books, to_start)?;
        let end = match to_end {
            Some(e) => Some(to_id(books, e)?.2),
            None => None,
        };
        let votes: i32 = cols[2].trim().parse().unwrap_or(0);
        index
            .entry((from_book, from_ch))
            .or_default()
            .entry(from_id)
            .or_default()
            .push(XrefTarget {
                to: to_id_start,
                end,
                votes,
            });
    }
    for chapter in index.values_mut() {
        for targets in chapter.values_mut() {
            targets.sort_by(|a, b| b.votes.cmp(&a.votes).then_with(|| a.to.cmp(&b.to)));
        }
    }
    Ok(index)
}
