//! ZFS snapshot management.

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use std::process::Stdio;
use tokio::process::Command;
use tracing::{debug, info, warn};

use crate::retention::RetentionPolicy;

/// Parsed snapshot information
#[derive(Debug, Clone)]
pub struct SnapshotInfo {
    pub dataset: String,
    pub name: String,
    pub creation: DateTime<Utc>,
    pub used: u64,
    pub referenced: u64,
}

impl SnapshotInfo {
    /// Get full snapshot name (dataset@name)
    pub fn full_name(&self) -> String {
        format!("{}@{}", self.dataset, self.name)
    }

    /// Check if this is a Hive-created snapshot
    pub fn is_hive_snapshot(&self) -> bool {
        self.name.starts_with("hive-")
    }

    /// Check if this is an auto-snapshot
    pub fn is_auto_snapshot(&self) -> bool {
        self.name.starts_with("hive-auto-")
    }
}

/// Manages ZFS snapshots
pub struct SnapshotManager {
    dataset: String,
    recursive: bool,
    retention: RetentionPolicy,
}

impl SnapshotManager {
    /// Create a new snapshot manager
    pub fn new(dataset: String, recursive: bool, retention: RetentionPolicy) -> Self {
        Self {
            dataset,
            recursive,
            retention,
        }
    }

    /// Create an automatic snapshot with timestamp
    pub async fn create_auto_snapshot(&self) -> Result<String> {
        let timestamp = Utc::now().format("%Y%m%d-%H%M%S");
        let name = format!("hive-auto-{}", timestamp);
        self.create_named_snapshot(&self.dataset, &name, self.recursive)
            .await
    }

    /// Create a named snapshot before an operation
    #[allow(dead_code)] // not yet called; for actuator's auto-snapshot-before-destructive-op path
    pub async fn create_pre_operation_snapshot(&self, operation: &str) -> Result<String> {
        let timestamp = Utc::now().format("%Y%m%d-%H%M%S");
        let name = format!("hive-before-{}-{}", operation, timestamp);
        self.create_named_snapshot(&self.dataset, &name, self.recursive)
            .await
    }

    /// Create a snapshot with a specific name
    pub async fn create_named_snapshot(
        &self,
        dataset: &str,
        name: &str,
        recursive: bool,
    ) -> Result<String> {
        let full_name = format!("{}@{}", dataset, name);

        let mut cmd = Command::new("zfs");
        cmd.arg("snapshot");

        if recursive {
            cmd.arg("-r");
        }

        cmd.arg(&full_name);
        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());

        let output = cmd.output().await.context("Failed to run zfs snapshot")?;

