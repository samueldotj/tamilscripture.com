//! usfm-ingest: build the static content tree for tamilscripture.com.
//!
//! Usage:
//!   usfm-ingest --books data/books.toml --xrefs data/xrefs/cross_references.txt \
//!               --audio data/audio --out apps/web/static/content data/versions
//!
//! Each version directory holds `version.toml` and one `.usfm` file per book.
//! A directory without `version.toml` stands for every version directory in
//! it, taken in `order` (then code), so adding a version is adding a directory.
//! Output (all under --out):
//!   manifest.json                              build id, versions, books
//!   {build}/{VERSION}/{BOOK}/{chapter}.json    chapter text
//!   {build}/{VERSION}/{BOOK}/intro.json        book introduction, when present
//!   {build}/xref/{BOOK}/{chapter}.json         cross-references
//!   {build}/search/{VERSION}.csv               verse_id,version,lang,book_ord,text
//! A version whose `version.toml` has `[audio] recording = "…"` takes that
//! recording from --audio (see audio.rs) into its manifest entry and chapters.
//! Exit status is non-zero if any input fails validation.

mod audio;
mod books;
mod hash;
mod model;
mod usfm;
mod xrefs;

use anyhow::{bail, Context, Result};
use books::Books;
use model::*;
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

struct Args {
    books: PathBuf,
    xrefs: Option<PathBuf>,
    audio: Option<PathBuf>,
    out: PathBuf,
    versions: Vec<PathBuf>,
    strict: bool,
}

fn parse_args() -> Result<Args> {
    let mut a = Args {
        books: PathBuf::from("data/books.toml"),
        xrefs: None,
        audio: None,
        out: PathBuf::from("out"),
        versions: Vec::new(),
        strict: true,
    };
    let mut it = std::env::args().skip(1);
    while let Some(arg) = it.next() {
        match arg.as_str() {
            "--books" => a.books = it.next().context("--books needs a path")?.into(),
            "--xrefs" => a.xrefs = Some(it.next().context("--xrefs needs a path")?.into()),
            "--audio" => a.audio = Some(it.next().context("--audio needs a path")?.into()),
            "--out" => a.out = it.next().context("--out needs a path")?.into(),
            "--lenient" => a.strict = false,
            "-h" | "--help" => {
                eprintln!("usfm-ingest --books B --xrefs X [--audio A] --out DIR [--lenient] VERSION_DIR...");
                std::process::exit(0);
            }
            other if other.starts_with("--") => bail!("unknown flag {other}"),
            other => a.versions.push(other.into()),
        }
    }
    if a.versions.is_empty() {
        bail!("no version directories given");
    }
    Ok(a)
}

fn write_json<T: serde::Serialize>(path: &Path, value: &T) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut bytes = serde_json::to_vec(value)?;
    bytes.push(b'\n');
    fs::write(path, bytes).with_context(|| format!("writing {}", path.display()))
}

fn csv_field(s: &str) -> String {
    if s.contains(['"', ',', '\n', '\r']) {
        format!("\"{}\"", s.replace('"', "\"\""))
    } else {
        s.to_string()
    }
}

struct VersionInput {
    meta: VersionMeta,
    files: Vec<PathBuf>,
}

fn read_version(dir: &Path) -> Result<VersionInput> {
    let meta_text = fs::read_to_string(dir.join("version.toml"))
        .with_context(|| format!("{} has no version.toml", dir.display()))?;
    let meta: VersionMeta = toml::from_str(&meta_text).context("parsing version.toml")?;
    let mut files: Vec<PathBuf> = fs::read_dir(dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().map(|x| x == "usfm").unwrap_or(false))
        .collect();
    files.sort();
    Ok(VersionInput { meta, files })
}

/// Version directories named on the command line, with any parent directory
/// replaced by its version subdirectories in `order`, then code.
fn expand_versions(dirs: &[PathBuf]) -> Result<Vec<VersionInput>> {
    let mut out = Vec::new();
    for dir in dirs {
        if dir.join("version.toml").exists() {
            out.push(read_version(dir)?);
            continue;
        }
        let mut found: Vec<VersionInput> = fs::read_dir(dir)
            .with_context(|| format!("reading {}", dir.display()))?
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p.join("version.toml").exists())
            .map(|p| read_version(&p))
            .collect::<Result<_>>()?;
        if found.is_empty() {
            bail!(
                "{} has no version.toml and no version directories",
                dir.display()
            );
        }
        found.sort_by(|a, b| (a.meta.order, &a.meta.code).cmp(&(b.meta.order, &b.meta.code)));
        out.extend(found);
    }
    Ok(out)
}

