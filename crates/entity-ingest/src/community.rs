//! Community review inputs (feature_dictionary.md §5–6): Tamil drafts produced
//! outside the repository under `data/entities/drafts/ta/`, and accepted
//! corrections exported from Postgres under `data/entities/overrides/`.
//! Overrides win over drafts; both are applied over the English source and
//! never replace it.

use anyhow::{Context, Result};
use serde::Deserialize;
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

use crate::articles::Article;
use crate::names::{NameForm, NamesTa};

// ---- drafts ----

#[derive(Debug, Deserialize)]
pub struct Draft {
    pub id: String,
    /// `hash` of the English article as listed in `articles/index.json`
    #[serde(default)]
    pub source_hash: String,
    #[serde(default)]
    pub title: Option<String>,
    pub paragraphs: Vec<DraftParagraph>,
    /// Read from `drafts/ta-sa/`: a translation of a ShareAlike source.
    #[serde(skip)]
    pub sharealike: bool,
}

#[derive(Debug, Deserialize)]
pub struct DraftParagraph {
    pub id: String,
    pub text: String,
}

/// `drafts/ta/{source}/{slug}.json` and `drafts/ta-sa/{source}/{slug}.json`
/// → draft by article id. Missing dirs → empty. The same article in both
/// folders is an error.
pub fn load_drafts(drafts: &Path) -> Result<BTreeMap<String, Draft>> {
    let mut out = BTreeMap::new();
    for (sub, sharealike) in [("ta", false), ("ta-sa", true)] {
        let dir = drafts.join(sub);
        if !dir.is_dir() {
            continue;
        }
        for source in sorted_dirs(&dir)? {
            for file in sorted_files(&source, "json")? {
                let text = fs::read_to_string(&file)
                    .with_context(|| format!("reading {}", file.display()))?;
                let mut d: Draft = serde_json::from_str(&text)
                    .with_context(|| format!("parsing {}", file.display()))?;
                d.sharealike = sharealike;
                if out.contains_key(&d.id) {
                    anyhow::bail!("draft {} is under both drafts/ta and drafts/ta-sa", d.id);
                }
                out.insert(d.id.clone(), d);
            }
        }
    }
    Ok(out)
}

// ---- overrides ----

#[derive(Debug, Deserialize)]
pub struct NameOverride {
    /// Accepted forms; the first is the label.
    pub forms: Vec<String>,
    #[serde(default)]
    #[allow(dead_code)]
    pub accepted_at: Option<toml::Value>,
    /// Owner-authored rather than community-corrected.
    #[serde(default)]
    pub owner: bool,
}

#[derive(Debug, Deserialize, Default)]
pub struct ArticleOverride {
    #[serde(default)]
    pub title: Option<String>,
    #[serde(default)]
    pub paragraphs: Vec<ParagraphOverride>,
}

#[derive(Debug, Deserialize)]
pub struct ParagraphOverride {
    pub id: String,
    pub text: String,
    #[serde(default)]
    #[allow(dead_code)]
    pub accepted_at: Option<toml::Value>,
    #[serde(default)]
    pub owner: bool,
}

/// An accepted Tamil gloss for a Strong's number (concordance C5).
#[derive(Debug, Deserialize)]
pub struct GlossOverride {
    pub ta: String,
    #[allow(dead_code)]
    pub accepted_at: Option<toml::Value>,
    #[serde(default)]
    pub owner: bool,
}

#[derive(Debug, Default)]
pub struct Overrides {
    /// name_en → override (`overrides/names.toml`)
    pub names: BTreeMap<String, NameOverride>,
    /// article id → override (`overrides/articles/{source}/{slug}.toml`)
    pub articles: BTreeMap<String, ArticleOverride>,
    /// Strong's number → Tamil gloss (`overrides/lexicon.toml`)
    pub lexicon: BTreeMap<String, GlossOverride>,
}

