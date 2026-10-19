//! Parsing a command line into lists, pipelines and simple commands.
//!
//! Quoting is tracked per piece of a word rather than stripped away, because
//! it decides what expansion may do later: nothing inside single quotes,
//! variables but no globs inside double quotes, everything unquoted. Every
//! operator (`;`, `&&`, `|`, `>`, ...) is recognized only outside quotes, so
//! `echo "a;b"` is one command.

use std::fmt;

/// How a piece of a word was quoted.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Quote {
    None,
    Single,
    Double,
}

/// A contiguous piece of a word with one quoting style: `a"b c"'d'` is three.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Part {
    pub text: String,
    pub quote: Quote,
}

/// One shell word, before expansion.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Word {
    pub parts: Vec<Part>,
}

impl Word {
    /// A word made of one unquoted piece.
    pub fn plain(text: &str) -> Self {
        Self {
            parts: vec![Part {
                text: text.to_string(),
                quote: Quote::None,
            }],
        }
    }

    fn push(&mut self, c: char, quote: Quote) {
        match self.parts.last_mut() {
            Some(part) if part.quote == quote => part.text.push(c),
            _ => self.parts.push(Part {
                text: c.to_string(),
                quote,
            }),
        }
    }

    /// The word's text with quoting removed and nothing expanded.
    pub fn literal(&self) -> String {
        self.parts.iter().map(|p| p.text.as_str()).collect()
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RedirectKind {
    /// `< file`
    In,
    /// `> file`
    Out,
    /// `>> file`
    Append,
    /// `2> file`
    ErrOut,
    /// `2>> file`
    ErrAppend,
    /// `2>&1`
    ErrToOut,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Redirect {
    pub kind: RedirectKind,
    /// The file; `None` only for `2>&1`.
    pub target: Option<Word>,
}

/// `NAME=value ... program args... redirects...`
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct SimpleCommand {
    pub assignments: Vec<(String, Word)>,
    pub words: Vec<Word>,
    pub redirects: Vec<Redirect>,
}

/// Commands joined by `|`.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Pipeline {
    pub commands: Vec<SimpleCommand>,
}

/// What comes after a pipeline in a list.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Connector {
    /// `;` or the end of the line
    Sequence,
    /// `&&`: run the next pipeline only if this one succeeded
    And,
    /// `||`: run the next pipeline only if this one failed
    Or,
    /// `&`: run this pipeline in the background
    Background,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ListItem {
    pub pipeline: Pipeline,
    pub connector: Connector,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParseError(pub String);

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "syntax error: {}", self.0)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum Token {
    Word(Word),
    Pipe,
    And,
    Or,
    Semicolon,
    Ampersand,
    Redirect(RedirectKind),
}

/// Parse one line of input. An empty line or a comment is an empty list.
pub fn parse(input: &str) -> Result<Vec<ListItem>, ParseError> {
    let tokens = tokenize(input)?;
    let mut items = Vec::new();
    let mut pipeline = Pipeline::default();
    let mut command = SimpleCommand::default();
    let mut tokens = tokens.into_iter().peekable();

    while let Some(token) = tokens.next() {
        match token {
            Token::Word(word) => match assignment(&word) {
                Some(assign) if command.words.is_empty() => command.assignments.push(assign),
                _ => command.words.push(word),
            },
            Token::Redirect(kind) => {
                let target = if kind == RedirectKind::ErrToOut {
                    None
                } else {
                    match tokens.next() {
                        Some(Token::Word(word)) => Some(word),
                        _ => return Err(ParseError("missing file name after redirection".into())),
                    }
                };
                command.redirects.push(Redirect { kind, target });
            }
            Token::Pipe => {
                if is_empty(&command) {
                    return Err(ParseError("missing command before `|`".into()));
                }
                pipeline.commands.push(std::mem::take(&mut command));
                if tokens.peek().is_none() {
                    return Err(ParseError("missing command after `|`".into()));
                }
            }
            Token::And | Token::Or | Token::Semicolon | Token::Ampersand => {
                let connector = match token {
                    Token::And => Connector::And,
                    Token::Or => Connector::Or,
                    Token::Ampersand => Connector::Background,
                    _ => Connector::Sequence,
                };
                if is_empty(&command) {
                    // A lone `;` or `&` after nothing is fine for `;` only.
                    if connector == Connector::Sequence && pipeline.commands.is_empty() {
                        continue;
                    }
                    return Err(ParseError("missing command".into()));
                }
                pipeline.commands.push(std::mem::take(&mut command));
                items.push(ListItem {
                    pipeline: std::mem::take(&mut pipeline),
                    connector,
                });
                if matches!(connector, Connector::And | Connector::Or) && tokens.peek().is_none() {
                    return Err(ParseError("missing command after `&&` or `||`".into()));
                }
            }
        }
    }

    if !is_empty(&command) {
        pipeline.commands.push(command);
        items.push(ListItem {
            pipeline,
            connector: Connector::Sequence,
        });
    }
    Ok(items)
}

fn is_empty(command: &SimpleCommand) -> bool {
    command.words.is_empty() && command.assignments.is_empty() && command.redirects.is_empty()
}

/// `NAME=value`, with an unquoted, valid NAME.
fn assignment(word: &Word) -> Option<(String, Word)> {
    let first = word.parts.first()?;
    if first.quote != Quote::None {
        return None;
    }
    let (name, rest) = first.text.split_once('=')?;
    let mut chars = name.chars();
    let valid = chars
        .next()
        .is_some_and(|c| c.is_ascii_alphabetic() || c == '_')
        && chars.all(|c| c.is_ascii_alphanumeric() || c == '_');
    if !valid {
        return None;
    }
    let mut value = Word::default();
    if !rest.is_empty() {
        value.parts.push(Part {
            text: rest.to_string(),
            quote: Quote::None,
        });
    }
    value.parts.extend(word.parts[1..].iter().cloned());
    Some((name.to_string(), value))
}

fn tokenize(input: &str) -> Result<Vec<Token>, ParseError> {
    let mut tokens = Vec::new();
    let mut word: Option<Word> = None;
    let mut chars = input.chars().peekable();

    fn finish(word: &mut Option<Word>, tokens: &mut Vec<Token>) {
        if let Some(w) = word.take() {
            tokens.push(Token::Word(w));
        }
    }

    while let Some(c) = chars.next() {
        match c {
            '\'' => {
                let w = word.get_or_insert_with(Word::default);
                let mut closed = false;
                for c in chars.by_ref() {
                    if c == '\'' {
                        closed = true;
                        break;
                    }
                    w.push(c, Quote::Single);
                }
                if !closed {
                    return Err(ParseError("unterminated single quote".into()));
                }
                // `''` is still a (empty) word.
                if w.parts.is_empty() {
                    w.parts.push(Part {
                        text: String::new(),
                        quote: Quote::Single,
                    });
                }
            }
            '"' => {
                let w = word.get_or_insert_with(Word::default);
                let mut closed = false;
                let mut empty = true;
                while let Some(c) = chars.next() {
                    match c {
                        '"' => {
                            closed = true;
                            break;
                        }
                        '\\' if matches!(chars.peek(), Some('"' | '\\' | '$' | '`')) => {
                            // Escaped: literal, and never expanded.
                            w.push(chars.next().unwrap(), Quote::Single);
                        }
                        _ => w.push(c, Quote::Double),
                    }
                    empty = false;
                }
                if !closed {
                    return Err(ParseError("unterminated double quote".into()));
                }
                if empty {
                    w.parts.push(Part {
                        text: String::new(),
                        quote: Quote::Double,
                    });
                }
            }
            '\\' => match chars.next() {
                Some(escaped) => word
                    .get_or_insert_with(Word::default)
                    .push(escaped, Quote::Single),
                None => return Err(ParseError("trailing backslash".into())),
            },
            '#' if word.is_none() => break,
            c if c.is_whitespace() => finish(&mut word, &mut tokens),
            '|' | '&' | ';' | '<' | '>' => {
                // `2>`, `2>>`, `2>&1`: a bare unquoted "2" right before `>`.
                let fd2 = c == '>'
                    && word.as_ref().is_some_and(|w| {
                        w.parts.len() == 1
                            && w.parts[0]
                                == Part {
                                    text: "2".into(),
                                    quote: Quote::None,
                                }
                    });
                if fd2 {
                    word = None;
                } else {
                    finish(&mut word, &mut tokens);
                }
                let token = match c {
                    '|' if chars.peek() == Some(&'|') => {
                        chars.next();
                        Token::Or
                    }
                    '|' => Token::Pipe,
                    '&' if chars.peek() == Some(&'&') => {
                        chars.next();
                        Token::And
                    }
                    '&' => Token::Ampersand,
                    ';' => Token::Semicolon,
                    '<' => Token::Redirect(RedirectKind::In),
                    _ => {
                        let append = chars.peek() == Some(&'>');
                        if append {
                            chars.next();
                        }
                        if fd2 && !append && chars.peek() == Some(&'&') {
                            chars.next();
                            match chars.next() {
                                Some('1') => Token::Redirect(RedirectKind::ErrToOut),
                                _ => return Err(ParseError("only `2>&1` is supported".into())),
                            }
                        } else {
                            match (fd2, append) {
                                (false, false) => Token::Redirect(RedirectKind::Out),
                                (false, true) => Token::Redirect(RedirectKind::Append),
                                (true, false) => Token::Redirect(RedirectKind::ErrOut),
                                (true, true) => Token::Redirect(RedirectKind::ErrAppend),
                            }
                        }
                    }
                };
                tokens.push(token);
            }
            c => word.get_or_insert_with(Word::default).push(c, Quote::None),
        }
    }
    finish(&mut word, &mut tokens);
    Ok(tokens)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn words(command: &SimpleCommand) -> Vec<String> {
        command.words.iter().map(Word::literal).collect()
    }

    fn single(input: &str) -> SimpleCommand {
        let items = parse(input).unwrap();
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].pipeline.commands.len(), 1);
        items[0].pipeline.commands[0].clone()
    }

