//! The 66-book table from `data/books.toml`; only the fields this crate needs.

use anyhow::{Context, Result};
use serde::Deserialize;
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct Book {
    pub code: String,
    pub order: u32,
    pub testament: String,
    pub chapters: u32,
    pub slug: String,
    pub name_en: String,
    pub name_ta: String,
    pub openbible: String,
}

#[derive(Deserialize)]
struct File {
    book: Vec<Book>,
}

pub struct Books {
    pub list: Vec<Book>,
    by_openbible: HashMap<String, usize>,
    by_code: HashMap<String, usize>,
}

impl Books {
    pub fn load(path: &Path) -> Result<Books> {
        let text =
            std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
        let file: File = toml::from_str(&text).context("parsing books.toml")?;
        let mut by_openbible = HashMap::new();
        let mut by_code = HashMap::new();
        for (i, b) in file.book.iter().enumerate() {
            by_openbible.insert(b.openbible.clone(), i);
            by_code.insert(b.code.clone(), i);
        }
        Ok(Books {
            list: file.book,
            by_openbible,
            by_code,
        })
    }

    pub fn by_openbible(&self, abbr: &str) -> Option<&Book> {
        self.by_openbible.get(abbr).map(|&i| &self.list[i])
    }

    pub fn by_code(&self, code: &str) -> Option<&Book> {
        self.by_code.get(code).map(|&i| &self.list[i])
    }
}