/// Tamil gloss drafts made outside the repository, one line per number:
/// `H0430G = "தேவன்"` in `drafts/lexicon-ta.toml`. Missing file, no drafts.
pub fn load_gloss_drafts(path: &Path) -> Result<BTreeMap<String, String>> {
    if !path.exists() {
        return Ok(BTreeMap::new());
    }
    let text = fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    toml::from_str(&text).with_context(|| format!("parsing {}", path.display()))
}

pub fn load_overrides(dir: &Path) -> Result<Overrides> {
    let mut ov = Overrides::default();
    let names_path = dir.join("names.toml");
    if names_path.exists() {
        let text = fs::read_to_string(&names_path)
            .with_context(|| format!("reading {}", names_path.display()))?;
        ov.names =
            toml::from_str(&text).with_context(|| format!("parsing {}", names_path.display()))?;
    }
    let lexicon_path = dir.join("lexicon.toml");
    if lexicon_path.exists() {
        let text = fs::read_to_string(&lexicon_path)
            .with_context(|| format!("reading {}", lexicon_path.display()))?;
        ov.lexicon =
            toml::from_str(&text).with_context(|| format!("parsing {}", lexicon_path.display()))?;
    }
    let articles_dir = dir.join("articles");
    if articles_dir.is_dir() {
        for source in sorted_dirs(&articles_dir)? {
            let source_name = source
                .file_name()
                .and_then(|s| s.to_str())
                .unwrap_or_default()
                .to_string();
            for file in sorted_files(&source, "toml")? {
                let slug = file
                    .file_stem()
                    .and_then(|s| s.to_str())
                    .unwrap_or_default()
                    .to_string();
                let text = fs::read_to_string(&file)
                    .with_context(|| format!("reading {}", file.display()))?;
                let a: ArticleOverride =
                    toml::from_str(&text).with_context(|| format!("parsing {}", file.display()))?;
                ov.articles.insert(format!("{source_name}/{slug}"), a);
            }
        }
    }
    Ok(ov)
}

/// Apply accepted name corrections. Community forms are human-verified, so
/// they are not subject to the corpus check that guards machine drafts.
/// Returns the number of (name, version) entries changed.
pub fn apply_names(names: &mut NamesTa, ov: &Overrides) -> usize {
    let mut n = 0;
    for (name, o) in &ov.names {
        let Some(label) = o.forms.first().filter(|f| has_tamil(f)) else {
            continue;
        };
        let entry = names.entry(name.clone()).or_insert_with(|| NameForm {
            label: label.clone(),
            forms: Vec::new(),
            confidence: 1.0,
            n: 0,
            review: false,
            community: false,
            owner: false,
            borrowed: false,
        });
        let mut forms = o.forms.clone();
        for f in &entry.forms {
            if !forms.contains(f) {
                forms.push(f.clone());
            }
        }
        entry.label = label.clone();
        entry.forms = forms;
        entry.review = false;
        entry.community = true;
        entry.borrowed = false;
        entry.owner = o.owner;
        n += 1;
    }
    n
}

#[derive(Debug, Default)]
pub struct ArticleReport {
    pub drafts: usize,
    pub stale_drafts: usize,
    pub draft_paragraphs: usize,
    pub invalid: Vec<String>,
    pub unmatched: Vec<String>,
    pub glossary_misses: Vec<String>,
    pub overridden: usize,
    pub orphans: Vec<String>,
}

