//! pack-build — the Android app's content packs (tamilscripture.app design §7).
//!
//! Reads the content build the website already serves (`apps/web/static/content`)
//! and writes, under `--out`:
//!
//! ```text
//! packs/bible.IRVTAM/{n}/bible.IRVTAM.sqlite.zst   one per version
//! packs/xref/{n}/xref.sqlite.zst                   cross-references
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
//!              --pack-version 7 [--key ~/.tamilscripture/catalogue-signing.key]

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
    packs: Vec<CatalogueEntry>,
}

struct Args {
    content: PathBuf,
    out: PathBuf,
    pack_version: u32,
    key: Option<PathBuf>,
    only: Option<Vec<String>>,
}

fn args() -> Result<Args> {
    let mut a = std::env::args().skip(1);
    let (mut content, mut out, mut pack_version, mut key, mut only) = (None, None, None, None, None);
    while let Some(k) = a.next() {
        let v = a.next().with_context(|| format!("{k} needs a value"))?;
        match k.as_str() {
            "--content" => content = Some(PathBuf::from(v)),
            "--out" => out = Some(PathBuf::from(v)),
            "--pack-version" => pack_version = Some(v.parse()?),
            "--key" => key = Some(PathBuf::from(v)),
            "--only" => only = Some(v.split(',').map(|s| s.trim().to_uppercase()).collect()),
            _ => bail!("unknown argument {k}"),
        }
    }
    Ok(Args {
        content: content.context("--content is required")?,
        out: out.context("--out is required")?,
        pack_version: pack_version.unwrap_or(1),
        key,
        only,
    })
}

