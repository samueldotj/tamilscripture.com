//! Syllables of the 1650 Scottish Psalter's lines, for writing the words under the
//! notes (docs/feature_psalms_explorer.md §9). The counting follows
//! scripts/import-scottish-psalter.py, so a line splits into as many syllables as that
//! script counts: the psalter marks its elisions with an apostrophe ("heav'n"), so a
//! written "-ed" is sung ("vex-ed"); "-tion" and "-sion" are two ("na-ti-on"); two vowels
//! sung apart are split ("li-on", "qui-et"). Within a word, a lone consonant starts the
//! next syllable and a cluster is split after its first letter, keeping th, sh, ch and
//! wh whole to start a syllable and ck to end one ("shep-herd" splits its ph). It is a heuristic: words a reader would split otherwise are few,
//! and the card only shows them small under the notes.

/// A line's syllables in order: every one but a word's last ends with "-", and a word's
/// punctuation stays on its last syllable. Superscript verse numbers are dropped.
pub fn line(text: &str) -> Vec<String> {
    let clean: String = text.trim().chars().filter(|c| !"⁰¹²³⁴⁵⁶⁷⁸⁹".contains(*c)).collect();
    let mut out = Vec::new();
    for word in clean.split_whitespace() {
        let parts = word_parts(word);
        let n = parts.len();
        for (i, p) in parts.into_iter().enumerate() {
            out.push(if i + 1 < n { format!("{p}-") } else { p });
        }
    }
    out
}

fn is_vowel(c: char) -> bool {
    matches!(c.to_ascii_lowercase(), 'a' | 'e' | 'i' | 'o' | 'u' | 'y')
}

