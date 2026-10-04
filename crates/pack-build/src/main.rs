//! pack-build — the Android app's content packs (tamilscripture.app design §7).
//!
//! Reads the content build the website already serves (`apps/web/static/content`)
//! and writes, under `--out`:
//!
//! ```text
//! packs/bible.IRVTAM/{n}/bible.IRVTAM.sqlite.zst   one per version
//! packs/xref/{n}/xref.sqlite.zst                   cross-references
//! packs/commentary.henry/{n}/….sqlite.zst          one per commentary (with --commentary)
//! packs/study.words/{n}/….sqlite.zst               study data from `entities/`, four packs
//! packs/catalogue.json (+ .sig)                    what exists, sizes, SHA-256
//! app/bootstrap.json  (+ .sig)                     where each origin lives
//! ```
//!
//! Bible packs keep the website's chapter JSON unchanged (app ADR-4) and add a
//! `verse` table plus a contentless FTS5 index over text normalised by
//! `tamil-norm`, so the phone never indexes anything. A trigram index for
//! misspellings would add 7.7 MB per Tamil pack (12.4 MB instead of 4.7 MB),
//! so misspelling-tolerant search stays online (app design §8.3). Output is deterministic:
//! two runs over the same content give identical bytes.
//!
//! Usage:
//!   pack-build --content apps/web/static/content --out dist/app \
//!              [--previous published-catalogue.json] [--pack-version 1] [--key signing.key]
//!              [--commentary dist/commentary/{version}] [--commentary-skip ecf]
//!
//! Commentary packs come from a published commentary version (the bible-commentaries
//! repository's output: `index.json` and `{source}/{BOOK}/{chapter}.json`). Without
//! `--commentary`, the commentary packs of the previous catalogue are carried over
//! unchanged, so a website deploy only rebuilds them when a new version is published.
//!
//! Pack bytes depend only on their content (no build ids or version numbers inside),
//! so with `--previous` an unchanged pack keeps its published version and file, and
//! phones re-download only what changed.

use anyhow::{bail, Context, Result};
use ed25519_dalek::{Signer, SigningKey};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use unicode_normalization::UnicodeNormalization;

/// Bumped when a table changes shape; the app refuses packs newer than it knows.
const SCHEMA: u32 = 1;

#[derive(Deserialize)]
struct Manifest {
    build: String,
    versions: Vec<Version>,
    books: Vec<Book>,
}

#[derive(Deserialize)]
struct Version {
    code: String,
    lang: String,
    name: String,
    #[serde(default)]
    name_native: Option<String>,
    #[serde(default)]
    short: Option<String>,
    #[serde(default)]
    licence: String,
    #[serde(default)]
    attribution: String,
    #[serde(default)]
    source_url: Option<String>,
    #[serde(default)]
    default: bool,
    #[serde(default)]
    books: Vec<String>,
}

#[derive(Deserialize, Clone)]
struct Book {
    code: String,
    order: u32,
    testament: String,
    chapters: u32,
    name_en: String,
    name_ta: String,
}

