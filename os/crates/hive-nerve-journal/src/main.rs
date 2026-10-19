//! Hive Nerve: Journal - Journald Observer
//!
//! Watches systemd journal for errors, warnings, and anomalies.
//! Reports significant events to hive-cortex for analysis.
//!
//! # Security Model
//!
//! - Runs as `_hive-sense` user with minimal privileges
//! - Read-only access to journal
//! - Cannot modify any system state

use anyhow::{Context, Result};
use hive_common::config::JournalNerveConfig;
use hive_common::ipc::IpcSocket;
use hive_common::messages::{HiveMessage, LogLine, Severity};
use std::collections::VecDeque;
use std::path::Path;
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;
use tokio::signal;
use tracing::{debug, error, info, warn};

/// Default socket path for cortex connection
const CORTEX_SOCKET: &str = "/run/hive/cortex.sock";

/// Maximum log lines to buffer before reporting
const MAX_BUFFER_SIZE: usize = 100;

/// Minimum number of similar errors to trigger anomaly detection
const ANOMALY_THRESHOLD: usize = 5;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    hive_common::logging::init("hive_nerve_journal")?;

    info!("Hive Nerve (Journal) starting...");

    // Load configuration
    let config = load_config().await?;

    // Drop privileges if running as root
    if nix::unistd::geteuid().is_root() {
        drop_privileges(&config.user)?;
    }

    // Connect to cortex
    let cortex_socket =
        std::env::var("HIVE_CORTEX_SOCKET").unwrap_or_else(|_| CORTEX_SOCKET.to_string());

    info!("Connecting to cortex at {}", cortex_socket);
    let mut cortex = IpcSocket::connect(&cortex_socket)
        .await
        .context("Failed to connect to cortex")?;

    info!("Hive Nerve (Journal) ready, watching for log events");
    hive_common::systemd::report_ready();

    // Start watching journal
    watch_journal(&config, &mut cortex).await
}

async fn load_config() -> Result<JournalNerveConfig> {
    let config_path =
        std::env::var("HIVE_CONFIG").unwrap_or_else(|_| "/etc/hive/config.toml".to_string());

    if Path::new(&config_path).exists() {
        let full_config = hive_common::config::Config::load(&config_path)?;
        Ok(full_config.nerves.journal)
    } else {
        warn!("Config file not found, using defaults");
        Ok(JournalNerveConfig::default())
    }
}

fn drop_privileges(username: &str) -> Result<()> {
    use nix::unistd::{setgid, setuid, Gid, Uid, User};

    let user = User::from_name(username)?.context(format!("User {} not found", username))?;

    setgid(Gid::from_raw(user.gid.as_raw()))?;
    setuid(Uid::from_raw(user.uid.as_raw()))?;

    info!("Dropped privileges to user {}", username);
    Ok(())
}

/// Arguments for the `journalctl` process the nerve reads events from.
fn journalctl_args(config: &JournalNerveConfig) -> Vec<String> {
    let mut args = vec![
        "--follow".to_string(),
        // Only entries logged from now on. Without this, --follow first
        // replays the last 10 matching entries, so every (re)start of the
        // nerve re-reported old crashes and anomalies as if they were new.
        "--lines=0".to_string(),
        "--no-pager".to_string(),
        "--output=json".to_string(),
        format!("--priority={}", config.min_priority),
    ];

    // Filter by specific services if configured
    for service in &config.watch_services {
        args.push("--unit".to_string());
        args.push(service.clone());
    }

    args
}

/// Watch the journal for events
async fn watch_journal(config: &JournalNerveConfig, cortex: &mut IpcSocket) -> Result<()> {
    let mut cmd = Command::new("journalctl");
    cmd.args(journalctl_args(config));
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::null());

    let mut child = cmd.spawn().context("Failed to spawn journalctl")?;
    let stdout = child.stdout.take().context("Failed to capture stdout")?;
    let reader = BufReader::new(stdout);
    let mut lines = reader.lines();

    // Buffer for anomaly detection
    let mut error_buffer: VecDeque<(String, LogLine)> = VecDeque::with_capacity(MAX_BUFFER_SIZE);

    loop {
        tokio::select! {
            line_result = lines.next_line() => {
                match line_result {
                    Ok(Some(line)) => {
                        if let Err(e) = process_log_line(&line, config, cortex, &mut error_buffer).await {
                            error!("Error processing log line: {}", e);
                        }
                    }
                    Ok(None) => {
                        warn!("Journal stream ended");
                        break;
                    }
                    Err(e) => {
                        error!("Error reading journal: {}", e);
                    }
                }
            }
            _ = signal::ctrl_c() => {
                info!("Received shutdown signal");
                break;
            }
        }
    }

    // Clean up child process
    let _ = child.kill().await;

    info!("Hive Nerve (Journal) shutting down");
    Ok(())
}

