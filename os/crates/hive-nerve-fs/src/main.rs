//! Hive Nerve FS - Filesystem Observer
//!
//! Monitors filesystem changes and reports significant events:
//! - File modifications in watched directories
//! - Large file creations
//! - Permission changes
//! - Disk space alerts

mod events;
mod tree;
mod watcher;

use anyhow::{Context, Result};
use hive_common::config::FilesystemNerveConfig;
use hive_common::ipc::IpcSocket;
use hive_common::messages::{HiveMessage, MessageId, Severity};
use notify::event::{CreateKind, ModifyKind, RenameMode};
use notify::{EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use std::path::{Path, PathBuf};
use std::sync::mpsc;
use std::time::Duration;
use tokio::signal;
use tracing::{debug, error, info, warn};

use crate::events::FsEvent;
use crate::tree::{watch_tree, TreeWatch};
use crate::watcher::FsEventProcessor;

/// Default socket path for cortex connection
const CORTEX_SOCKET: &str = "/run/hive/cortex.sock";

fn next_message_id() -> MessageId {
    uuid::Uuid::new_v4()
}

/// Configuration for hive-nerve-fs
#[derive(Debug, Clone)]
pub struct NerveFsConfig {
    /// Paths to watch
    pub watch_paths: Vec<PathBuf>,
    /// Paths to ignore
    pub ignore_patterns: Vec<String>,
    /// Disk space warning threshold (percentage)
    pub disk_space_warn_percent: u8,
    /// Disk space critical threshold (percentage)
    pub disk_space_critical_percent: u8,
    /// Minimum file size change to report (bytes)
    pub min_size_change: u64,
}

impl NerveFsConfig {
    /// Watch settings from `[nerves.filesystem]` in /etc/hive/config.toml;
    /// the thresholds aren't configurable there (yet) and keep defaults.
    fn from_settings(settings: FilesystemNerveConfig) -> Self {
        Self {
            watch_paths: settings.watch_paths,
            ignore_patterns: settings.ignore_patterns,
            disk_space_warn_percent: 80,
            disk_space_critical_percent: 95,
            min_size_change: 1024 * 1024, // 1MB
        }
    }
}

impl Default for NerveFsConfig {
    fn default() -> Self {
        Self::from_settings(FilesystemNerveConfig::default())
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    hive_common::logging::init("hive_nerve_fs")?;

    info!("Hive Nerve FS starting...");

    // Load configuration
    let config = load_config().await?;

    // Connect to cortex
    let cortex_socket =
        std::env::var("HIVE_CORTEX_SOCKET").unwrap_or_else(|_| CORTEX_SOCKET.to_string());

    info!("Connecting to cortex at {}", cortex_socket);
    let mut cortex = IpcSocket::connect(&cortex_socket)
        .await
        .context("Failed to connect to cortex")?;

    // Set up file watcher
    let (tx, rx) = mpsc::channel();

    let mut watcher: RecommendedWatcher = notify::recommended_watcher(move |res| {
        if let Ok(event) = res {
            let _ = tx.send(event);
        }
    })?;

    // Watch configured paths
    for path in &config.watch_paths {
        if path.exists() {
            let tree = watch_tree(path, |dir| watcher.watch(dir, RecursiveMode::NonRecursive));
            info!(
                "Watching {}: {}",
                path.display(),
                describe_tree_watch(&tree)
            );
        } else {
            warn!("Path does not exist, skipping: {}", path.display());
        }
    }

    // Create event processor
    let processor = FsEventProcessor::new(config.ignore_patterns.clone());

    // Create disk space check interval
    let mut disk_check_interval = tokio::time::interval(Duration::from_secs(300)); // Every 5 minutes

    info!("Hive Nerve FS ready");
    hive_common::systemd::report_ready();

    // Main event loop
    loop {
        tokio::select! {
            // Check for filesystem events (non-async, so we use try_recv in a loop)
            _ = tokio::time::sleep(Duration::from_millis(100)) => {
                while let Ok(event) = rx.try_recv() {
                    watch_new_directories(&mut watcher, &event);
                    if let Some(fs_event) = processor.process_event(&event) {
                        if let Err(e) = report_event(&mut cortex, fs_event).await {
                            error!("Failed to report event: {}", e);
                        }
                    }
                }
            }
            // Periodic disk space check
            _ = disk_check_interval.tick() => {
                if let Err(e) = check_disk_space(&mut cortex, &config).await {
                    error!("Failed to check disk space: {}", e);
                }
            }
            // Handle messages from cortex
            result = cortex.recv() => {
                match result {
                    Ok(msg) => {
                        debug!("Received message: {}", msg.type_name());
                    }
                    Err(hive_common::ipc::IpcError::ConnectionClosed) => {
                        warn!("Connection to cortex closed, exiting");
                        break;
                    }
                    Err(e) => {
                        error!("Error receiving message: {}", e);
                    }
                }
            }
            _ = signal::ctrl_c() => {
                info!("Received shutdown signal");
                break;
            }
        }
    }

    info!("Hive Nerve FS shutting down");
    Ok(())
}

async fn load_config() -> Result<NerveFsConfig> {
    let config_path =
        std::env::var("HIVE_CONFIG").unwrap_or_else(|_| "/etc/hive/config.toml".to_string());

    if Path::new(&config_path).exists() {
        let full_config = hive_common::config::Config::load(&config_path)?;
        Ok(NerveFsConfig::from_settings(full_config.nerves.filesystem))
    } else {
        warn!("Config file not found, using defaults");
        Ok(NerveFsConfig::default())
    }
}

/// e.g. "412 directories" or "409 directories, 3 unreadable skipped
/// (/etc/credstore, /etc/ssl/private, ...)". Skipping is expected for an
/// unprivileged observer, so it's reported, not treated as an error.
fn describe_tree_watch(tree: &TreeWatch) -> String {
    const SHOWN: usize = 5;
    let mut description = format!("{} directories", tree.watched);
    if !tree.skipped.is_empty() {
        let mut shown: Vec<String> = tree
            .skipped
            .iter()
            .take(SHOWN)
            .map(|p| p.display().to_string())
            .collect();
        if tree.skipped.len() > SHOWN {
            shown.push("...".to_string());
        }
        description.push_str(&format!(
            ", {} unreadable skipped ({})",
            tree.skipped.len(),
            shown.join(", ")
        ));
    }
    description
}

/// inotify watches are per directory, so a directory created (or moved in)
/// inside a watched tree needs watches of its own before anything in it is
/// seen. Whatever lands in it before this runs is missed.
fn watch_new_directories(watcher: &mut impl Watcher, event: &notify::Event) {
    let path = match event.kind {
        EventKind::Create(CreateKind::Folder)
        | EventKind::Modify(ModifyKind::Name(RenameMode::To)) => event.paths.first(),
        EventKind::Modify(ModifyKind::Name(RenameMode::Both)) => event.paths.get(1),
        _ => None,
    };
    let Some(path) = path.filter(|p| p.is_dir()) else {
        return;
    };

    let tree = watch_tree(path, |dir| watcher.watch(dir, RecursiveMode::NonRecursive));
    debug!(
        "Watching new directory {}: {}",
        path.display(),
        describe_tree_watch(&tree)
    );
}

async fn report_event(cortex: &mut IpcSocket, event: FsEvent) -> Result<()> {
    let (severity, message) = match event {
        FsEvent::ConfigModified { path } => (
            Severity::Notice,
            format!("Config file modified: {}", path.display()),
        ),
        FsEvent::PermissionChanged {
            path,
            old_mode,
            new_mode,
        } => {
            let severity = if new_mode & 0o002 != 0 {
                // World-writable
                Severity::Warning
            } else {
                Severity::Notice
            };
            (
                severity,
                format!(
                    "Permissions changed: {} ({:o} -> {:o})",
                    path.display(),
                    old_mode,
                    new_mode
                ),
            )
        }
        FsEvent::LargeFileCreated { path, size } => (
            Severity::Notice,
            format!(
                "Large file created: {} ({:.2} MB)",
                path.display(),
                size as f64 / 1024.0 / 1024.0
            ),
        ),
        FsEvent::SensitiveAccess { path, user } => (
            Severity::Warning,
            format!("Sensitive file accessed: {} by {}", path.display(), user),
        ),
    };

    let msg = HiveMessage::Notification {
        id: next_message_id(),
        title: "Filesystem Event".to_string(),
        body: message.clone(),
        severity,
        actions: vec![],
        timeout_secs: 10,
    };

    cortex.send(&msg).await?;
    info!("Reported filesystem event: {}", message);
    Ok(())
}

async fn check_disk_space(cortex: &mut IpcSocket, config: &NerveFsConfig) -> Result<()> {
    // Get disk space for root filesystem
    let output = tokio::process::Command::new("df")
        .args(["--output=pcent,avail,target", "/"])
        .output()
        .await?;

    if !output.status.success() {
        return Ok(());
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    for line in stdout.lines().skip(1) {
        // Skip header
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() >= 3 {
            let usage_str = parts[0].trim_end_matches('%');
            if let Ok(usage) = usage_str.parse::<u8>() {
                let mount = parts[2];

                let (severity, should_report) = if usage >= config.disk_space_critical_percent {
                    (Severity::Critical, true)
                } else if usage >= config.disk_space_warn_percent {
                    (Severity::Warning, true)
                } else {
                    (Severity::Info, false)
                };

                if should_report {
                    let avail = parts[1];
                    let msg = HiveMessage::Notification {
                        id: next_message_id(),
                        title: "Disk Space Alert".to_string(),
                        body: format!(
                            "Disk usage at {}% on {} ({} available)",
                            usage, mount, avail
                        ),
                        severity,
                        actions: vec![],
                        timeout_secs: 30,
                    };

                    cortex.send(&msg).await?;
                }
            }
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = NerveFsConfig::default();
        assert!(!config.watch_paths.is_empty());
        assert!(config.disk_space_warn_percent < config.disk_space_critical_percent);
    }

    #[test]
    fn watch_settings_come_from_the_shipped_config() {
        // The nerve used to ignore /etc/hive/config.toml entirely and watch
        // a hardcoded list instead.
        let shipped = concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../config/hive/default.toml"
        );
        let full = hive_common::config::Config::load(shipped).unwrap();

        let config = NerveFsConfig::from_settings(full.nerves.filesystem);

        assert_eq!(
            config.watch_paths,
            vec![PathBuf::from("/etc"), PathBuf::from("/home")]
        );
        assert!(config
            .ignore_patterns
            .contains(&"node_modules/*".to_string()));
    }

    #[test]
    fn tree_watch_description_lists_a_few_skipped_directories() {
        let tree = TreeWatch {
            watched: 409,
            skipped: (1..=7)
                .map(|i| PathBuf::from(format!("/etc/private{i}")))
                .collect(),
        };

        assert_eq!(
            describe_tree_watch(&tree),
            "409 directories, 7 unreadable skipped (/etc/private1, /etc/private2, \
             /etc/private3, /etc/private4, /etc/private5, ...)"
        );
        assert_eq!(
            describe_tree_watch(&TreeWatch {
                watched: 3,
                skipped: vec![]
            }),
            "3 directories"
        );
    }
}