#[derive(Serialize)]
struct Title {
    ta: String,
    en: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct CatalogueEntry {
    id: String,
    #[serde(rename = "type")]
    kind: String,
    lang: String,
    version: u32,
    schema: u32,
    min_app: u32,
    title: Title,
    licence: String,
    attribution: String,
    path: String,
    size: u64,
    raw_size: u64,
    sha256: String,
    raw_sha256: String,
    starter: bool,
    build: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Catalogue {
    schema: u32,
    content_build: String,
    min_app: u32,
    config: BTreeMap<String, Value>,
    content: BTreeMap<String, String>,
    commentary: BTreeMap<String, String>,
    packs: Vec<Value>,
}

/// The catalogue currently published, used to keep version numbers stable.
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct PreviousEntry {
    id: String,
    #[serde(rename = "type", default)]
    kind: String,
    #[serde(default)]
    build: String,
    version: u32,
    path: String,
    size: u64,
    sha256: String,
    raw_sha256: String,
}

#[derive(Deserialize)]
struct PreviousCatalogue {
    packs: Vec<Value>,
}

/// Where a pack's bytes go: an unchanged pack keeps its published version and file,
/// a changed one gets the next version number, a new one starts at `--pack-version`.
struct Placement {
    version: u32,
    path: String,
    size: u64,
    sha256: String,
    reused: bool,
}

fn place(
    out: &Path,
    id: &str,
    file: &str,
    raw: &[u8],
    prev: &BTreeMap<String, PreviousEntry>,
    first: u32,
) -> Result<Placement> {
    let raw_sha = hex(&Sha256::digest(raw));
    if let Some(p) = prev.get(id) {
        if p.raw_sha256 == raw_sha {
            return Ok(Placement {
                version: p.version,
                path: p.path.clone(),
                size: p.size,
                sha256: p.sha256.clone(),
                reused: true,
            });
        }
    }
    let version = prev.get(id).map_or(first, |p| p.version + 1);
    let rel = format!("packs/{id}/{version}/{file}");
    let path = out.join(&rel);
    fs::create_dir_all(path.parent().unwrap())?;
    let compressed = zstd::encode_all(raw, 19)?;
    fs::write(&path, &compressed)?;
    Ok(Placement {
        version,
        path: rel,
        size: compressed.len() as u64,
        sha256: hex(&Sha256::digest(&compressed)),
        reused: false,
    })
}

struct Args {
    content: PathBuf,
    out: PathBuf,
    pack_version: u32,
    key: Option<PathBuf>,
    only: Option<Vec<String>>,
    previous: Option<PathBuf>,
    commentary: Option<PathBuf>,
    commentary_skip: Vec<String>,
}

fn args() -> Result<Args> {
    let mut a = std::env::args().skip(1);
    let (mut content, mut out, mut pack_version, mut key, mut only, mut previous) =
        (None, None, None, None, None, None);
    let mut commentary = None;
    // The Early Church Fathers stay out of the app for now (app requirements §7.1).
    let mut commentary_skip = vec!["ecf".to_string()];
    while let Some(k) = a.next() {
        let v = a.next().with_context(|| format!("{k} needs a value"))?;
        match k.as_str() {
            "--content" => content = Some(PathBuf::from(v)),
            "--out" => out = Some(PathBuf::from(v)),
            "--pack-version" => pack_version = Some(v.parse()?),
            "--key" => key = Some(PathBuf::from(v)),
            "--only" => only = Some(v.split(',').map(|s| s.trim().to_uppercase()).collect()),
            "--previous" => previous = Some(PathBuf::from(v)),
            "--commentary" => commentary = Some(PathBuf::from(v)),
            "--commentary-skip" => {
                commentary_skip = v
                    .split(',')
                    .map(|s| s.trim().to_string())
                    .filter(|s| !s.is_empty())
                    .collect()
            }
            _ => bail!("unknown argument {k}"),
        }
    }
    Ok(Args {
        content: content.context("--content is required")?,
        out: out.context("--out is required")?,
        pack_version: pack_version.unwrap_or(1),
        key,
        only,
        previous,
        commentary,
        commentary_skip,
    })
}

fn main() -> Result<()> {
    // `pack-build --print-public <keyfile>`: the verifying key the app embeds.
    let raw: Vec<String> = std::env::args().collect();
    if raw.get(1).map(String::as_str) == Some("--print-public") {
        let key = load_key(Path::new(
            raw.get(2).context("--print-public needs a key file")?,
        ))?;
        println!("{}", hex(key.verifying_key().as_bytes()));
        return Ok(());
    }
    let args = args()?;
    let manifest: Manifest =
        serde_json::from_slice(&fs::read(args.content.join("manifest.json"))?)?;
    let build_dir = args.content.join(&manifest.build);
    let packs_dir = args.out.join("packs");
    fs::create_dir_all(&packs_dir)?;
    let n = args.pack_version;
    let mut entries = Vec::new();
    // Previous entries as published (to carry over) and parsed (to keep versions stable).
    let prev_raw: Vec<Value> = match &args.previous {
        Some(p) if p.exists() => serde_json::from_slice::<PreviousCatalogue>(&fs::read(p)?)
            .map(|c| c.packs)
            .unwrap_or_default(),
        _ => Vec::new(),
    };
    let prev: BTreeMap<String, PreviousEntry> = prev_raw
        .iter()
        .filter_map(|v| serde_json::from_value::<PreviousEntry>(v.clone()).ok())
        .map(|e| (e.id.clone(), e))
        .collect();

    for v in &manifest.versions {
        if let Some(only) = &args.only {
            if !only.contains(&v.code) {
                continue;
            }
        }
        let id = format!("bible.{}", v.code);
        let (rows, raw) = build_bible(&build_dir, &manifest, v)?;
        let pl = place(&args.out, &id, &format!("{id}.sqlite.zst"), &raw, &prev, n)?;
        println!(
            "{id}: {rows} rows → v{} {} KB{}",
            pl.version,
            pl.size / 1024,
            if pl.reused { " (unchanged)" } else { "" }
        );
        let raw_size = raw.len() as u64;
        let raw_sha256 = hex(&Sha256::digest(&raw));
        entries.push(CatalogueEntry {
            id,
            kind: "bible".into(),
            lang: v.lang.clone(),
            version: pl.version,
            schema: SCHEMA,
            min_app: 1,
            title: Title {
                ta: v.name_native.clone().unwrap_or_else(|| v.name.clone()),
                en: v.name.clone(),
            },
            licence: v.licence.clone(),
            attribution: v.attribution.clone(),
            path: pl.path,
            size: pl.size,
            raw_size,
            sha256: pl.sha256,
            raw_sha256,
            starter: v.default || v.code == "BSB",
            build: manifest.build.clone(),
        });
    }

    if args
        .only
        .as_ref()
        .is_none_or(|o| o.iter().any(|c| c == "XREF"))
    {
        let (rows, raw) = build_xref(&build_dir, &manifest)?;
        let pl = place(&args.out, "xref", "xref.sqlite.zst", &raw, &prev, n)?;
        println!(
            "xref: {rows} rows → v{} {} KB{}",
            pl.version,
            pl.size / 1024,
            if pl.reused { " (unchanged)" } else { "" }
        );
        let raw_size = raw.len() as u64;
        let raw_sha256 = hex(&Sha256::digest(&raw));
        entries.push(CatalogueEntry {
            id: "xref".into(),
            kind: "xref".into(),
            lang: "".into(),
            version: pl.version,
            schema: SCHEMA,
            min_app: 1,
            title: Title { ta: "தொடர்புள்ள வசனங்கள்".into(), en: "Cross-references".into() },
            licence: "CC BY 4.0".into(),
            attribution: "OpenBible.info cross references, CC BY 4.0, merged with the translations' own references".into(),
            path: pl.path,
            size: pl.size,
            raw_size,
            sha256: pl.sha256,
            raw_sha256,
            starter: true,
            build: manifest.build.clone(),
        });
    }

    // Study data (app roadmap M8-1): the website's entities/ files, grouped into packs.
    let entities = build_dir.join("entities");
    if entities.is_dir()
        && args
            .only
            .as_ref()
            .is_none_or(|o| o.iter().any(|c| c == "STUDY"))
    {
        for spec in STUDY_PACKS {
            let (rows, raw) = build_files(&entities, spec.prefixes)?;
            let pl = place(
                &args.out,
                spec.id,
                &format!("{}.sqlite.zst", spec.id),
                &raw,
                &prev,
                n,
            )?;
            println!(
                "{}: {rows} files → v{} {} KB{}",
                spec.id,
                pl.version,
                pl.size / 1024,
                if pl.reused { " (unchanged)" } else { "" }
            );
            let raw_size = raw.len() as u64;
            let raw_sha256 = hex(&Sha256::digest(&raw));
            entries.push(CatalogueEntry {
                id: spec.id.into(),
                kind: "study".into(),
                lang: "".into(),
                version: pl.version,
                schema: SCHEMA,
                min_app: 1,
                title: Title {
                    ta: spec.title_ta.into(),
                    en: spec.title_en.into(),
                },
                licence: spec.licence.into(),
                attribution: spec.attribution.into(),
                path: pl.path,
                size: pl.size,
                raw_size,
                sha256: pl.sha256,
                raw_sha256,
                starter: false,
                build: manifest.build.clone(),
            });
        }
    }

    let mut entries: Vec<Value> = entries
        .into_iter()
        .map(serde_json::to_value)
        .collect::<Result<_, _>>()?;
    match &args.commentary {
        Some(dir) => entries.extend(commentary_packs(
            &args.out,
            dir,
            &args.commentary_skip,
            &prev,
            &prev_raw,
            n,
        )?),
        None => {
            let carried: Vec<Value> = prev_raw
                .iter()
                .filter(|v| v["type"] == "commentary")
                .cloned()
                .collect();
            if !carried.is_empty() {
                println!(
                    "commentary: {} packs carried over from the published catalogue",
                    carried.len()
                );
            }
            entries.extend(carried);
        }
    }

    let mut config = BTreeMap::new();
    config.insert("stats.read.minVisible".into(), Value::from(0.6));
    config.insert("stats.read.minMs".into(), Value::from(2000));
    let catalogue = Catalogue {
        schema: 1,
        content_build: manifest.build.clone(),
        min_app: 1,
        config,
        content: BTreeMap::from([("manifest".into(), "content/manifest.json".into())]),
        commentary: BTreeMap::from([("pointer".into(), "commentary/latest.json".into())]),
        packs: entries,
    };
    let key = args.key.as_deref().map(load_key).transpose()?;
    write_signed(
        &packs_dir.join("catalogue.json"),
        &serde_json::to_vec_pretty(&catalogue)?,
        key.as_ref(),
    )?;
    let bootstrap = serde_json::json!({
        "schema": 1,
        "origins": {
            "content": ["https://www.tamilscripture.com/"],
            "packs": ["https://packs.tamilaudiobible.com/"],
            "commentary": ["https://stream.tamilaudiobible.com/"],
            "audio": ["https://stream.tamilaudiobible.com/"],
            "api": ["https://www.tamilscripture.com/"]
        },
        "catalogue": "packs/catalogue.json"
    });
    fs::create_dir_all(args.out.join("app"))?;
    write_signed(
        &args.out.join("app/bootstrap.json"),
        &serde_json::to_vec_pretty(&bootstrap)?,
        key.as_ref(),
    )?;
    if key.is_none() {
        eprintln!("note: no --key given, catalogue and bootstrap are unsigned");
    }
    Ok(())
}

#[derive(Deserialize)]
struct CommentaryIndex {
    sources: Vec<CommentarySource>,
    /// source → book → chapters (0 is the book's introduction)
    chapters: BTreeMap<String, BTreeMap<String, Vec<u32>>>,
}

#[derive(Deserialize, Serialize)]
struct CommentarySource {
    id: String,
    name: String,
    short: String,
    #[serde(default)]
    year: String,
    #[serde(default)]
    title: String,
    #[serde(default)]
    desc_ta: String,
    #[serde(default)]
    desc_en: String,
    #[serde(default)]
    licence: String,
    #[serde(default)]
    attribution: String,
}

/// One pack per commentary in a published commentary version. A source whose pack was
/// already built from this version is carried over without reading its files again.
fn commentary_packs(
    out: &Path,
    dir: &Path,
    skip: &[String],
    prev: &BTreeMap<String, PreviousEntry>,
    prev_raw: &[Value],
    first: u32,
) -> Result<Vec<Value>> {
    let version = dir
        .file_name()
        .and_then(|n| n.to_str())
        .context("--commentary must be a version directory")?
        .to_string();
    let index: CommentaryIndex = serde_json::from_slice(&fs::read(dir.join("index.json"))?)
        .with_context(|| format!("reading {}/index.json", dir.display()))?;
    let mut out_entries = Vec::new();
    for src in &index.sources {
        if skip.contains(&src.id) {
            continue;
        }
        let id = format!("commentary.{}", src.id);
        if prev
            .get(&id)
            .is_some_and(|p| p.kind == "commentary" && p.build == version)
        {
            if let Some(v) = prev_raw.iter().find(|v| v["id"] == id.as_str()) {
                println!("{id}: built from {version} already (unchanged)");
                out_entries.push(v.clone());
                continue;
            }
        }
        let chapters = index.chapters.get(&src.id).cloned().unwrap_or_default();
        let (rows, raw) = build_commentary(dir, src, &chapters)?;
        let pl = place(out, &id, &format!("{id}.sqlite.zst"), &raw, prev, first)?;
        println!(
            "{id}: {rows} chapters → v{} {} KB{}",
            pl.version,
            pl.size / 1024,
            if pl.reused { " (unchanged)" } else { "" }
        );
        out_entries.push(serde_json::to_value(CatalogueEntry {
            id,
            kind: "commentary".into(),
            lang: "en".into(),
            version: pl.version,
            schema: SCHEMA,
            min_app: 1,
            title: Title {
                ta: format!("{} · {}", src.short, src.desc_ta),
                en: format!("{} · {}", src.short, src.desc_en),
            },
            licence: src.licence.clone(),
            attribution: src.attribution.clone(),
            path: pl.path,
            size: pl.size,
            raw_size: raw.len() as u64,
            sha256: pl.sha256,
            raw_sha256: hex(&Sha256::digest(&raw)),
            starter: false,
            build: version.clone(),
        })?);
    }
    Ok(out_entries)
}

/// A commentary pack keeps each chapter's published JSON unchanged, so the app reads a
/// downloaded chapter exactly as it reads one from the CDN. `meta.source` holds the
/// source's entry from `index.json`, for showing it while offline.
fn build_commentary(
    dir: &Path,
    src: &CommentarySource,
    chapters: &BTreeMap<String, Vec<u32>>,
) -> Result<(usize, Vec<u8>)> {
    let conn = open()?;
    conn.execute_batch(
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
         CREATE TABLE chapter (book TEXT NOT NULL, chapter INTEGER NOT NULL, body TEXT NOT NULL,
                               PRIMARY KEY (book, chapter)) WITHOUT ROWID;",
    )?;
    let meta = [
        ("pack_id", format!("commentary.{}", src.id)),
        ("schema", SCHEMA.to_string()),
        ("source", serde_json::to_string(src)?),
    ];
    for (k, v) in meta {
        conn.execute("INSERT INTO meta VALUES (?1, ?2)", params![k, v])?;
    }
    let mut rows = 0;
    let tx = conn.unchecked_transaction()?;
    for (book, list) in chapters {
        for ch in list {
            // Chapter 0 is the book's introduction, published as intro.json.
            let file = if *ch == 0 {
                "intro.json".to_string()
            } else {
                format!("{ch}.json")
            };
            let path = dir.join(&src.id).join(book).join(file);
            let body =
                fs::read_to_string(&path).with_context(|| format!("reading {}", path.display()))?;
            tx.execute(
                "INSERT INTO chapter VALUES (?1, ?2, ?3)",
                params![book, ch, body],
            )?;
            rows += 1;
        }
    }
    tx.commit()?;
    Ok((rows, finish(conn)?))
}

fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

fn load_key(p: &Path) -> Result<SigningKey> {
    let text = fs::read_to_string(p).with_context(|| format!("reading {}", p.display()))?;
    let bytes: Vec<u8> = (0..64)
        .step_by(2)
        .map(|i| u8::from_str_radix(&text.trim()[i..i + 2], 16))
        .collect::<Result<_, _>>()
        .context("key must be 64 hex characters (a 32-byte Ed25519 seed)")?;
    Ok(SigningKey::from_bytes(&bytes.try_into().unwrap()))
}

fn write_signed(path: &Path, body: &[u8], key: Option<&SigningKey>) -> Result<()> {
    fs::create_dir_all(path.parent().unwrap())?;
    fs::write(path, body)?;
    if let Some(k) = key {
        let sig = k.sign(body);
        fs::write(path.with_extension("json.sig"), hex(&sig.to_bytes()))?;
    }
    Ok(())
}

/// Fresh database in memory, written out with VACUUM INTO for stable bytes.
fn finish(conn: Connection) -> Result<Vec<u8>> {
    let tmp = std::env::temp_dir().join(format!("pack-build-{}.sqlite", std::process::id()));
    let _ = fs::remove_file(&tmp);
    conn.execute("VACUUM INTO ?1", params![tmp.to_string_lossy()])?;
    let bytes = fs::read(&tmp)?;
    fs::remove_file(&tmp)?;
    Ok(bytes)
}

fn open() -> Result<Connection> {
    let conn = Connection::open_in_memory()?;
    conn.execute_batch(&format!(
        "PRAGMA page_size = 4096; PRAGMA user_version = {SCHEMA};"
    ))?;
    Ok(conn)
}

fn norm(text: &str) -> String {
    let nfc: String = text.nfc().collect();
    tamil_norm::normalize(&nfc)
}

/// The search index over `tamil_norm` text. Tamil vowel signs and the virama are
/// combining marks (Mn, Mc), which `unicode61` treats as separators by default, so
/// அன்பு would be indexed as அன + ப and match அனுப்பு. Counting marks as token
/// characters keeps whole words, like the website's `tamil_tsvector`.
const FTS_TABLE: &str = "CREATE VIRTUAL TABLE verse_fts USING fts5(norm, content='', contentless_delete=1,
                                                   tokenize=\"unicode61 remove_diacritics 0 categories 'L* N* Co Mn Mc'\");";

fn verse_key(order: u32, chapter: u32, verse: u32) -> i64 {
    order as i64 * 1_000_000 + chapter as i64 * 1_000 + verse as i64
}

fn build_bible(build_dir: &Path, m: &Manifest, v: &Version) -> Result<(usize, Vec<u8>)> {
    let conn = open()?;
    conn.execute_batch(&format!(
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
         CREATE TABLE book (code TEXT PRIMARY KEY, ord INTEGER NOT NULL, testament TEXT NOT NULL,
                            name TEXT NOT NULL, chapters INTEGER NOT NULL);
         CREATE TABLE chapter (book TEXT NOT NULL, chapter INTEGER NOT NULL, body TEXT NOT NULL,
                               PRIMARY KEY (book, chapter)) WITHOUT ROWID;
         CREATE TABLE verse (id INTEGER PRIMARY KEY, book TEXT NOT NULL, chapter INTEGER NOT NULL,
                             verse INTEGER NOT NULL, text TEXT NOT NULL);
         {FTS_TABLE}",
    ))?;
    let meta = [
        ("pack_id", format!("bible.{}", v.code)),
        ("schema", SCHEMA.to_string()),
        ("version_code", v.code.clone()),
        ("language", v.lang.clone()),
        ("name_en", v.name.clone()),
        ("name_ta", v.name_native.clone().unwrap_or_default()),
        ("short", v.short.clone().unwrap_or_else(|| v.code.clone())),
        ("licence", v.licence.clone()),
        ("attribution", v.attribution.clone()),
        ("source_url", v.source_url.clone().unwrap_or_default()),
    ];
    let tx = conn.unchecked_transaction()?;
    for (k, val) in meta {
        tx.execute("INSERT INTO meta VALUES (?1, ?2)", params![k, val])?;
    }
    let mut rows = 0usize;
    let books: Vec<&Book> = m
        .books
        .iter()
        .filter(|b| v.books.is_empty() || v.books.contains(&b.code))
        .collect();
    for b in &books {
        let dir = build_dir.join(&v.code).join(&b.code);
        if !dir.exists() {
            continue;
        }
        tx.execute(
            "INSERT INTO book VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                b.code,
                b.order,
                b.testament,
                if v.lang == "ta" {
                    &b.name_ta
                } else {
                    &b.name_en
                },
                b.chapters
            ],
        )?;
        for ch in 1..=b.chapters {
            let f = dir.join(format!("{ch}.json"));
            let Ok(body) = fs::read_to_string(&f) else {
                continue;
            };
            tx.execute(
                "INSERT INTO chapter VALUES (?1, ?2, ?3)",
                params![b.code, ch, body],
            )?;
            let json: Value =
                serde_json::from_str(&body).with_context(|| f.display().to_string())?;
            // Join a verse's segments (poetry lines, split paragraphs) in order.
            let mut verses: Vec<(u32, String)> = Vec::new();
            for block in json["blocks"].as_array().into_iter().flatten() {
                for seg in block["segments"].as_array().into_iter().flatten() {
                    let Some(id) = seg["id"].as_str() else {
                        continue;
                    };
                    let Some(n) = id
                        .split('.')
                        .nth(2)
                        .and_then(|x| x.split('-').next())
                        .and_then(|x| x.parse::<u32>().ok())
                    else {
                        continue;
                    };
                    let text = seg["text"].as_str().unwrap_or("");
                    match verses.last_mut() {
                        Some((last, t)) if *last == n => {
                            t.push(' ');
                            t.push_str(text);
                        }
                        _ => verses.push((n, text.to_string())),
                    }
                }
            }
            for (n, text) in verses {
                let key = verse_key(b.order, ch, n);
                let normed = norm(&text);
                tx.execute(
                    "INSERT OR REPLACE INTO verse VALUES (?1, ?2, ?3, ?4, ?5)",
                    params![key, b.code, ch, n, text],
                )?;
                tx.execute(
                    "INSERT INTO verse_fts(rowid, norm) VALUES (?1, ?2)",
                    params![key, normed],
                )?;
                rows += 1;
            }
        }
    }
    tx.commit()?;
    conn.execute_batch("INSERT INTO verse_fts(verse_fts) VALUES('optimize');")?;
    Ok((rows, finish(conn)?))
}

struct StudyPack {
    id: &'static str,
    /// Paths under entities/ that go in the pack: a directory ("strongs/") or a file.
    prefixes: &'static [&'static str],
    title_ta: &'static str,
    title_en: &'static str,
    licence: &'static str,
    attribution: &'static str,
}

