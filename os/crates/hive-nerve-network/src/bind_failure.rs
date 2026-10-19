//! Services failing to bind a port that is already taken.
//!
//! A real port conflict never shows up in /proc/net: the process that loses
//! doesn't get a socket at all. What it leaves behind is its error message
//! ("Address already in use", EADDRINUSE) in the journal — usually written to
//! stderr, so at info priority — together with the journal's own trusted
//! record of who logged it (`_PID`, `_UID`, `_COMM`, `_CMDLINE`,
//! `_SYSTEMD_UNIT`), still there after that process has exited.

use regex::Regex;
use std::sync::OnceLock;

/// `journalctl --grep` pattern (PCRE2, used case-insensitively) selecting
/// the candidate entries.
pub const JOURNAL_PATTERN: &str = "address already in use|EADDRINUSE";

/// A process that could not bind `port`, as recorded by the journal.
#[derive(Debug, Clone, PartialEq)]
pub struct BindFailure {
    pub port: u16,
    pub pid: u32,
    pub uid: u32,
    pub comm: String,
    pub cmdline: Vec<String>,
    /// The unit the process ran in (e.g. `nginx.service`), if any.
    pub unit: Option<String>,
}

impl BindFailure {
    /// Who failed, for logs and dedup: the unit when there is one.
    pub fn requester(&self) -> String {
        match &self.unit {
            Some(unit) => format!("{unit} ({}, pid {})", self.comm, self.pid),
            None => format!("{} (pid {})", self.comm, self.pid),
        }
    }
}

/// The bind failure a journal entry (`journalctl -o json`) describes, if it
/// describes one and names the port. Messages that don't say which port
/// (Python's bare `OSError: [Errno 98]`, PostgreSQL's address-only line) are
/// skipped rather than guessed at.
pub fn from_journal_entry(entry: &serde_json::Value) -> Option<BindFailure> {
    let message = entry["MESSAGE"].as_str()?;
    let lower = message.to_ascii_lowercase();
    if !lower.contains("address already in use") && !lower.contains("eaddrinuse") {
        return None;
    }

    Some(BindFailure {
        port: port_in_message(message)?,
        pid: numeric_field(entry, "_PID").unwrap_or(0),
        uid: numeric_field(entry, "_UID").unwrap_or(0),
        comm: entry["_COMM"].as_str().unwrap_or("unknown").to_string(),
        cmdline: entry["_CMDLINE"]
            .as_str()
            .map(|c| vec![c.to_string()])
            .unwrap_or_default(),
        unit: entry["_SYSTEMD_UNIT"].as_str().map(str::to_string),
    })
}

fn numeric_field(entry: &serde_json::Value, field: &str) -> Option<u32> {
    entry[field].as_str()?.parse().ok()
}

/// In order of precedence: "port 22" (sshd); "address:port", where the
/// address is one a server would bind — dotted IPv4, bracketed IPv6, `*`,
/// `::` or `localhost` (anything looser would read a timestamp's `13:00` as
/// a port); and Python's `('127.0.0.1', 8000)` address tuples.
fn port_patterns() -> &'static [Regex; 3] {
    static PATTERNS: OnceLock<[Regex; 3]> = OnceLock::new();
    PATTERNS.get_or_init(|| {
        [
            Regex::new(r"(?i)\bport\s+(\d{1,5})\b").unwrap(),
            Regex::new(
                r"(?:\b\d{1,3}(?:\.\d{1,3}){3}|\[[0-9A-Fa-f:.]*\]|\*|::|\blocalhost):(\d{1,5})\b",
            )
            .unwrap(),
            Regex::new(r"\(\s*'[^']*'\s*,\s*(\d{1,5})\s*\)").unwrap(),
        ]
    })
}

fn port_in_message(message: &str) -> Option<u16> {
    port_patterns()
        .iter()
        .find_map(|re| re.captures(message))
        .and_then(|caps| caps[1].parse::<u16>().ok())
        .filter(|port| *port != 0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn reads_ports_from_real_servers_error_messages() {
        for (message, port) in [
            (
                "nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)",
                80,
            ),
            (
                "(98)Address already in use: AH00072: make_sock: could not bind to address [::]:443",
                443,
            ),
            (
                "Could not create server TCP listening socket *:6379: bind: Address already in use",
                6379,
            ),
            (
                "Error: listen EADDRINUSE: address already in use :::3000",
                3000,
            ),
            (
                "error: Bind to port 22 on 0.0.0.0 failed: Address already in use.",
                22,
            ),
            (
                "OSError: [Errno 98] error while attempting to bind on address ('127.0.0.1', 8000): address already in use",
                8000,
            ),
        ] {
            assert_eq!(port_in_message(message), Some(port), "{message}");
        }
    }

    #[test]
    fn a_timestamp_is_not_a_port() {
        assert_eq!(
            port_in_message(
                "2026/09/10 13:00:01 [emerg] bind() to 10.0.0.5:8443 failed (98: Address already in use)"
            ),
            Some(8443)
        );
        assert_eq!(
            port_in_message("13:00:01 bind failed: Address already in use"),
            None
        );
    }

    #[test]
    fn messages_without_a_port_are_skipped() {
        assert_eq!(
            port_in_message("could not bind IPv4 address \"0.0.0.0\": Address already in use"),
            None
        );
        assert_eq!(
            port_in_message("OSError: [Errno 98] Address already in use"),
            None
        );
    }

    #[test]
    fn builds_the_failure_from_the_journals_trusted_fields() {
        // Shape captured from a DruidOS guest (a transient unit failing to bind).
        let entry = json!({
            "PRIORITY": "6",
            "MESSAGE": "nginx: [emerg] bind() to 0.0.0.0:8081 failed (98: Address already in use)",
            "_PID": "1099",
            "_UID": "0",
            "_COMM": "python3",
            "_CMDLINE": "/usr/bin/python3 -c ...",
            "_SYSTEMD_UNIT": "druidos-probe-binder.service",
            "SYSLOG_IDENTIFIER": "python3",
        });

        let failure = from_journal_entry(&entry).unwrap();

        assert_eq!(
            failure,
            BindFailure {
                port: 8081,
                pid: 1099,
                uid: 0,
                comm: "python3".into(),
                cmdline: vec!["/usr/bin/python3 -c ...".into()],
                unit: Some("druidos-probe-binder.service".into()),
            }
        );
        assert_eq!(
            failure.requester(),
            "druidos-probe-binder.service (python3, pid 1099)"
        );
    }

    #[test]
    fn unrelated_entries_are_ignored() {
        let entry = json!({ "MESSAGE": "Listening on 0.0.0.0:80", "_PID": "1" });
        assert!(from_journal_entry(&entry).is_none());
    }
}
