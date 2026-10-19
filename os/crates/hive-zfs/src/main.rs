//! Hive ZFS - ZFS Snapshot Integration
//!
//! Manages ZFS snapshots for the Hive Stack, providing:
//! - Automatic pre-operation snapshots
//! - Scheduled snapshot rotation
//! - Snapshot cleanup based on retention policies
//! - Integration with Hive actions for rollback

mod retention;
mod snapshot;

use anyhow::{Context, Result};
use hive_common::config::Config;
use hive_common::ipc::IpcSocket;
use hive_common::messages::HiveMessage;
use std::path::Path;
use std::time::Duration;
use tokio::signal;
use tracing::{error, info, warn};

use crate::retention::RetentionPolicy;
use crate::snapshot::SnapshotManager;

/// Default socket path for cortex connection
const CORTEX_SOCKET: &str = "/run/hive/cortex.sock";

/// Configuration for hive-zfs
#[derive(Debug, Clone)]
pub struct ZfsConfig {
    /// Primary dataset to snapshot: the configured one, or the root
    /// filesystem's (empty when neither exists)
    pub dataset: String,
    /// Whether to snapshot recursively
    pub recursive: bool,
    /// Retention policy
    pub retention: RetentionPolicy,
    /// Auto-snapshot interval in seconds (0 = disabled)
    pub auto_snapshot_interval: u64,
}