const STUDY_PACKS: &[StudyPack] = &[
    StudyPack {
        id: "study.words",
        prefixes: &["strongs/", "original/"],
        title_ta: "மூல மொழிச் சொற்கள் · ஸ்ட்ராங்ஸ்",
        title_en: "Original words · Strong's",
        licence: "CC BY 4.0",
        attribution: "STEPBible.org (Tyndale House, Cambridge): TAHOT, TAGNT, TBESH, TBESG, CC BY 4.0",
    },
    StudyPack {
        id: "study.people",
        prefixes: &["person/", "place/", "mentions/", "people.json", "places.json", "glossary.json", "journeys.json", "church.json"],
        title_ta: "நபர்களும் இடங்களும்",
        title_en: "People and places",
        licence: "CC BY 4.0",
        attribution: "STEPBible TIPNR (CC BY 4.0), OpenBible.info geocoding (CC BY 4.0), BibleAquifer (CC BY-SA 4.0)",
    },
    StudyPack {
        id: "study.dictionary",
        prefixes: &["articles/"],
        title_ta: "வேத அகராதி",
        title_en: "Bible dictionary",
        licence: "Public domain and CC BY-SA 4.0",
        attribution: "Easton's and Smith's Bible Dictionaries (public domain); BibleAquifer articles (CC BY-SA 4.0)",
    },
    StudyPack {
        id: "study.maps",
        prefixes: &["maps/", "geo/"],
        title_ta: "வரைபடங்கள்",
        title_en: "Maps",
        licence: "CC BY 4.0 and public domain",
        attribution: "Natural Earth (public domain), OpenBible.info (CC BY 4.0), Cliopatria (CC BY 4.0)",
    },
];