        if output.status.success() {
            info!("Created snapshot: {}", full_name);
            Ok(format!("Created snapshot: {}", full_name))
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            anyhow::bail!("Failed to create snapshot: {}", stderr.trim())
        }
    }

    /// Restore a snapshot (rollback)
    pub async fn restore_snapshot(&self, dataset: &str, snapshot: &str) -> Result<String> {
        let full_name = format!("{}@{}", dataset, snapshot);

        let output = Command::new("zfs")
            .args(["rollback", "-r", &full_name])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .await
            .context("Failed to run zfs rollback")?;

        if output.status.success() {
            info!("Restored snapshot: {}", full_name);
            Ok(format!("Restored to snapshot: {}", full_name))
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            anyhow::bail!("Failed to restore snapshot: {}", stderr.trim())
        }
    }

    /// Delete a snapshot
    pub async fn delete_snapshot(&self, dataset: &str, snapshot: &str) -> Result<String> {
        let full_name = format!("{}@{}", dataset, snapshot);

        let output = Command::new("zfs")
            .args(["destroy", &full_name])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .await
            .context("Failed to run zfs destroy")?;

        if output.status.success() {
            info!("Deleted snapshot: {}", full_name);
            Ok(format!("Deleted snapshot: {}", full_name))
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            anyhow::bail!("Failed to delete snapshot: {}", stderr.trim())
        }
    }

    /// List snapshots
    pub async fn list_snapshots(&self, dataset: Option<&str>) -> Result<String> {
        let mut cmd = Command::new("zfs");
        cmd.args([
            "list",
            "-t",
            "snapshot",
            "-o",
            "name,creation,used,refer",
            "-H",
        ]);

        if let Some(ds) = dataset {
            cmd.args(["-r", ds]);
        } else {
            cmd.args(["-r", &self.dataset]);
        }

        let output = cmd
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .await
            .context("Failed to run zfs list")?;

        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            Ok(stdout.to_string())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            anyhow::bail!("Failed to list snapshots: {}", stderr.trim())
        }
    }

    /// Get parsed snapshot information
    pub async fn get_snapshots(&self) -> Result<Vec<SnapshotInfo>> {
        let output = Command::new("zfs")
            .args([
                "list",
                "-t",
                "snapshot",
                "-o",
                "name,creation,used,refer",
                "-H",
                "-p", // Parseable output
                "-r",
                &self.dataset,
            ])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .await
            .context("Failed to run zfs list")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            anyhow::bail!("Failed to list snapshots: {}", stderr.trim());
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let mut snapshots = Vec::new();

        for line in stdout.lines() {
            let parts: Vec<&str> = line.split('\t').collect();
            if parts.len() >= 4 {
                let full_name = parts[0];
                if let Some((dataset, name)) = full_name.split_once('@') {
                    let creation_ts: i64 = parts[1].parse().unwrap_or(0);
                    let creation =
                        DateTime::from_timestamp(creation_ts, 0).unwrap_or_else(Utc::now);
                    let used: u64 = parts[2].parse().unwrap_or(0);
                    let referenced: u64 = parts[3].parse().unwrap_or(0);

                    snapshots.push(SnapshotInfo {
                        dataset: dataset.to_string(),
                        name: name.to_string(),
                        creation,
                        used,
                        referenced,
                    });
                }
            }
        }

        Ok(snapshots)
    }

    /// Cleanup old snapshots based on retention policy
    pub async fn cleanup_old_snapshots(&self) -> Result<u32> {
        let snapshots = self.get_snapshots().await?;
        let mut deleted = 0;

        // Filter to only Hive auto-snapshots
        let hive_auto_snapshots: Vec<_> =
            snapshots.iter().filter(|s| s.is_auto_snapshot()).collect();

        // Get snapshots to delete based on retention policy
        let to_delete = self.retention.snapshots_to_delete(&hive_auto_snapshots);

        for snapshot in to_delete {
            match self
                .delete_snapshot(&snapshot.dataset, &snapshot.name)
                .await
            {
                Ok(_) => {
                    deleted += 1;
                    debug!("Cleaned up old snapshot: {}", snapshot.full_name());
                }
                Err(e) => {
                    warn!("Failed to delete snapshot {}: {}", snapshot.full_name(), e);
                }
            }
        }

        if deleted > 0 {
            info!("Cleaned up {} old snapshots", deleted);
        }

        Ok(deleted)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_snapshot_info() {
        let snapshot = SnapshotInfo {
            dataset: "rpool/ROOT/druidos".to_string(),
            name: "hive-auto-20240101-120000".to_string(),
            creation: Utc::now(),
            used: 1024,
            referenced: 2048,
        };

        assert_eq!(
            snapshot.full_name(),
            "rpool/ROOT/druidos@hive-auto-20240101-120000"
        );
        assert!(snapshot.is_hive_snapshot());
        assert!(snapshot.is_auto_snapshot());
    }

    #[test]
    fn test_non_hive_snapshot() {
        let snapshot = SnapshotInfo {
            dataset: "rpool/ROOT/druidos".to_string(),
            name: "manual-backup".to_string(),
            creation: Utc::now(),
            used: 1024,
            referenced: 2048,
        };

        assert!(!snapshot.is_hive_snapshot());
        assert!(!snapshot.is_auto_snapshot());
    }
}