/// Attach Tamil text to article paragraphs: drafts first, overrides on top.
/// `label_of(title)` gives the accepted Tamil label of the article's subject
/// for the glossary check (a draft that never uses it is reported).
pub fn apply_articles(
    articles: &mut [Article],
    drafts: &BTreeMap<String, Draft>,
    ov: &Overrides,
    label_of: &dyn Fn(&str) -> Option<String>,
) -> ArticleReport {
    let mut r = ArticleReport::default();
    for a in articles.iter_mut() {
        // ShareAlike translations stay apart from CC BY ones (§2).
        let draft = drafts.get(&a.id).filter(|d| {
            let ok = d.sharealike == is_sharealike(a.licence);
            if !ok {
                let want = if is_sharealike(a.licence) {
                    "ta-sa"
                } else {
                    "ta"
                };
                r.invalid.push(format!(
                    "{}: draft of a {} article belongs under drafts/{want}",
                    a.id, a.licence
                ));
            }
            ok
        });
        if let Some(d) = draft {
            r.drafts += 1;
            let h = d.source_hash.trim_start_matches("fnv8:");
            if !h.is_empty() && h != a.hash {
                // Paragraph ids carry the English hash, so unchanged
                // paragraphs still match below; changed ones fall back.
                r.stale_drafts += 1;
            }
            let mut used_any = false;
            for dp in &d.paragraphs {
                let Some(p) = a.paragraphs.iter_mut().find(|p| p.id == dp.id) else {
                    r.unmatched.push(dp.id.clone());
                    continue;
                };
                if let Err(why) = check_text(&dp.text) {
                    r.invalid.push(format!("{}: {why}", dp.id));
                    continue;
                }
                p.ta = Some(dp.text.trim().to_string());
                p.ta_source = Some("draft");
                r.draft_paragraphs += 1;
                used_any = true;
            }
            if let Some(t) = d.title.as_deref().filter(|t| check_text(t).is_ok()) {
                a.title_ta = Some(t.trim().to_string());
            }
            if used_any {
                if let Some(label) = label_of(&a.title) {
                    let stem: String = label.chars().take(4).collect();
                    let mentions = a
                        .paragraphs
                        .iter()
                        .filter_map(|p| p.ta.as_deref())
                        .any(|t| t.contains(stem.as_str()));
                    if !mentions {
                        r.glossary_misses
                            .push(format!("{} (expects {label})", a.id));
                    }
                }
            }
        }
        if let Some(o) = ov.articles.get(&a.id) {
            for po in &o.paragraphs {
                let Some(p) = a.paragraphs.iter_mut().find(|p| p.id == po.id) else {
                    r.orphans.push(po.id.clone());
                    continue;
                };
                if let Err(why) = check_text(&po.text) {
                    r.invalid.push(format!("{}: {why}", po.id));
                    continue;
                }
                p.ta = Some(po.text.trim().to_string());
                p.ta_source = Some(if po.owner { "owner" } else { "community" });
                r.overridden += 1;
            }
            if let Some(t) = o.title.as_deref().filter(|t| check_text(t).is_ok()) {
                a.title_ta = Some(t.trim().to_string());
            }
        }
    }
    r
}

fn is_sharealike(licence: &str) -> bool {
    licence.contains("SA")
}

pub fn has_tamil(s: &str) -> bool {
    s.chars().any(|c| ('\u{0B80}'..='\u{0BFF}').contains(&c))
}

/// Tamil script present, no markup, sane length.
pub fn check_text(s: &str) -> Result<(), &'static str> {
    let t = s.trim();
    if t.is_empty() {
        return Err("empty");
    }
    if t.chars().count() > 4000 {
        return Err("longer than 4000 characters");
    }
    if !has_tamil(t) {
        return Err("no Tamil script");
    }
    let mut it = t.chars().peekable();
    while let Some(c) = it.next() {
        if c == '<' && it.peek().is_some_and(|n| n.is_alphabetic() || *n == '/') {
            return Err("contains HTML");
        }
    }
    Ok(())
}