/// Process a single log line from journalctl JSON output
async fn process_log_line(
    line: &str,
    config: &JournalNerveConfig,
    cortex: &mut IpcSocket,
    error_buffer: &mut VecDeque<(String, LogLine)>,
) -> Result<()> {
    // Parse JSON
    let entry: serde_json::Value =
        serde_json::from_str(line).context("Failed to parse journal JSON")?;

    if logged_by_the_hive(&entry) {
        return Ok(());
    }

    // Extract fields
    let message = entry["MESSAGE"].as_str().unwrap_or("").to_string();

    let service = entry_service(&entry);

    let priority: u8 = entry["PRIORITY"]
        .as_str()
        .and_then(|s| s.parse().ok())
        .unwrap_or(6);

    let timestamp = chrono::Utc::now();

    // Skip if priority is below threshold
    if priority > config.min_priority {
        return Ok(());
    }

    let severity = priority_to_severity(priority);

    debug!(
        "Journal event: [{}] {}: {}",
        severity_str(severity),
        service,
        message
    );

    let log_line = LogLine {
        timestamp,
        message: message.clone(),
        priority,
        unit: Some(service.clone()),
    };

    // Check for service crash patterns
    if is_crash_pattern(&message) {
        let msg = HiveMessage::ServiceCrash {
            service: service.clone(),
            exit_code: extract_exit_code(&message).unwrap_or(-1),
            restart_count: 0, // Would need to track this
            logs: vec![log_line.clone()],
        };
        cortex.send(&msg).await?;
        info!("Reported service crash: {}", service);
    }

    // Buffer for anomaly detection
    error_buffer.push_back((service.clone(), log_line.clone()));
    if error_buffer.len() > MAX_BUFFER_SIZE {
        error_buffer.pop_front();
    }

    // Check for anomalies (same service, many errors)
    let service_errors: Vec<_> = error_buffer
        .iter()
        .filter(|(s, _)| s == &service)
        .map(|(_, l)| l.clone())
        .collect();

    if service_errors.len() >= ANOMALY_THRESHOLD {
        let msg = HiveMessage::LogAnomaly {
            service: service.clone(),
            severity,
            lines: service_errors,
            pattern: None,
        };
        cortex.send(&msg).await?;
        info!("Reported log anomaly for service: {}", service);

        // Clear buffer to avoid duplicate reports
        error_buffer.retain(|(s, _)| s != &service);
    }

    Ok(())
}

/// Whether a Hive component itself logged this entry.
///
/// The Hive's warnings and errors reach the journal at their real priority,
/// so without this the nerve would report them back into the Hive — a
/// synapse warning becomes an anomaly, which becomes a request to synapse,
/// which can warn again. Messages *about* a Hive unit from systemd (say,
/// hive-cortex crashed) are logged by PID 1, not by the Hive, and are still
/// reported.
fn logged_by_the_hive(entry: &serde_json::Value) -> bool {
    entry["_SYSTEMD_UNIT"]
        .as_str()
        .is_some_and(|unit| unit.starts_with("hive-"))
}

/// Which service a journal entry is about.
///
/// systemd's own messages about a unit ("foo.service: Failed with result
/// 'exit-code'.") are *logged by* PID 1, so their `_SYSTEMD_UNIT` is
/// `init.scope`; the unit they concern is in `UNIT` (`USER_UNIT` for a user
/// manager). Everything else is attributed to the unit that logged it.
fn entry_service(entry: &serde_json::Value) -> String {
    ["UNIT", "USER_UNIT", "_SYSTEMD_UNIT", "SYSLOG_IDENTIFIER"]
        .iter()
        .find_map(|field| entry[*field].as_str())
        .unwrap_or("unknown")
        .to_string()
}

/// Convert syslog priority to Hive severity
fn priority_to_severity(priority: u8) -> Severity {
    match priority {
        0 => Severity::Critical, // Emergency
        1 => Severity::Critical, // Alert
        2 => Severity::Critical, // Critical
        3 => Severity::Error,    // Error
        4 => Severity::Warning,  // Warning
        5 => Severity::Notice,   // Notice
        6 => Severity::Info,     // Info
        _ => Severity::Info,     // Debug and below
    }
}

fn severity_str(severity: Severity) -> &'static str {
    match severity {
        Severity::Critical => "CRIT",
        Severity::Error => "ERROR",
        Severity::Warning => "WARN",
        Severity::Notice => "NOTE",
        Severity::Info => "INFO",
    }
}

/// Check if a log message indicates a service crash
fn is_crash_pattern(message: &str) -> bool {
    let patterns = [
        "segmentation fault",
        "killed",
        "terminated",
        "exited with status",
        "failed with result",
        "core dumped",
        "fatal error",
        "panic",
        "oom-kill",
    ];

    let lower = message.to_lowercase();
    patterns.iter().any(|p| lower.contains(p))
}

