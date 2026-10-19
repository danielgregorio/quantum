//! The Hive, from the shell: questions (`? ...`), notices at the prompt, and
//! `anon` - over hive-cortex's user socket, which any local user may use.
//!
//! Optional by design: without a Hive to talk to (cortex not running, not
//! DruidOS) grove is just a shell, and only `?` and `anon` say so.

use hive_common::actions::is_valid_package_name;
use hive_common::ipc::blocking::Connection;
use hive_common::messages::{AnonymousLevel, HiveMessage, MessageId};
use std::path::PathBuf;
use std::sync::mpsc::{self, Receiver, RecvTimeoutError};
use std::thread;
use std::time::{Duration, Instant};

/// How long `?` waits for the local model before giving up. Answers take
/// 10-20 s on a small VM, longer when events are being answered first.
const ANSWER_TIMEOUT: Duration = Duration::from_secs(180);

/// Why a question got no answer.
#[derive(Debug, PartialEq, Eq)]
pub enum AskError {
    /// Lost the connection to the Hive
    Disconnected,
    /// No answer within `ANSWER_TIMEOUT`
    TimedOut,
    /// The user pressed Ctrl-C
    Interrupted,
}

/// A connection to the Hive.
pub struct Hive {
    conn: Connection,
    incoming: Receiver<HiveMessage>,
    /// Notices that arrived while waiting for an answer, for the next prompt.
    held_notices: Vec<String>,
}

impl Hive {
    /// Connect to the user socket (`HIVE_USER_SOCKET`, or the default path).
    pub fn connect() -> Option<Self> {
        let path = std::env::var_os("HIVE_USER_SOCKET")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from(hive_common::USER_SOCKET));
        Self::connect_to(&path)
    }

    pub fn connect_to(path: &std::path::Path) -> Option<Self> {
        let conn = Connection::connect(path).ok()?;
        let mut reader = conn.try_clone().ok()?;
        let (tx, incoming) = mpsc::channel();
        // The reader ends when the connection does; the channel then reports
        // Disconnected to whoever is listening.
        thread::spawn(move || {
            while let Ok(msg) = reader.recv() {
                if tx.send(msg).is_err() {
                    break;
                }
            }
        });
        Some(Self {
            conn,
            incoming,
            held_notices: Vec::new(),
        })
    }

    /// Notices received since the last call, as lines to print.
    pub fn take_notices(&mut self) -> Vec<String> {
        let mut notices = std::mem::take(&mut self.held_notices);
        while let Ok(msg) = self.incoming.try_recv() {
            notices.extend(notice_line(&msg));
        }
        notices
    }

    /// Ask the Hive `query` and wait for the answer, one line per point it
    /// makes. `interrupted` is polled while waiting.
    pub fn ask(
        &mut self,
        query: &str,
        cwd: Option<PathBuf>,
        interrupted: impl Fn() -> bool,
    ) -> Result<Vec<String>, AskError> {
        let request_id = MessageId::new_v4();
        self.conn
            .send(&HiveMessage::UserQuery {
                request_id,
                query: query.to_string(),
                cwd,
            })
            .map_err(|_| AskError::Disconnected)?;

        let deadline = Instant::now() + ANSWER_TIMEOUT;
        loop {
            match self.incoming.recv_timeout(Duration::from_millis(200)) {
                Ok(msg) => match answer_lines(&msg, request_id) {
                    Some(lines) => return Ok(lines),
                    None => self.held_notices.extend(notice_line(&msg)),
                },
                Err(RecvTimeoutError::Disconnected) => return Err(AskError::Disconnected),
                Err(RecvTimeoutError::Timeout) => {}
            }
            if interrupted() {
                return Err(AskError::Interrupted);
            }
            if Instant::now() > deadline {
                return Err(AskError::TimedOut);
            }
        }
    }

    /// Tell the Hive a program the user ran is missing, and which package
    /// would provide it.
    pub fn offer_package(&mut self, command: &str, package: &str) -> bool {
        self.conn
            .send(&HiveMessage::CommandNotFound {
                command: command.to_string(),
                package: package.to_string(),
            })
            .is_ok()
    }

    /// Enter or leave anonymous mode for this shell (and what it runs).
    pub fn set_anonymous(&mut self, on: bool) -> bool {
        let pid = Some(std::process::id());
        let msg = if on {
            HiveMessage::AnonymousModeEnter {
                level: AnonymousLevel::Detach,
                pid,
            }
        } else {
            HiveMessage::AnonymousModeExit { pid }
        };
        self.conn.send(&msg).is_ok()
    }
}

/// The package that would provide `command`, if one of that exact name can
/// be installed - asked of apt's cache (`apt-cache policy`, which needs no
/// privileges and no network). Only for plain names that are also valid
/// package names; nothing on systems without apt.
pub fn package_for_command(command: &str) -> Option<String> {
    if !is_valid_package_name(command) {
        return None;
    }
    let output = std::process::Command::new("apt-cache")
        .args(["policy", "--", command])
        .stderr(std::process::Stdio::null())
        .output()
        .ok()?;
    installable_candidate(&String::from_utf8_lossy(&output.stdout)).then(|| command.to_string())
}