/// A study pack keeps each entities/ file unchanged under its path, so the app reads a
/// downloaded file exactly as it reads one from the website (`content/{build}/entities/{path}`).
fn build_files(entities: &Path, prefixes: &[&str]) -> Result<(usize, Vec<u8>)> {
    let conn = open()?;
    conn.execute_batch(
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
         CREATE TABLE file (path TEXT PRIMARY KEY, body TEXT NOT NULL) WITHOUT ROWID;",
    )?;
    conn.execute(
        "INSERT INTO meta VALUES ('schema', ?1)",
        params![SCHEMA.to_string()],
    )?;
    let mut paths = Vec::new();
    for prefix in prefixes {
        let p = entities.join(prefix.trim_end_matches('/'));
        if p.is_file() {
            paths.push(p);
        } else if p.is_dir() {
            collect_files(&p, &mut paths)?;
        }
    }
    paths.sort();
    let tx = conn.unchecked_transaction()?;
    for path in &paths {
        let rel = path
            .strip_prefix(entities)?
            .to_string_lossy()
            .replace('\\', "/");
        tx.execute(
            "INSERT INTO file VALUES (?1, ?2)",
            params![rel, fs::read_to_string(path)?],
        )?;
    }
    tx.commit()?;
    Ok((paths.len(), finish(conn)?))
}