    #[test]
    fn words_and_quotes() {
        assert_eq!(words(&single("echo hello")), ["echo", "hello"]);
        assert_eq!(
            words(&single("echo \"hello world\" 'a b'")),
            ["echo", "hello world", "a b"]
        );
        assert_eq!(words(&single("echo a\"b c\"d")), ["echo", "ab cd"]);
        assert_eq!(words(&single("echo '' \"\"")), ["echo", "", ""]);
        assert_eq!(words(&single("echo a\\ b")), ["echo", "a b"]);
    }

    #[test]
    fn quoting_is_remembered_per_part() {
        let command = single("echo $A'$B'\"$C\"");
        assert_eq!(
            command.words[1].parts,
            vec![
                Part {
                    text: "$A".into(),
                    quote: Quote::None
                },
                Part {
                    text: "$B".into(),
                    quote: Quote::Single
                },
                Part {
                    text: "$C".into(),
                    quote: Quote::Double
                },
            ]
        );
    }

    #[test]
    fn operators_inside_quotes_are_just_text() {
        assert_eq!(
            words(&single("echo 'a;b' \"c&&d|e>f\"")),
            ["echo", "a;b", "c&&d|e>f"]
        );
    }

    #[test]
    fn lists_and_connectors() {
        let items = parse("a && b || c; d & e").unwrap();
        let connectors: Vec<_> = items.iter().map(|i| i.connector).collect();
        assert_eq!(
            connectors,
            [
                Connector::And,
                Connector::Or,
                Connector::Sequence,
                Connector::Background,
                Connector::Sequence
            ]
        );
    }