/// Whether `apt-cache policy` output shows a version that can be installed.
fn installable_candidate(policy: &str) -> bool {
    policy.lines().any(|line| {
        line.trim()
            .strip_prefix("Candidate:")
            .is_some_and(|version| !matches!(version.trim(), "" | "(none)"))
    })
}

/// `[hive] Title: body` for a notice; nothing for anything else.
pub fn notice_line(msg: &HiveMessage) -> Option<String> {
    match msg {
        HiveMessage::Notification { title, body, .. } => Some(format!("[hive] {title}: {body}")),
        _ => None,
    }
}

/// The lines of the answer to `request_id`, if `msg` is that answer.
pub fn answer_lines(msg: &HiveMessage, request_id: MessageId) -> Option<Vec<String>> {
    match msg {
        HiveMessage::SuggestionResponse {
            request_id: answered,
            suggestions,
            ..
        } if *answered == request_id => {
            let mut lines: Vec<String> = suggestions
                .iter()
                .map(|s| {
                    let text = if s.description.trim().is_empty() {
                        &s.title
                    } else {
                        &s.description
                    };
                    format!("[hive] {}", text.trim())
                })
                .collect();
            if lines.is_empty() {
                lines.push("[hive] (no answer - the model had nothing to say)".to_string());
            }
            Some(lines)
        }
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use hive_common::messages::{Severity, Suggestion};

    fn suggestion(title: &str, description: &str) -> Suggestion {
        Suggestion {
            id: 1,
            title: title.into(),
            description: description.into(),
            action: None,
            learn_more: None,
            confidence: 0.7,
        }
    }

    #[test]
    fn answers_are_matched_to_their_question() {
        let asked = MessageId::new_v4();
        let answer = |request_id| HiveMessage::SuggestionResponse {
            request_id,
            suggestions: vec![
                suggestion("Check failed", "Run `systemctl --failed`"),
                suggestion("Just a title", ""),
            ],
            processing_time_ms: 1,
        };

        assert_eq!(
            answer_lines(&answer(asked), asked).unwrap(),
            vec!["[hive] Run `systemctl --failed`", "[hive] Just a title"]
        );
        assert!(answer_lines(&answer(MessageId::new_v4()), asked).is_none());
    }

    #[test]
    fn an_empty_answer_still_says_something() {
        let asked = MessageId::new_v4();
        let empty = HiveMessage::SuggestionResponse {
            request_id: asked,
            suggestions: vec![],
            processing_time_ms: 1,
        };
        assert_eq!(answer_lines(&empty, asked).unwrap().len(), 1);
    }

    #[test]
    fn a_package_is_offered_only_when_apt_has_a_candidate() {
        let available =
            "htop:\n  Installed: (none)\n  Candidate: 3.3.0-4build1\n  Version table:\n";
        let virtual_only = "mail-transport-agent:\n  Installed: (none)\n  Candidate: (none)\n";
        assert!(installable_candidate(available));
        assert!(!installable_candidate(virtual_only));
        assert!(!installable_candidate(""));
        // Not a package name: never even asked.
        assert_eq!(package_for_command("./script.sh"), None);
        assert_eq!(package_for_command("-o"), None);
    }

    #[test]
    fn notices_are_one_line() {
        let notice = HiveMessage::Notification {
            id: MessageId::new_v4(),
            title: "Service Crashed".into(),
            body: "nginx.service exited with code 1".into(),
            severity: Severity::Error,
            actions: vec![],
            timeout_secs: 10,
        };
        assert_eq!(
            notice_line(&notice).as_deref(),
            Some("[hive] Service Crashed: nginx.service exited with code 1")
        );
        assert!(notice_line(&HiveMessage::ReloadConfig).is_none());
    }

    #[test]
    fn a_question_round_trips_through_a_socket() {
        use std::os::unix::net::UnixListener;

        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("user.sock");
        let listener = UnixListener::bind(&path).unwrap();
        // A stand-in cortex: answers the first question it gets, after a
        // notice, the way a real one may interleave them.
        let server = thread::spawn(move || {
            let (stream, _) = listener.accept().unwrap();
            let mut conn = Connection::from_std(stream);
            let HiveMessage::UserQuery {
                request_id, query, ..
            } = conn.recv().unwrap()
            else {
                panic!("expected a UserQuery");
            };
            assert_eq!(query, "why?");
            conn.send(&HiveMessage::Notification {
                id: MessageId::new_v4(),
                title: "Low Disk Space".into(),
                body: "/ is 95.0% full".into(),
                severity: Severity::Warning,
                actions: vec![],
                timeout_secs: 10,
            })
            .unwrap();
            conn.send(&HiveMessage::SuggestionResponse {
                request_id,
                suggestions: vec![suggestion("t", "because")],
                processing_time_ms: 1,
            })
            .unwrap();
        });

        let mut hive = Hive::connect_to(&path).expect("connects");
        let answer = hive.ask("why?", None, || false).unwrap();
        server.join().unwrap();

        assert_eq!(answer, vec!["[hive] because"]);
        assert_eq!(
            hive.take_notices(),
            vec!["[hive] Low Disk Space: / is 95.0% full"]
        );
    }
}