fn main() -> Result<()> {
    let args = parse_args()?;
    let books = Books::load(&args.books)?;

    // Gather inputs and hash them for the build id.
    let mut hasher = hash::Fnv64::new();
    hasher.update(&fs::read(&args.books)?);
    let inputs = expand_versions(&args.versions)?;
    for v in &inputs {
        hasher.update(v.meta.code.as_bytes());
        for f in &v.files {
            hasher.update(&fs::read(f)?);
        }
    }
    // Recordings, for versions that name one; their files join the build id.
    let mut problems: Vec<String> = Vec::new();
    let mut recordings: Vec<Option<audio::Recording>> = Vec::new();
    for v in &inputs {
        let Some(want) = &v.meta.audio else {
            recordings.push(None);
            continue;
        };
        let Some(dir) = &args.audio else {
            problems.push(format!(
                "{}: version.toml names recording {} but --audio was not given",
                v.meta.code, want.recording
            ));
            recordings.push(None);
            continue;
        };
        let (rec, rec_problems) = audio::Recording::load(dir, &v.meta.code, &want.recording)?;
        problems.extend(rec_problems);
        for f in &rec.files {
            hasher.update(&fs::read(f)?);
        }
        recordings.push(Some(rec));
    }
    let xref_index = match &args.xrefs {
        Some(p) => {
            hasher.update(&fs::read(p)?);
            Some(xrefs::load(p, &books)?)
        }
        None => None,
    };
    let build = format!("{:016x}", hasher.finish())[..10].to_string();
    let build_dir = args.out.join(&build);
    if args.out.exists() {
        fs::remove_dir_all(&args.out)
            .with_context(|| format!("clearing {}", args.out.display()))?;
    }
    fs::create_dir_all(&build_dir)?;

    let mut versions_meta = Vec::new();
    // One version per code, and at most one default per language.
    let mut seen_codes = std::collections::BTreeSet::new();
    let mut default_langs = std::collections::BTreeSet::new();
    for input in &inputs {
        if !seen_codes.insert(input.meta.code.clone()) {
            problems.push(format!("{}: version code used twice", input.meta.code));
        }
        if input.meta.default && !default_langs.insert(input.meta.lang.clone()) {
            problems.push(format!(
                "{}: a second default version for language {}",
                input.meta.code, input.meta.lang
            ));
        }
    }

    for (input, recording) in inputs.iter().zip(&recordings) {
        let code = input.meta.code.clone();
        eprintln!("[{code}] {} files", input.files.len());
        let mut parsed: BTreeMap<usize, usfm::ParsedBook> = BTreeMap::new();
        for f in &input.files {
            let src = fs::read_to_string(f).with_context(|| format!("reading {}", f.display()))?;
            let book = usfm::parse(&src);
            let Some(idx) = books.index(&book.code) else {
                // Front matter (FRT) and other non-canonical ids are skipped.
                eprintln!(
                    "[{code}] skipping {} (id {})",
                    f.file_name().unwrap().to_string_lossy(),
                    book.code
                );
                continue;
            };
            let expected = books.list[idx].chapters;
            if book.chapters.len() as u32 != expected {
                problems.push(format!(
                    "{code} {}: {} chapters, books.toml says {expected}",
                    book.code,
                    book.chapters.len()
                ));
            }
            if !book.unknown.is_empty() {
                problems.push(format!(
                    "{code} {}: unknown markers {:?}",
                    book.code, book.unknown
                ));
            }
            parsed.insert(idx, book);
        }
        if let Some(rec) = recording {
            for (book, chapter) in rec.chapter_keys() {
                let known = books
                    .index(book)
                    .and_then(|i| parsed.get(&i))
                    .is_some_and(|b| b.chapters.iter().any(|c| c.number == *chapter));
                if !known {
                    problems.push(format!(
                        "{code} recording {}: {book} {chapter} is not in the text",
                        rec.meta.recording
                    ));
                }
            }
            eprintln!(
                "[{code}] audio {}: {} chapters",
                rec.meta.recording,
                rec.chapter_keys().count()
            );
        }

        // Chapter files, intro files, search CSV.
        let mut csv = String::from("verse_id,version,lang,book_ord,text\n");
        let order: Vec<usize> = parsed.keys().copied().collect();
        for (pos, &idx) in order.iter().enumerate() {
            let book = &parsed[&idx];
            let meta = &books.list[idx];
            let prev_book = pos.checked_sub(1).map(|p| &books.list[order[p]]);
            let next_book = order.get(pos + 1).map(|&n| &books.list[n]);

            if !book.intro.is_empty() {
                write_json(
                    &build_dir.join(&code).join(&meta.code).join("intro.json"),
                    &IntroJson {
                        version: code.clone(),
                        book: meta.code.clone(),
                        title: book.title.clone(),
                        blocks: book.intro.clone(),
                    },
                )?;
            }

            let n = book.chapters.len();
            for (ci, ch) in book.chapters.iter().enumerate() {
                let prev = if ci > 0 {
                    Some(ChapterRef {
                        book: meta.code.clone(),
                        chapter: book.chapters[ci - 1].number,
                    })
                } else {
                    prev_book.map(|b| ChapterRef {
                        book: b.code.clone(),
                        chapter: b.chapters,
                    })
                };
                let next = if ci + 1 < n {
                    Some(ChapterRef {
                        book: meta.code.clone(),
                        chapter: book.chapters[ci + 1].number,
                    })
                } else {
                    next_book.map(|b| ChapterRef {
                        book: b.code.clone(),
                        chapter: 1,
                    })
                };
                let json = ChapterJson {
                    version: code.clone(),
                    book: meta.code.clone(),
                    chapter: ch.number,
                    build: build.clone(),
                    label: ch.label.clone(),
                    blocks: ch.blocks.clone(),
                    bridges: ch.bridges.clone(),
                    prev,
                    next,
                    audio: recording
                        .as_ref()
                        .and_then(|r| r.chapter(&code, &meta.code, ch.number)),
                };
                write_json(
                    &build_dir
                        .join(&code)
                        .join(&meta.code)
                        .join(format!("{}.json", ch.number)),
                    &json,
                )?;

                // Search rows: one per verse id, text joined across segments.
                let mut verse_text: BTreeMap<String, String> = BTreeMap::new();
                let mut verse_order: Vec<String> = Vec::new();
                for block in &ch.blocks {
                    if let Block::Para { segments, .. } = block {
                        for seg in segments {
                            let Some(id) = &seg.id else { continue };
                            let entry = verse_text.entry(id.clone()).or_insert_with(|| {
                                verse_order.push(id.clone());
                                String::new()
                            });
                            if !entry.is_empty() && !seg.text.is_empty() {
                                entry.push(' ');
                            }
                            entry.push_str(&seg.text);
                        }
                    }
                }
                for id in verse_order {
                    let text = &verse_text[&id];
                    if text.is_empty() {
                        continue;
                    }
                    csv.push_str(&format!(
                        "{},{},{},{},{}\n",
                        id,
                        code,
                        input.meta.lang,
                        meta.order,
                        csv_field(text)
                    ));
                }
            }
        }
        let search_dir = build_dir.join("search");
        fs::create_dir_all(&search_dir)?;
        fs::write(search_dir.join(format!("{code}.csv")), csv)?;
        let mut meta = input.meta.clone();
        meta.audio = recording.as_ref().map(|r| r.meta.clone());
        meta.books = order.iter().map(|&i| books.list[i].code.clone()).collect();
        // books.toml names the books in Tamil and English; any other language
        // takes them from the version's own \h headers.
        if meta.lang != "ta" && meta.lang != "en" {
            for &idx in &order {
                let header = parsed[&idx].header.trim();
                if !header.is_empty() {
                    meta.book_names
                        .insert(books.list[idx].code.clone(), header.to_string());
                }
            }
        }
        versions_meta.push(meta);
    }

    if let Some(index) = &xref_index {
        let mut count = 0usize;
        for ((book, chapter), map) in index {
            write_json(
                &build_dir
                    .join("xref")
                    .join(book)
                    .join(format!("{chapter}.json")),
                map,
            )?;
            count += map.values().map(Vec::len).sum::<usize>();
        }
        eprintln!("[xref] {count} references in {} chapters", index.len());
    }

    let default_version = versions_meta
        .iter()
        .find(|v| v.default)
        .or(versions_meta.first())
        .map(|v| v.code.clone())
        .unwrap_or_default();
    write_json(
        &args.out.join("manifest.json"),
        &Manifest {
            build: build.clone(),
            default_version,
            versions: versions_meta,
            books: books.list.clone(),
        },
    )?;

    if !problems.is_empty() {
        eprintln!("validation:");
        for p in &problems {
            eprintln!("  - {p}");
        }
        if args.strict {
            bail!(
                "{} validation problem(s); pass --lenient to write output anyway",
                problems.len()
            );
        }
    }
    eprintln!("build {build} written to {}", args.out.display());
    Ok(())
}