/// Splits one word (with any punctuation) into syllables.
fn word_parts(word: &str) -> Vec<String> {
    let chars: Vec<char> = word.chars().collect();
    let letter = |c: char| c.is_alphabetic() || c == '\'' || c == '’';
    // The letters, without leading and trailing punctuation.
    let start = chars.iter().position(|&c| c.is_alphabetic()).unwrap_or(0);
    let end = chars.iter().rposition(|&c| c.is_alphabetic()).map(|e| e + 1).unwrap_or(chars.len());
    if start >= end {
        return vec![word.to_string()];
    }
    let core: Vec<char> = chars[start..end].to_vec();
    let lower: Vec<char> = core.iter().map(|c| c.to_ascii_lowercase()).collect();
    let bare: String = lower.iter().filter(|c| c.is_alphabetic()).collect();

    // Vowel groups as index ranges into `core` (apostrophes are not vowels).
    let mut groups: Vec<(usize, usize)> = Vec::new();
    let mut i = 0;
    while i < lower.len() {
        let y_as_consonant = lower[i] == 'y' && (i == 0 || (i + 1 < lower.len() && is_vowel(lower[i + 1]) && lower[i + 1] != 'y'));
        if is_vowel(lower[i]) && !y_as_consonant {
            let s = i;
            while i < lower.len() && is_vowel(lower[i]) && !(lower[i] == 'y' && i > s && i + 1 < lower.len() && is_vowel(lower[i + 1])) {
                i += 1;
            }
            groups.push((s, i));
        } else {
            i += 1;
        }
    }
    if groups.is_empty() {
        return vec![word.to_string()];
    }

    // Two vowels sung apart: split the group in two (not -tion, not the u of qu- and gu-).
    let tion = ["tion", "sion", "tions", "sions"].iter().any(|t| bare.ends_with(t));
    let mut split: Vec<(usize, usize)> = Vec::new();
    for &(s, e) in &groups {
        // The u of qu- and gu- is a consonant: "qui-et", "guide".
        let s = if lower[s] == 'u' && e - s > 1 && s > 0 && matches!(lower[s - 1], 'q' | 'g') { s + 1 } else { s };
        let g: String = lower[s..e].iter().collect();
        let after: String = lower[e..].iter().filter(|c| c.is_alphabetic()).collect();
        let quiet_u = g.starts_with('u') && s > 0 && matches!(lower[s - 1], 'q' | 'g');
        let pair = matches!(g.as_str(), "ia" | "io" | "ie" | "ua" | "ue" | "oe" | "ae");
        let at_tion = tion && g == "io" && e + 1 >= lower.len() - 1;
        if pair && !quiet_u && !matches!(after.as_str(), "" | "s" | "e") && !tion {
            split.push((s, s + 1));
            split.push((s + 1, e));
        } else if at_tion {
            split.push((s, s + 1)); // na-ti-on
            split.push((s + 1, e));
        } else {
            split.push((s, e));
        }
    }
    let mut groups = split;

    // A silent final e (also before s): "make", "makes", but not "able" or "graces".
    if groups.len() > 1 {
        // A possessive's "'s" does not count: "name's" ends in a silent e.
        let possessive = lower.len() > 2 && lower[lower.len() - 1] == 's' && matches!(lower[lower.len() - 2], '\'' | '’');
        let n = if possessive { lower.len() - 2 } else { lower.len() };
        let last = groups[groups.len() - 1];
        let ends_e = last.1 == n && last.0 == n - 1 && lower[n - 1] == 'e';
        let ends_es = last.1 == n - 1 && last.0 == n - 2 && lower[n - 2] == 'e' && lower[n - 1] == 's';
        let before = if ends_e { n.checked_sub(2) } else if ends_es { n.checked_sub(3) } else { None };
        if let Some(b) = before {
            let c = lower[b];
            let keeps = (ends_e && c == 'l') || (ends_es && matches!(c, 'c' | 'g' | 's' | 'x' | 'z'));
            if !is_vowel(c) && !keeps {
                groups.pop();
            }
        }
    }
    if groups.len() <= 1 {
        return vec![word.to_string()];
    }

    // Cut points between groups.
    let digraph = |a: char, b: char| matches!((a, b), ('t', 'h') | ('s', 'h') | ('c', 'h') | ('w', 'h') | ('c', 'k'));
    // Verb endings keep the stem's consonant: "lead-eth", "lov-ing", "walk-ed", "seek-est".
    let suffix = ["eth", "est", "ed", "ing"].iter().any(|x| bare.ends_with(x));
    let mut cuts = Vec::new();
    for (wi, w) in groups.windows(2).enumerate() {
        let last_cut = wi + 2 == groups.len();
        let (a_end, b_start) = (w[0].1, w[1].0);
        let cons: Vec<usize> = (a_end..b_start).filter(|&k| letter(core[k]) && lower[k] != '\'' && lower[k] != '’').collect();
        let cut = match cons.len() {
            0 => b_start,
            1 if last_cut && suffix => b_start,
            2 if last_cut && suffix && digraph(lower[cons[0]], lower[cons[1]]) => b_start,
            // A final "-le" takes the consonant before it: "ta-ble", "tem-ple".
            n if n >= 2 && last_cut && (bare.ends_with("le") && cons[n - 1] + 2 == lower.len() || bare.ends_with("les") && cons[n - 1] + 3 == lower.len()) => cons[n - 2],
            1 => cons[0],
            2 if digraph(lower[cons[0]], lower[cons[1]]) => {
                if lower[cons[0]] == 'c' { b_start } else { cons[0] }
            }
            _ => cons[0] + 1,
        };
        cuts.push(cut);
    }
    let mut parts = Vec::new();
    let mut from = 0;
    for &c in &cuts {
        parts.push(core[from..c].iter().collect::<String>());
        from = c;
    }
    parts.push(core[from..].iter().collect::<String>());
    let parts: Vec<String> = parts.into_iter().filter(|p| !p.is_empty()).collect();
    let mut out = parts;
    let lead: String = chars[..start].iter().collect();
    let tail: String = chars[end..].iter().collect();
    out[0] = format!("{lead}{}", out[0]);
    let last = out.len() - 1;
    out[last] = format!("{}{tail}", out[last]);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn s(t: &str) -> String {
        line(t).join(" ")
    }

    #[test]
    fn words() {
        assert_eq!(s("¹The Lord’s my shepherd, I’ll not want."), "The Lord’s my shep- herd, I’ll not want.");
        assert_eq!(s("In pastures green: he leadeth me"), "In pas- tures green: he lead- eth me");
        assert_eq!(s("the quiet waters by."), "the qui- et wa- ters by.");
        assert_eq!(s("and me to walk doth make"), "and me to walk doth make");
        assert_eq!(s("My table thou hast furnished"), "My ta- ble thou hast fur- nish- ed");
        assert_eq!(s("Salvation doth appertain"), "Sal- va- ti- on doth ap- per- tain");
        assert_eq!(s("should, like a lion, tear,"), "should, like a li- on, tear,");
        assert_eq!(s("ev’n for his own name’s sake."), "ev’n for his own name’s sake.");
    }

    #[test]
    fn counts_match_the_metre() {
        assert_eq!(line("¹The Lord’s my shepherd, I’ll not want.").len(), 8);
        assert_eq!(line("  ²He makes me down to lie").len(), 6);
        assert_eq!(line("Within the paths of righteousness,").len(), 8);
    }
}
