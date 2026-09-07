//! The book table from `data/books.toml`.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Book {
    pub code: String,
    pub order: u32,
    pub testament: String,
    pub chapters: u32,
    pub slug: String,
    pub slugs: Vec<String>,
    pub name_en: String,
    pub abbr_en: Vec<String>,
    pub name_ta: String,
    pub alias_ta: Vec<String>,
    pub abbr_ta: Vec<String>,
    pub openbible: String,
}

#[derive(Debug, Deserialize)]
struct BooksFile {
    book: Vec<Book>,
}

#[derive(Debug, Clone)]
pub struct Books {
    pub list: Vec<Book>,
    by_code: HashMap<String, usize>,
    by_openbible: HashMap<String, usize>,
}

impl Books {
    pub fn load(path: &Path) -> Result<Books> {
        let text =
            std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
        let file: BooksFile = toml::from_str(&text).context("parsing books.toml")?;
        let mut list = file.book;
        list.sort_by_key(|b| b.order);
        let by_code = list
            .iter()
            .enumerate()
            .map(|(i, b)| (b.code.clone(), i))
            .collect();
        let by_openbible = list
            .iter()
            .enumerate()
            .map(|(i, b)| (b.openbible.clone(), i))
            .collect();
        Ok(Books {
            list,
            by_code,
            by_openbible,
        })
    }

    pub fn by_openbible(&self, abbr: &str) -> Option<&Book> {
        self.by_openbible.get(abbr).map(|&i| &self.list[i])
    }

    pub fn index(&self, code: &str) -> Option<usize> {
        self.by_code.get(code).copied()
    }
}