fn collect_files(dir: &Path, out: &mut Vec<PathBuf>) -> Result<()> {
    for e in fs::read_dir(dir)? {
        let p = e?.path();
        if p.is_dir() {
            collect_files(&p, out)?;
        } else {
            out.push(p);
        }
    }
    Ok(())
}

fn build_xref(build_dir: &Path, m: &Manifest) -> Result<(usize, Vec<u8>)> {
    let conn = open()?;
    conn.execute_batch(
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
         CREATE TABLE xref (from_id TEXT NOT NULL, rank INTEGER NOT NULL, to_id TEXT NOT NULL,
                            to_end TEXT, votes INTEGER NOT NULL, PRIMARY KEY (from_id, rank)) WITHOUT ROWID;",
    )?;
    let tx = conn.unchecked_transaction()?;
    for (k, val) in [
        ("pack_id", "xref".to_string()),
        ("schema", SCHEMA.to_string()),
    ] {
        tx.execute("INSERT INTO meta VALUES (?1, ?2)", params![k, val])?;
    }
    let mut rows = 0;
    for b in &m.books {
        for ch in 1..=b.chapters {
            let f = build_dir
                .join("xref")
                .join(&b.code)
                .join(format!("{ch}.json"));
            let Ok(body) = fs::read(&f) else { continue };
            let map: BTreeMap<String, Vec<Value>> = serde_json::from_slice(&body)?;
            for (from, list) in map {
                for (rank, r) in list.iter().enumerate() {
                    tx.execute(
                        "INSERT INTO xref VALUES (?1, ?2, ?3, ?4, ?5)",
                        params![
                            from,
                            rank as i64,
                            r["to"].as_str().unwrap_or(""),
                            r["end"].as_str(),
                            r["votes"].as_i64().unwrap_or(0)
                        ],
                    )?;
                    rows += 1;
                }
            }
        }
    }
    tx.commit()?;
    Ok((rows, finish(conn)?))
}