    #[test]
    fn pipelines_keep_each_commands_quoting() {
        let items = parse("printf 'x y' | grep \"x y\" | wc -l").unwrap();
        let commands = &items[0].pipeline.commands;
        assert_eq!(commands.len(), 3);
        assert_eq!(words(&commands[1]), ["grep", "x y"]);
    }

    #[test]
    fn redirections() {
        let command = single("cmd < in > out 2> err");
        let kinds: Vec<_> = command.redirects.iter().map(|r| r.kind).collect();
        assert_eq!(
            kinds,
            [RedirectKind::In, RedirectKind::Out, RedirectKind::ErrOut]
        );
        assert_eq!(words(&command), ["cmd"]);

        let command = single("cmd >> log 2>&1");
        assert_eq!(command.redirects[0].kind, RedirectKind::Append);
        assert_eq!(
            command.redirects[1],
            Redirect {
                kind: RedirectKind::ErrToOut,
                target: None
            }
        );

        // "2" is only a file descriptor when bare and right before `>`.
        assert_eq!(words(&single("echo 2 >x")), ["echo", "2"]);
        assert_eq!(words(&single("echo a2>x")), ["echo", "a2"]);
    }

    #[test]
    fn leading_assignments() {
        let command = single("A=1 B='two words' env X=3");
        assert_eq!(command.assignments.len(), 2);
        assert_eq!(command.assignments[1].0, "B");
        assert_eq!(command.assignments[1].1.literal(), "two words");
        assert_eq!(words(&command), ["env", "X=3"]);

        assert!(single("1A=x cmd").assignments.is_empty());
        assert!(single("'A'=x cmd").assignments.is_empty());
    }

    #[test]
    fn comments_and_blank_lines() {
        assert!(parse("").unwrap().is_empty());
        assert!(parse("   ").unwrap().is_empty());
        assert!(parse("# comment").unwrap().is_empty());
        assert_eq!(words(&single("echo a#b # comment")), ["echo", "a#b"]);
    }

    #[test]
    fn syntax_errors() {
        for input in [
            "| wc",
            "echo |",
            "echo 'open",
            "echo \"open",
            "cat <",
            "true &&",
            "; ;&",
        ] {
            assert!(parse(input).is_err(), "{input}");
        }
        assert!(parse("echo a;").is_ok());
    }
}