/// Extract exit code from a crash message
fn extract_exit_code(message: &str) -> Option<i32> {
    // Look for patterns like "exited with status 1" or "exit code 137"
    let patterns = [r"status[= ](\d+)", r"exit code[= ](\d+)", r"code[= ](\d+)"];

    for pattern in patterns {
        if let Ok(re) = regex::Regex::new(pattern) {
            if let Some(caps) = re.captures(message) {
                if let Some(m) = caps.get(1) {
                    if let Ok(code) = m.as_str().parse() {
                        return Some(code);
                    }
                }
            }
        }
    }

    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_crash_pattern_detection() {
        assert!(is_crash_pattern(
            "nginx.service: Process exited with status 1"
        ));
        assert!(is_crash_pattern("Out of memory: Killed process 1234"));
        assert!(is_crash_pattern("Segmentation fault (core dumped)"));
        assert!(!is_crash_pattern("Started nginx service"));
    }

    #[test]
    fn test_exit_code_extraction() {
        assert_eq!(extract_exit_code("Process exited with status 1"), Some(1));
        assert_eq!(extract_exit_code("exit code 137"), Some(137));
    }

    #[test]
    fn systemd_messages_about_a_unit_are_attributed_to_that_unit() {
        // What PID 1 actually logs when a service fails (captured from a
        // DruidOS guest): logged by init.scope, about nginx.service.
        let entry = serde_json::json!({
            "MESSAGE": "nginx.service: Failed with result 'exit-code'.",
            "PRIORITY": "4",
            "_SYSTEMD_UNIT": "init.scope",
            "UNIT": "nginx.service",
            "SYSLOG_IDENTIFIER": "systemd",
        });

        assert_eq!(entry_service(&entry), "nginx.service");
    }

    #[test]
    fn the_hives_own_logs_are_not_reported_back_to_it() {
        let synapse_warning = serde_json::json!({
            "MESSAGE": "Failed to reach Ollama backend",
            "PRIORITY": "4",
            "_SYSTEMD_UNIT": "hive-synapse.service",
            "SYSLOG_IDENTIFIER": "hive-synapse",
        });
        assert!(logged_by_the_hive(&synapse_warning));
    }

    #[test]
    fn systemd_reporting_a_hive_unit_failure_still_counts() {
        let cortex_failed = serde_json::json!({
            "MESSAGE": "hive-cortex.service: Failed with result 'exit-code'.",
            "PRIORITY": "4",
            "_SYSTEMD_UNIT": "init.scope",
            "UNIT": "hive-cortex.service",
        });
        let nginx_error = serde_json::json!({
            "MESSAGE": "worker process exited on signal 9",
            "_SYSTEMD_UNIT": "nginx.service",
        });

        assert!(!logged_by_the_hive(&cortex_failed));
        assert!(!logged_by_the_hive(&nginx_error));
    }

    #[test]
    fn service_falls_back_to_the_logging_unit_then_identifier() {
        let from_unit = serde_json::json!({
            "_SYSTEMD_UNIT": "nginx.service",
            "SYSLOG_IDENTIFIER": "nginx",
        });
        let from_identifier = serde_json::json!({ "SYSLOG_IDENTIFIER": "kernel" });

        assert_eq!(entry_service(&from_unit), "nginx.service");
        assert_eq!(entry_service(&from_identifier), "kernel");
        assert_eq!(entry_service(&serde_json::json!({})), "unknown");
    }

    #[test]
    fn journalctl_follows_only_new_entries() {
        let args = journalctl_args(&JournalNerveConfig::default());

        assert!(args.contains(&"--follow".to_string()));
        assert!(
            args.contains(&"--lines=0".to_string()),
            "without --lines=0, journalctl --follow replays recent history on every start: {args:?}"
        );
    }

    #[test]
    fn journalctl_filters_by_priority_and_configured_units() {
        let config = JournalNerveConfig {
            min_priority: 3,
            watch_services: vec!["nginx.service".into(), "ssh.service".into()],
            ..JournalNerveConfig::default()
        };

        let args = journalctl_args(&config);

        assert!(args.contains(&"--priority=3".to_string()));
        assert!(args
            .windows(2)
            .any(|w| w == ["--unit".to_string(), "nginx.service".to_string()]));
        assert!(args
            .windows(2)
            .any(|w| w == ["--unit".to_string(), "ssh.service".to_string()]));
    }

    #[test]
    fn test_priority_to_severity() {
        assert!(matches!(priority_to_severity(0), Severity::Critical));
        assert!(matches!(priority_to_severity(3), Severity::Error));
        assert!(matches!(priority_to_severity(4), Severity::Warning));
        assert!(matches!(priority_to_severity(6), Severity::Info));
    }
}