#[cfg(test)]
mod tests {
    use super::{build_commentary, build_files, CommentarySource, FTS_TABLE};

    #[test]
    fn study_pack_keeps_files_under_their_paths() {
        let dir = std::env::temp_dir().join(format!("pb-study-{}", std::process::id()));
        std::fs::create_dir_all(dir.join("person")).unwrap();
        std::fs::create_dir_all(dir.join("other")).unwrap();
        std::fs::write(dir.join("person").join("aaron.json"), r#"{"id":"aaron"}"#).unwrap();
        std::fs::write(dir.join("people.json"), "[]").unwrap();
        std::fs::write(dir.join("other").join("x.json"), "{}").unwrap();
        let (rows, raw) = build_files(&dir, &["person/", "people.json"]).unwrap();
        assert_eq!(rows, 2);
        let db = dir.join("pack.sqlite");
        std::fs::write(&db, &raw).unwrap();
        let conn = rusqlite::Connection::open(&db).unwrap();
        let body: String = conn
            .query_row(
                "SELECT body FROM file WHERE path = 'person/aaron.json'",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(body, r#"{"id":"aaron"}"#);
        let n: i64 = conn
            .query_row("SELECT count(*) FROM file", [], |r| r.get(0))
            .unwrap();
        assert_eq!(n, 2);
        drop(conn);
        let _ = std::fs::remove_dir_all(&dir);
    }
    use std::collections::BTreeMap;

    #[test]
    fn commentary_pack_keeps_published_chapters() {
        let dir = std::env::temp_dir().join(format!("pb-commentary-{}", std::process::id()));
        let jhn = dir.join("henry").join("JHN");
        std::fs::create_dir_all(&jhn).unwrap();
        std::fs::write(jhn.join("intro.json"), r#"{"units":[]}"#).unwrap();
        std::fs::write(
            jhn.join("3.json"),
            r#"{"source":"henry","book":"JHN","chapter":3}"#,
        )
        .unwrap();
        let src: CommentarySource =
            serde_json::from_str(r#"{"id":"henry","name":"Matthew Henry","short":"M. Henry"}"#)
                .unwrap();
        let chapters = BTreeMap::from([("JHN".to_string(), vec![0, 3])]);
        let (rows, raw) = build_commentary(&dir, &src, &chapters).unwrap();
        assert_eq!(rows, 2);
        let db = dir.join("pack.sqlite");
        std::fs::write(&db, &raw).unwrap();
        let conn = rusqlite::Connection::open(&db).unwrap();
        let body: String = conn
            .query_row(
                "SELECT body FROM chapter WHERE book = 'JHN' AND chapter = 3",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(body, r#"{"source":"henry","book":"JHN","chapter":3}"#);
        let intro: String = conn
            .query_row(
                "SELECT body FROM chapter WHERE book = 'JHN' AND chapter = 0",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(intro, r#"{"units":[]}"#);
        drop(conn);
        // Deterministic: the same files give the same bytes.
        assert_eq!(build_commentary(&dir, &src, &chapters).unwrap().1, raw);
        let _ = std::fs::remove_dir_all(&dir);
    }

    fn hits(texts: &[&str], query: &str) -> Vec<i64> {
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        conn.execute_batch(FTS_TABLE).unwrap();
        for (i, t) in texts.iter().enumerate() {
            conn.execute(
                "INSERT INTO verse_fts(rowid, norm) VALUES (?1, ?2)",
                rusqlite::params![i as i64, tamil_norm::normalize(t)],
            )
            .unwrap();
        }
        let q = format!("\"{}\"*", tamil_norm::normalize(query));
        let mut st = conn
            .prepare("SELECT rowid FROM verse_fts WHERE verse_fts MATCH ?1 ORDER BY rowid")
            .unwrap();
        st.query_map([q], |r| r.get(0))
            .unwrap()
            .map(Result::unwrap)
            .collect()
    }

    #[test]
    fn tamil_words_are_indexed_whole() {
        let texts = [
            "அன்பு நீடிய சாந்தமும்",
            "அன்புக்குப் பொறாமை இல்லை",
            "என்னை அனுப்பு",
            "அன்பைக் காட்டு",
        ];
        // A prefix of the whole normalised word: அன்பு and அன்புக்குப், not அன்பை (stem அன்ப).
        assert_eq!(hits(&texts, "அன்பு"), vec![0, 1]);
        // Not a fragment match on அன + ப.
        assert!(!hits(&texts, "அன்பு").contains(&2));
        assert_eq!(hits(&texts, "அனுப்பு"), vec![2]);
    }
}
