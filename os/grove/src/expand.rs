//! Expanding words right before a command runs, so `export A=1; echo $A`
//! sees the assignment.
//!
//! - `$NAME`, `${NAME}`, `$?` (last status), `$$` (grove's pid): unquoted and
//!   inside double quotes
//! - `~` / `~/...` at the start of an unquoted word: `$HOME`
//! - `*`, `?`, `[...]` in unquoted text: matching paths, sorted; left as-is
//!   when nothing matches
//!
//! Unlike POSIX shells, an unquoted `$VAR` holding spaces stays one word.

use crate::parser::{Quote, Word};

/// Expand one word into zero or more arguments (a glob can match many).
pub fn expand_word(word: &Word, last_status: i32) -> Vec<String> {
    let mut text = String::new();
    let mut pattern = String::new();
    let mut has_glob = false;

    for (index, part) in word.parts.iter().enumerate() {
        let expanded = match part.quote {
            Quote::Single => part.text.clone(),
            Quote::Double | Quote::None => expand_variables(&part.text, last_status),
        };
        let expanded = if index == 0 && part.quote == Quote::None {
            expand_tilde(&expanded)
        } else {
            expanded
        };

        if part.quote == Quote::None && expanded.contains(['*', '?', '[']) {
            has_glob = true;
            pattern.push_str(&expanded);
        } else {
            pattern.push_str(&glob::Pattern::escape(&expanded));
        }
        text.push_str(&expanded);
    }

    if has_glob {
        let options = glob::MatchOptions {
            require_literal_leading_dot: true,
            ..Default::default()
        };
        if let Ok(paths) = glob::glob_with(&pattern, options) {
            let mut matches: Vec<String> = paths
                .filter_map(Result::ok)
                .map(|path| path.to_string_lossy().into_owned())
                .collect();
            if !matches.is_empty() {
                matches.sort();
                return matches;
            }
        }
    }
    vec![text]
}

/// Expand a word that must stay a single string (redirection targets,
/// assignment values): globs are not applied.
pub fn expand_single(word: &Word, last_status: i32) -> String {
    let mut text = String::new();
    for (index, part) in word.parts.iter().enumerate() {
        let expanded = match part.quote {
            Quote::Single => part.text.clone(),
            Quote::Double | Quote::None => expand_variables(&part.text, last_status),
        };
        if index == 0 && part.quote == Quote::None {
            text.push_str(&expand_tilde(&expanded));
        } else {
            text.push_str(&expanded);
        }
    }
    text
}

fn expand_tilde(text: &str) -> String {
    match text.strip_prefix('~') {
        Some(rest) if rest.is_empty() || rest.starts_with('/') => {
            format!("{}{}", std::env::var("HOME").unwrap_or_default(), rest)
        }
        _ => text.to_string(),
    }
}

fn expand_variables(text: &str, last_status: i32) -> String {
    let mut out = String::new();
    let mut chars = text.chars().peekable();
    while let Some(c) = chars.next() {
        if c != '$' {
            out.push(c);
            continue;
        }
        match chars.peek() {
            Some('?') => {
                chars.next();
                out.push_str(&last_status.to_string());
            }
            Some('$') => {
                chars.next();
                out.push_str(&std::process::id().to_string());
            }
            Some('{') => {
                chars.next();
                let name: String = chars.by_ref().take_while(|c| *c != '}').collect();
                out.push_str(&std::env::var(&name).unwrap_or_default());
            }
            Some(c) if c.is_ascii_alphabetic() || *c == '_' => {
                let mut name = String::new();
                while let Some(&c) = chars.peek() {
                    if c.is_ascii_alphanumeric() || c == '_' {
                        name.push(c);
                        chars.next();
                    } else {
                        break;
                    }
                }
                out.push_str(&std::env::var(&name).unwrap_or_default());
            }
            _ => out.push('$'),
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parser::Part;

    fn word(parts: &[(&str, Quote)]) -> Word {
        Word {
            parts: parts
                .iter()
                .map(|(text, quote)| Part {
                    text: text.to_string(),
                    quote: *quote,
                })
                .collect(),
        }
    }

    #[test]
    fn variables_expand_unquoted_and_in_double_quotes_only() {
        std::env::set_var("GROVE_EXPAND_TEST", "leaf");
        assert_eq!(
            expand_single(
                &word(&[("$GROVE_EXPAND_TEST-${GROVE_EXPAND_TEST}s", Quote::None)]),
                0
            ),
            "leaf-leafs"
        );
        assert_eq!(
            expand_single(&word(&[("$GROVE_EXPAND_TEST", Quote::Double)]), 0),
            "leaf"
        );
        assert_eq!(
            expand_single(&word(&[("$GROVE_EXPAND_TEST", Quote::Single)]), 0),
            "$GROVE_EXPAND_TEST"
        );
        assert_eq!(
            expand_single(&word(&[("$GROVE_UNSET_VARIABLE_XYZ", Quote::None)]), 0),
            ""
        );
    }

    #[test]
    fn special_parameters() {
        assert_eq!(expand_single(&word(&[("$?", Quote::None)]), 127), "127");
        assert_eq!(
            expand_single(&word(&[("cost: $", Quote::None)]), 0),
            "cost: $"
        );
    }

    #[test]
    fn tilde_only_at_the_start_of_an_unquoted_word() {
        let home = std::env::var("HOME").unwrap_or_default();
        assert_eq!(
            expand_single(&word(&[("~/x", Quote::None)]), 0),
            format!("{home}/x")
        );
        assert_eq!(expand_single(&word(&[("~", Quote::Single)]), 0), "~");
        assert_eq!(expand_single(&word(&[("a~", Quote::None)]), 0), "a~");
        assert_eq!(expand_single(&word(&[("~user", Quote::None)]), 0), "~user");
    }

    #[test]
    fn globs_match_sorted_and_stay_literal_without_matches() {
        let dir = tempfile::tempdir().unwrap();
        for name in ["b.txt", "a.txt", ".hidden.txt", "c.log"] {
            std::fs::write(dir.path().join(name), "").unwrap();
        }
        let base = dir.path().display().to_string();

        let matched = expand_word(&word(&[(&format!("{base}/*.txt"), Quote::None)]), 0);
        assert_eq!(matched, [format!("{base}/a.txt"), format!("{base}/b.txt")]);

        let none = expand_word(&word(&[(&format!("{base}/*.none"), Quote::None)]), 0);
        assert_eq!(none, [format!("{base}/*.none")]);
    }

    #[test]
    fn quoted_wildcards_are_literal_even_next_to_unquoted_ones() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("x*y"), "").unwrap();
        std::fs::write(dir.path().join("xzy"), "").unwrap();
        let base = dir.path().display().to_string();

        // "x" + quoted "*" + "y": only the file literally named x*y.
        let expanded = expand_word(
            &word(&[
                (&format!("{base}/x"), Quote::None),
                ("*", Quote::Double),
                ("y", Quote::None),
            ]),
            0,
        );
        assert_eq!(expanded, [format!("{base}/x*y")]);
    }
}