fn main() -> Result<()> {
    // `pack-build --print-public <keyfile>`: the verifying key the app embeds.
    let raw: Vec<String> = std::env::args().collect();
    if raw.get(1).map(String::as_str) == Some("--print-public") {
        let key = load_key(Path::new(raw.get(2).context("--print-public needs a key file")?))?;
        println!("{}", hex(key.verifying_key().as_bytes()));
        return Ok(());
    }
    let args = args()?;
    let manifest: Manifest = serde_json::from_slice(&fs::read(args.content.join("manifest.json"))?)?;
    let build_dir = args.content.join(&manifest.build);
    let packs_dir = args.out.join("packs");
    fs::create_dir_all(&packs_dir)?;
    let n = args.pack_version;
    let mut entries = Vec::new();

    for v in &manifest.versions {
        if let Some(only) = &args.only {
            if !only.contains(&v.code) {
                continue;
            }
        }
        let id = format!("bible.{}", v.code);
        let rel = format!("packs/{id}/{n}/{id}.sqlite.zst");
        let raw = build_bible(&build_dir, &manifest, v, n)?;
        let e = write_pack(&args.out, &rel, raw)?;
        println!("{id}: {} rows → {} KB", e.0, e.2 / 1024);
        entries.push(CatalogueEntry {
            id,
            kind: "bible".into(),
            lang: v.lang.clone(),
            version: n,
            schema: SCHEMA,
            min_app: 1,
            title: Title {
                ta: v.name_native.clone().unwrap_or_else(|| v.name.clone()),
                en: v.name.clone(),
            },
            licence: v.licence.clone(),
            attribution: v.attribution.clone(),
            path: rel,
            size: e.2,
            raw_size: e.1,
            sha256: e.3,
            raw_sha256: e.4,
            starter: v.default || v.code == "BSB",
            build: manifest.build.clone(),
        });
    }

    if args.only.as_ref().map_or(true, |o| o.iter().any(|c| c == "XREF")) {
        let rel = format!("packs/xref/{n}/xref.sqlite.zst");
        let raw = build_xref(&build_dir, &manifest, n)?;
        let e = write_pack(&args.out, &rel, raw)?;
        println!("xref: {} rows → {} KB", e.0, e.2 / 1024);
        entries.push(CatalogueEntry {
            id: "xref".into(),
            kind: "xref".into(),
            lang: "".into(),
            version: n,
            schema: SCHEMA,
            min_app: 1,
            title: Title { ta: "தொடர்புள்ள வசனங்கள்".into(), en: "Cross-references".into() },
            licence: "CC BY 4.0".into(),
            attribution: "OpenBible.info cross references, CC BY 4.0, merged with the translations' own references".into(),
            path: rel,
            size: e.2,
            raw_size: e.1,
            sha256: e.3,
            raw_sha256: e.4,
            starter: true,
            build: manifest.build.clone(),
        });
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
    write_signed(&packs_dir.join("catalogue.json"), &serde_json::to_vec_pretty(&catalogue)?, key.as_ref())?;
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
    write_signed(&args.out.join("app/bootstrap.json"), &serde_json::to_vec_pretty(&bootstrap)?, key.as_ref())?;
    if key.is_none() {
        eprintln!("note: no --key given, catalogue and bootstrap are unsigned");
    }
    Ok(())
}

/// (rows, raw size, compressed size, sha256 of compressed, sha256 of raw)
fn write_pack(out: &Path, rel: &str, raw: (usize, Vec<u8>)) -> Result<(usize, u64, u64, String, String)> {
    let (rows, bytes) = raw;
    let path = out.join(rel);
    fs::create_dir_all(path.parent().unwrap())?;
    let compressed = zstd::encode_all(&bytes[..], 19)?;
    fs::write(&path, &compressed)?;
    Ok((rows, bytes.len() as u64, compressed.len() as u64, hex(&Sha256::digest(&compressed)), hex(&Sha256::digest(&bytes))))
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
    conn.execute_batch(&format!("PRAGMA page_size = 4096; PRAGMA user_version = {SCHEMA};"))?;
    Ok(conn)
}

fn norm(text: &str) -> String {
    let nfc: String = text.nfc().collect();
    tamil_norm::normalize(&nfc)
}

fn verse_key(order: u32, chapter: u32, verse: u32) -> i64 {
    order as i64 * 1_000_000 + chapter as i64 * 1_000 + verse as i64
}

fn build_bible(build_dir: &Path, m: &Manifest, v: &Version, pack_version: u32) -> Result<(usize, Vec<u8>)> {
    let conn = open()?;
    conn.execute_batch(
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
         CREATE TABLE book (code TEXT PRIMARY KEY, ord INTEGER NOT NULL, testament TEXT NOT NULL,
                            name TEXT NOT NULL, chapters INTEGER NOT NULL);
         CREATE TABLE chapter (book TEXT NOT NULL, chapter INTEGER NOT NULL, body TEXT NOT NULL,
                               PRIMARY KEY (book, chapter)) WITHOUT ROWID;
         CREATE TABLE verse (id INTEGER PRIMARY KEY, book TEXT NOT NULL, chapter INTEGER NOT NULL,
                             verse INTEGER NOT NULL, text TEXT NOT NULL);
         CREATE VIRTUAL TABLE verse_fts USING fts5(norm, content='', contentless_delete=1,
                                                   tokenize='unicode61 remove_diacritics 0');",
    )?;
    let meta = [
        ("pack_id", format!("bible.{}", v.code)),
        ("pack_version", pack_version.to_string()),
        ("schema", SCHEMA.to_string()),
        ("version_code", v.code.clone()),
        ("language", v.lang.clone()),
        ("name_en", v.name.clone()),
        ("name_ta", v.name_native.clone().unwrap_or_default()),
        ("short", v.short.clone().unwrap_or_else(|| v.code.clone())),
        ("licence", v.licence.clone()),
        ("attribution", v.attribution.clone()),
        ("source_url", v.source_url.clone().unwrap_or_default()),
        ("build_id", m.build.clone()),
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
            params![b.code, b.order, b.testament, if v.lang == "ta" { &b.name_ta } else { &b.name_en }, b.chapters],
        )?;
        for ch in 1..=b.chapters {
            let f = dir.join(format!("{ch}.json"));
            let Ok(body) = fs::read_to_string(&f) else { continue };
            tx.execute("INSERT INTO chapter VALUES (?1, ?2, ?3)", params![b.code, ch, body])?;
            let json: Value = serde_json::from_str(&body).with_context(|| f.display().to_string())?;
            // Join a verse's segments (poetry lines, split paragraphs) in order.
            let mut verses: Vec<(u32, String)> = Vec::new();
            for block in json["blocks"].as_array().into_iter().flatten() {
                for seg in block["segments"].as_array().into_iter().flatten() {
                    let Some(id) = seg["id"].as_str() else { continue };
                    let Some(n) = id.split('.').nth(2).and_then(|x| x.split('-').next()).and_then(|x| x.parse::<u32>().ok()) else { continue };
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
                tx.execute("INSERT OR REPLACE INTO verse VALUES (?1, ?2, ?3, ?4, ?5)", params![key, b.code, ch, n, text])?;
                tx.execute("INSERT INTO verse_fts(rowid, norm) VALUES (?1, ?2)", params![key, normed])?;
                rows += 1;
            }
        }
    }
    tx.commit()?;
    conn.execute_batch(
        "INSERT INTO verse_fts(verse_fts) VALUES('optimize');",
    )?;
    Ok((rows, finish(conn)?))
}

fn build_xref(build_dir: &Path, m: &Manifest, pack_version: u32) -> Result<(usize, Vec<u8>)> {
    let conn = open()?;
    conn.execute_batch(
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
         CREATE TABLE xref (from_id TEXT NOT NULL, rank INTEGER NOT NULL, to_id TEXT NOT NULL,
                            to_end TEXT, votes INTEGER NOT NULL, PRIMARY KEY (from_id, rank)) WITHOUT ROWID;",
    )?;
    let tx = conn.unchecked_transaction()?;
    for (k, val) in [("pack_id", "xref".to_string()), ("pack_version", pack_version.to_string()),
                     ("schema", SCHEMA.to_string()), ("build_id", m.build.clone())] {
        tx.execute("INSERT INTO meta VALUES (?1, ?2)", params![k, val])?;
    }
    let mut rows = 0;
    for b in &m.books {
        for ch in 1..=b.chapters {
            let f = build_dir.join("xref").join(&b.code).join(format!("{ch}.json"));
            let Ok(body) = fs::read(&f) else { continue };
            let map: BTreeMap<String, Vec<Value>> = serde_json::from_slice(&body)?;
            for (from, list) in map {
                for (rank, r) in list.iter().enumerate() {
                    tx.execute(
                        "INSERT INTO xref VALUES (?1, ?2, ?3, ?4, ?5)",
                        params![from, rank as i64, r["to"].as_str().unwrap_or(""), r["end"].as_str(), r["votes"].as_i64().unwrap_or(0)],
                    )?;
                    rows += 1;
                }
            }
        }
    }
    tx.commit()?;
    Ok((rows, finish(conn)?))
}