impl Default for ZfsConfig {
    fn default() -> Self {
        Self {
            dataset: root_dataset(),
            recursive: true,
            retention: RetentionPolicy::default(),
            auto_snapshot_interval: 3600, // Hourly
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    hive_common::logging::init("hive_zfs")?;

    if std::env::args().nth(1).as_deref() == Some("prune") {
        return prune();
    }

    info!("Hive ZFS starting...");

    // Load configuration
    let config = load_config().await?;

    // Check if ZFS is available
    if !is_zfs_available().await {
        error!("ZFS is not available on this system");
        return Err(anyhow::anyhow!("ZFS not available"));
    }

    if config.dataset.is_empty() {
        error!("The root filesystem is not on ZFS and no snapshot_dataset is configured");
        return Err(anyhow::anyhow!("No dataset to snapshot"));
    }

    // Initialize snapshot manager
    let mut snapshot_manager = SnapshotManager::new(
        config.dataset.clone(),
        config.recursive,
        config.retention.clone(),
    );

    // Connect to cortex
    let cortex_socket =
        std::env::var("HIVE_CORTEX_SOCKET").unwrap_or_else(|_| CORTEX_SOCKET.to_string());

    info!("Connecting to cortex at {}", cortex_socket);
    let mut cortex = IpcSocket::connect(&cortex_socket)
        .await
        .context("Failed to connect to cortex")?;

    info!("Hive ZFS ready");

    // Create auto-snapshot timer if configured
    let mut auto_interval = if config.auto_snapshot_interval > 0 {
        Some(tokio::time::interval(Duration::from_secs(
            config.auto_snapshot_interval,
        )))
    } else {
        None
    };

    // Create cleanup timer (run every hour)
    let mut cleanup_interval = tokio::time::interval(Duration::from_secs(3600));

    // Main event loop
    loop {
        tokio::select! {
            result = cortex.recv() => {
                match result {
                    Ok(msg) => {
                        if let Err(e) = handle_message(msg, &mut snapshot_manager, &mut cortex).await {
                            error!("Error handling message: {}", e);
                        }
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
            Some(_) = async {
                match &mut auto_interval {
                    Some(interval) => Some(interval.tick().await),
                    None => std::future::pending().await,
                }
            } => {
                info!("Creating automatic snapshot");
                if let Err(e) = snapshot_manager.create_auto_snapshot().await {
                    error!("Failed to create auto snapshot: {}", e);
                }
            }
            _ = cleanup_interval.tick() => {
                info!("Running snapshot cleanup");
                if let Err(e) = snapshot_manager.cleanup_old_snapshots().await {
                    error!("Failed to cleanup snapshots: {}", e);
                }
            }
            _ = signal::ctrl_c() => {
                info!("Received shutdown signal");
                break;
            }
        }
    }

    info!("Hive ZFS shutting down");
    Ok(())
}

async fn load_config() -> Result<ZfsConfig> {
    let config_path =
        std::env::var("HIVE_CONFIG").unwrap_or_else(|_| "/etc/hive/config.toml".to_string());

    if Path::new(&config_path).exists() {
        // Load from main config and extract ZFS settings
        let full_config = Config::load(&config_path)?;

        // Use actuator's snapshot_dataset if available
        let dataset = full_config
            .actuator
            .snapshot_dataset
            .unwrap_or_else(root_dataset);

        Ok(ZfsConfig {
            dataset,
            ..Default::default()
        })
    } else {
        warn!("Config file not found, using defaults");
        Ok(ZfsConfig::default())
    }
}

/// `hive-zfs prune`: remove the Hive's safety snapshots once they are past
/// `[zfs] prune_after_days`, sparing the newest `keep_newest`. Run daily as
/// root by hive-zfs-prune.timer - destroying snapshots is delegated to no
/// one. Only each system dataset's own `hive-*` snapshots are considered,
/// and each goes with `destroy -r`, the way it was taken.
fn prune() -> Result<()> {
    let config_path =
        std::env::var("HIVE_CONFIG").unwrap_or_else(|_| "/etc/hive/config.toml".to_string());
    let config = if Path::new(&config_path).exists() {
        Config::load(&config_path)?
    } else {
        Config::default()
    };
    let datasets = match config.actuator.snapshot_dataset {
        Some(dataset) => vec![dataset],
        None => hive_common::zfs::system_datasets(),
    };
    if datasets.is_empty() {
        info!("No ZFS system datasets: nothing to prune");
        return Ok(());
    }

    let now = chrono::Utc::now();
    let mut failures = 0;
    for dataset in &datasets {
        let names = snapshot_names(dataset)?;
        let prune = hive_common::zfs::snapshots_to_prune(
            &names,
            now,
            config.zfs.prune_after_days,
            config.zfs.keep_newest,
        );
        info!(
            "{}: {} snapshot(s), pruning {} Hive snapshot(s) older than {} days (keeping the newest {})",
            dataset,
            names.len(),
            prune.len(),
            config.zfs.prune_after_days,
            config.zfs.keep_newest
        );
        for name in prune {
            let snapshot = format!("{dataset}@{name}");
            let output = std::process::Command::new("zfs")
                .args(["destroy", "-r", &snapshot])
                .output()
                .context("Failed to run zfs destroy")?;
            if output.status.success() {
                info!("Pruned {}", snapshot);
            } else {
                failures += 1;
                error!(
                    "Failed to prune {}: {}",
                    snapshot,
                    String::from_utf8_lossy(&output.stderr).trim()
                );
            }
        }
    }
    if failures > 0 {
        anyhow::bail!("{failures} snapshot(s) could not be pruned");
    }
    Ok(())
}

/// The names (after `@`) of a dataset's own snapshots, not its children's.
fn snapshot_names(dataset: &str) -> Result<Vec<String>> {
    let output = std::process::Command::new("zfs")
        .args([
            "list", "-H", "-t", "snapshot", "-o", "name", "-d", "1", dataset,
        ])
        .output()
        .context("Failed to run zfs list")?;
    if !output.status.success() {
        anyhow::bail!(
            "zfs list for {} failed: {}",
            dataset,
            String::from_utf8_lossy(&output.stderr).trim()
        );
    }
    Ok(String::from_utf8_lossy(&output.stdout)
        .lines()
        .filter_map(|line| line.split_once('@'))
        .filter(|(owner, _)| *owner == dataset)
        .map(|(_, name)| name.to_string())
        .collect())
}

/// The dataset mounted at `/`, whatever the installer named it.
fn root_dataset() -> String {
    hive_common::zfs::system_datasets()
        .into_iter()
        .next()
        .unwrap_or_default()
}

async fn is_zfs_available() -> bool {
    tokio::process::Command::new("zfs")
        .arg("version")
        .output()
        .await
        .map(|o| o.status.success())
        .unwrap_or(false)
}

async fn handle_message(
    msg: HiveMessage,
    snapshot_manager: &mut SnapshotManager,
    cortex: &mut IpcSocket,
) -> Result<()> {
    match msg {
        HiveMessage::ActionRequest {
            request_id, action, ..
        } => {
            use hive_common::actions::Action;

            match action {
                Action::CreateSnapshot {
                    dataset,
                    name,
                    recursive,
                } => {
                    info!("Creating snapshot {}@{}", dataset, name);
                    let result = snapshot_manager
                        .create_named_snapshot(&dataset, &name, recursive)
                        .await;

                    let (success, output) = match result {
                        Ok(msg) => (true, Some(msg)),
                        Err(e) => (false, Some(e.to_string())),
                    };

                    cortex
                        .send(&HiveMessage::ActionResponse {
                            request_id,
                            action: Action::CreateSnapshot {
                                dataset,
                                name,
                                recursive,
                            },
                            success,
                            output,
                            exit_code: if success { Some(0) } else { Some(1) },
                        })
                        .await?;
                }

                Action::RestoreSnapshot { dataset, snapshot } => {
                    info!("Restoring snapshot {}@{}", dataset, snapshot);
                    let result = snapshot_manager.restore_snapshot(&dataset, &snapshot).await;

                    let (success, output) = match result {
                        Ok(msg) => (true, Some(msg)),
                        Err(e) => (false, Some(e.to_string())),
                    };

                    cortex
                        .send(&HiveMessage::ActionResponse {
                            request_id,
                            action: Action::RestoreSnapshot { dataset, snapshot },
                            success,
                            output,
                            exit_code: if success { Some(0) } else { Some(1) },
                        })
                        .await?;
                }

                Action::ListSnapshots { dataset } => {
                    info!("Listing snapshots for {:?}", dataset);
                    let result = snapshot_manager.list_snapshots(dataset.as_deref()).await;

                    let (success, output) = match result {
                        Ok(list) => (true, Some(list)),
                        Err(e) => (false, Some(e.to_string())),
                    };

                    cortex
                        .send(&HiveMessage::ActionResponse {
                            request_id,
                            action: Action::ListSnapshots { dataset },
                            success,
                            output,
                            exit_code: if success { Some(0) } else { Some(1) },
                        })
                        .await?;
                }

                Action::DeleteSnapshot { dataset, snapshot } => {
                    info!("Deleting snapshot {}@{}", dataset, snapshot);
                    let result = snapshot_manager.delete_snapshot(&dataset, &snapshot).await;

                    let (success, output) = match result {
                        Ok(msg) => (true, Some(msg)),
                        Err(e) => (false, Some(e.to_string())),
                    };

                    cortex
                        .send(&HiveMessage::ActionResponse {
                            request_id,
                            action: Action::DeleteSnapshot { dataset, snapshot },
                            success,
                            output,
                            exit_code: if success { Some(0) } else { Some(1) },
                        })
                        .await?;
                }

                _ => {
                    // Not a ZFS action, ignore
                }
            }
        }
        _ => {
            // Ignore other message types
        }
    }

    Ok(())
}