fn sorted_dirs(dir: &Path) -> Result<Vec<std::path::PathBuf>> {
    let mut v: Vec<_> = fs::read_dir(dir)
        .with_context(|| format!("listing {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.is_dir())
        .collect();
    v.sort();
    Ok(v)
}

fn sorted_files(dir: &Path, ext: &str) -> Result<Vec<std::path::PathBuf>> {
    let mut v: Vec<_> = fs::read_dir(dir)
        .with_context(|| format!("listing {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.is_file() && p.extension().and_then(|e| e.to_str()) == Some(ext))
        .collect();
    v.sort();
    Ok(v)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn text_rules() {
        assert!(check_text("தமஸ்கு").is_ok());
        assert_eq!(check_text("Damascus"), Err("no Tamil script"));
        assert_eq!(check_text("தமஸ்கு <b>x</b>"), Err("contains HTML"));
        assert!(check_text("தமஸ்கு < 3").is_ok());
        assert_eq!(check_text("  "), Err("empty"));
    }

    fn article(id: &str, licence: &'static str) -> Article {
        Article {
            source: id.split('/').next().unwrap().into(),
            id: id.into(),
            slug: id.split('/').nth(1).unwrap().into(),
            title: "Abagtha".into(),
            title_ta: None,
            lang: "en",
            licence,
            attribution: "",
            entities: vec![],
            hints: vec![],
            paragraphs: vec![crate::articles::Paragraph {
                id: format!("{id}#p1-f448c73f"),
                text: "One of the seven eunuchs".into(),
                heading: false,
                ta: None,
                ta_source: None,
            }],
            refs: vec![],
            hash: "f448c73f".into(),
            also_in: vec![],
        }
    }

    fn draft(id: &str, sharealike: bool) -> Draft {
        Draft {
            id: id.into(),
            source_hash: "f448c73f".into(),
            title: Some("அபக்தா".into()),
            paragraphs: vec![DraftParagraph {
                id: format!("{id}#p1-f448c73f"),
                text: "ஏழு அண்ணகர்களில் ஒருவன்".into(),
            }],
            sharealike,
        }
    }

    #[test]
    fn drafts_stay_in_their_licence_folder() {
        let mut arts = vec![
            article("aquifer/abagtha", "CC BY-SA 4.0"),
            article("eastons/abagtha", "PD"),
        ];
        let drafts: BTreeMap<_, _> = [
            (
                "aquifer/abagtha".to_string(),
                draft("aquifer/abagtha", true),
            ),
            (
                "eastons/abagtha".to_string(),
                draft("eastons/abagtha", true),
            ),
        ]
        .into_iter()
        .collect();
        let r = apply_articles(&mut arts, &drafts, &Overrides::default(), &|_| None);
        assert_eq!(r.drafts, 1);
        assert!(arts[0].paragraphs[0].ta.is_some());
        assert!(arts[1].paragraphs[0].ta.is_none());
        assert_eq!(r.invalid.len(), 1);
        assert!(r.invalid[0].contains("belongs under drafts/ta"));
    }

    #[test]
    fn lexicon_overrides_parse() {
        let t = "[G0026]
ta = \"அன்பு\"
accepted_at = \"2026-09-20T10:00:00Z\"

[H1121a]
ta = \"மகன்\"
owner = true
";
        let lex: BTreeMap<String, GlossOverride> = toml::from_str(t).unwrap();
        assert_eq!(lex["G0026"].ta, "அன்பு");
        assert!(!lex["G0026"].owner && lex["H1121a"].owner);
    }

    #[test]
    fn name_override_leads_with_label_and_keeps_forms() {
        let mut names = NamesTa::new();
        names.insert(
            "Damascus".into(),
            NameForm {
                label: "தமஸ்குவை".into(),
                forms: vec!["தமஸ்குவை".into(), "தமஸ்குவின்".into()],
                confidence: 0.5,
                n: 10,
                review: true,
                community: false,
                owner: false,
                borrowed: false,
            },
        );
        let toml_text = "[Damascus]\nforms = [\"தமஸ்கு\"]\naccepted_at = \"2026-10-03T14:12:00Z\"\n";
        let ov = Overrides {
            names: toml::from_str(toml_text).unwrap(),
            articles: BTreeMap::new(),
            lexicon: BTreeMap::new(),
        };
        assert_eq!(apply_names(&mut names, &ov), 1);
        let f = &names["Damascus"];
        assert_eq!(f.label, "தமஸ்கு");
        assert_eq!(f.forms, vec!["தமஸ்கு", "தமஸ்குவை", "தமஸ்குவின்"]);
        assert!(!f.review && f.community);
    }
}
