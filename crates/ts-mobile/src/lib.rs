//! Bindings for the Android app (tamilscripture.app design §9).
//!
//! The app must parse references and normalise Tamil exactly as the website
//! does, so it calls these crates instead of re-implementing them. Inputs are
//! NFC-normalised here, which the WebAssembly wrapper leaves to JavaScript.

use unicode_normalization::UnicodeNormalization;

uniffi::setup_scaffolding!();

/// A parsed reference. `verse_end` is set only for a range.
#[derive(Debug, Clone, PartialEq, Eq, uniffi::Record)]
pub struct ParsedReference {
    /// USFM book code, e.g. `JHN`.
    pub book: String,
    pub chapter: u32,
    pub verse: Option<u32>,
    pub verse_end: Option<u32>,
}

fn nfc(s: &str) -> String {
    s.nfc().collect()
}

/// Parses `John 3:16`, `யோவான் 3:16`, `jn3.16`, `சங் ௨௩`… or returns None.
#[uniffi::export]
pub fn parse_reference(input: String) -> Option<ParsedReference> {
    bible_ref::parse(&nfc(&input)).map(|r| ParsedReference {
        book: r.book.code.to_string(),
        chapter: r.chapter,
        verse: r.verse,
        verse_end: r.verse_end,
    })
}

/// Book codes whose names or abbreviations start with `prefix`, best first.
#[uniffi::export]
pub fn suggest_books(prefix: String, limit: u32) -> Vec<String> {
    bible_ref::suggest(&nfc(&prefix), limit as usize)
        .into_iter()
        .map(|b| b.code.to_string())
        .collect()
}

/// Search normalisation, identical to the index built by `pack-build` and to
/// the website's `tamil_norm()` SQL function.
#[uniffi::export]
pub fn normalize(text: String) -> String {
    tamil_norm::normalize(&nfc(&text))
}

#[derive(Debug, uniffi::Error)]
pub enum PackError {
    Io { reason: String },
}

impl std::fmt::Display for PackError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PackError::Io { reason } => f.write_str(reason),
        }
    }
}

impl std::error::Error for PackError {}

impl From<std::io::Error> for PackError {
    fn from(e: std::io::Error) -> Self {
        PackError::Io {
            reason: e.to_string(),
        }
    }
}

/// Decompresses a downloaded `.sqlite.zst` pack to `dest` and returns the
/// SHA-256 (hex) of what it wrote, so the caller can compare it with the
/// catalogue's `rawSha256` before installing (app design §7.7).
#[uniffi::export]
pub fn decompress_pack(source: String, dest: String) -> Result<String, PackError> {
    use sha2::{Digest, Sha256};
    use std::io::{Read, Write};
    let input = std::io::BufReader::new(std::fs::File::open(&source)?);
    let mut decoder = zstd::stream::read::Decoder::new(input)?;
    let mut out = std::io::BufWriter::new(std::fs::File::create(&dest)?);
    let mut hasher = Sha256::new();
    let mut buf = vec![0u8; 1 << 16];
    loop {
        let n = decoder.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
        out.write_all(&buf[..n])?;
    }
    out.flush()?;
    Ok(hasher
        .finalize()
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect())
}

/// Verifies an Ed25519 signature (hex) over `message` with `public_key` (hex),
/// as written by `pack-build --key` for the catalogue and bootstrap files.
#[uniffi::export]
pub fn verify_signature(public_key: String, message: Vec<u8>, signature: String) -> bool {
    fn unhex<const N: usize>(s: &str) -> Option<[u8; N]> {
        let s = s.trim();
        if s.len() != N * 2 {
            return None;
        }
        let mut out = [0u8; N];
        for i in 0..N {
            out[i] = u8::from_str_radix(&s[i * 2..i * 2 + 2], 16).ok()?;
        }
        Some(out)
    }
    let (Some(pk), Some(sig)) = (unhex::<32>(&public_key), unhex::<64>(&signature)) else {
        return false;
    };
    let Ok(key) = ed25519_dalek::VerifyingKey::from_bytes(&pk) else {
        return false;
    };
    key.verify_strict(&message, &ed25519_dalek::Signature::from_bytes(&sig))
        .is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_tamil_and_english() {
        let r = parse_reference("யோவான் 3:16".into()).unwrap();
        assert_eq!((r.book.as_str(), r.chapter, r.verse), ("JHN", 3, Some(16)));
        let r = parse_reference("1co13.4-7".into()).unwrap();
        assert_eq!(
            (r.book.as_str(), r.verse, r.verse_end),
            ("1CO", Some(4), Some(7))
        );
        assert!(parse_reference("அன்பு".into()).is_none());
    }

    #[test]
    fn normalises_like_the_website() {
        // Case suffixes strip to the stem (tamil-norm's own contract).
        assert_eq!(normalize("அன்பை".into()), normalize("அன்பினால்".into()));
        // Input is NFC-normalised first: a decomposed ொ (ெ + ா) equals the precomposed letter.
        assert_eq!(
            normalize("கொ".into()),
            normalize("க\u{0BC6}\u{0BBE}".into())
        );
    }
}
