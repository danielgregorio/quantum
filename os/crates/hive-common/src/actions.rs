//! Executable actions for the Hive actuator.
//!
//! All actions must go through the actuator's whitelist before execution.
//! This provides a security boundary between the SLM's suggestions and
//! actual system modifications.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Actions that can be executed by the actuator.
///
/// Each action variant defines a specific operation with typed parameters.
/// The actuator validates these against its whitelist before execution.
///
/// Derives PartialEq so hive-dashboard can correlate an incoming
/// ActionResponse (which only carries the Action back, not any
/// notification/suggestion id) with the suggestion it sent — see
/// hive-dashboard's `apply_action_response`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Action {
    // =========================================================================
    // Command execution
    // =========================================================================
    /// Run a whitelisted command
    RunCommand {
        /// Command name (must be in whitelist)
        cmd: String,
        /// Command arguments
        args: Vec<String>,
        /// Working directory (optional)
        cwd: Option<PathBuf>,
        /// Environment variables to set
        env: Vec<(String, String)>,
    },

    // =========================================================================
    // ZFS operations
    // =========================================================================
    /// Create a ZFS snapshot
    CreateSnapshot {
        /// Dataset name (e.g., "rpool/ROOT/druidos")
        dataset: String,
        /// Snapshot name (e.g., "before-update")
        name: String,
        /// Whether to snapshot recursively
        recursive: bool,
    },

    /// Restore from a ZFS snapshot
    RestoreSnapshot {
        /// Dataset name
        dataset: String,
        /// Snapshot name
        snapshot: String,
    },

    /// List ZFS snapshots
    ListSnapshots {
        /// Dataset name (optional, all if None)
        dataset: Option<String>,
    },

    /// Delete a ZFS snapshot
    DeleteSnapshot {
        /// Dataset name
        dataset: String,
        /// Snapshot name
        snapshot: String,
    },

    // =========================================================================
    // User interface
    // =========================================================================
    /// Show a desktop notification
    ShowNotification {
        /// Notification title
        title: String,
        /// Notification body
        body: String,
        /// Urgency level (low, normal, critical)
        urgency: NotificationUrgency,
        /// Action buttons
        actions: Vec<String>,
        /// Icon name or path
        icon: Option<String>,
    },

    /// Open a file in the default or specified editor
    OpenFile {
        /// Path to the file
        path: PathBuf,
        /// Specific editor to use (optional)
        editor: Option<String>,
        /// Line number to jump to
        line: Option<u32>,
    },

    /// Open a URL in the default browser
    OpenUrl {
        /// URL to open
        url: String,
    },

    // =========================================================================
    // Package management
    // =========================================================================
    /// Install a package
    InstallPackage {
        /// Package name
        name: String,
        /// Whether to auto-confirm
        assume_yes: bool,
    },

    /// Remove a package
    RemovePackage {
        /// Package name
        name: String,
        /// Whether to purge config files
        purge: bool,
    },

    /// Update package lists
    UpdatePackageLists,

    /// Upgrade installed packages
    UpgradePackages {
        /// Only upgrade specific packages (empty = all)
        packages: Vec<String>,
    },

    // =========================================================================
    // Service management
    // =========================================================================
    /// Start a systemd service
    StartService {
        /// Service name
        name: String,
    },

    /// Stop a systemd service
    StopService {
        /// Service name
        name: String,
    },

    /// Restart a systemd service
    RestartService {
        /// Service name
        name: String,
    },

    /// Reload a systemd service
    ReloadService {
        /// Service name
        name: String,
    },

    /// Enable a service to start at boot
    EnableService {
        /// Service name
        name: String,
        /// Start immediately
        now: bool,
    },

    /// Disable a service from starting at boot
    DisableService {
        /// Service name
        name: String,
        /// Stop immediately
        now: bool,
    },

    // =========================================================================
    // File operations
    // =========================================================================
    /// Create a directory
    CreateDirectory {
        /// Path to create
        path: PathBuf,
        /// Create parent directories if needed
        parents: bool,
        /// Permissions mode (e.g., 0o755)
        mode: Option<u32>,
    },

    /// Move/rename a file or directory
    MoveFile {
        /// Source path
        from: PathBuf,
        /// Destination path
        to: PathBuf,
    },

    /// Copy a file or directory
    CopyFile {
        /// Source path
        from: PathBuf,
        /// Destination path
        to: PathBuf,
        /// Copy recursively (for directories)
        recursive: bool,
    },

    /// Delete a file or directory (moves to trash by default)
    DeleteFile {
        /// Path to delete
        path: PathBuf,
        /// Bypass trash and delete permanently
        permanent: bool,
    },

    /// Change file permissions
    ChangePermissions {
        /// Path to modify
        path: PathBuf,
        /// New mode (e.g., 0o644)
        mode: u32,
        /// Apply recursively
        recursive: bool,
    },

    // =========================================================================
    // Network operations
    // =========================================================================
    /// Kill a process using a specific port
    KillPortProcess {
        /// Port number
        port: u16,
        /// Signal to send (default: SIGTERM)
        signal: Option<i32>,
    },

    /// Add a firewall rule
    AddFirewallRule {
        /// Rule specification
        rule: FirewallRule,
    },

    // =========================================================================
    // System operations
    // =========================================================================
    /// Reboot the system
    Reboot {
        /// Delay in seconds before reboot
        delay_secs: u32,
    },

    /// Shutdown the system
    Shutdown {
        /// Delay in seconds before shutdown
        delay_secs: u32,
    },

    /// Suspend the system
    Suspend,

    /// Clean package cache
    CleanPackageCache,

    /// Run garbage collection (logs, temp files, etc.)
    CleanSystem {
        /// What to clean
        targets: Vec<CleanTarget>,
    },
}

/// Notification urgency levels
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum NotificationUrgency {
    Low,
    Normal,
    Critical,
}

/// Firewall rule specification
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FirewallRule {
    /// Allow or deny
    pub action: FirewallAction,
    /// Protocol (tcp, udp, or both)
    pub protocol: Option<String>,
    /// Port number
    pub port: Option<u16>,
    /// Source address/network
    pub source: Option<String>,
    /// Destination address/network
    pub destination: Option<String>,
    /// Rule comment
    pub comment: Option<String>,
}

/// Firewall action
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum FirewallAction {
    Allow,
    Deny,
}

/// Targets for system cleaning
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum CleanTarget {
    /// Old journal logs
    JournalLogs { older_than_days: u32 },
    /// Temporary files
    TempFiles,
    /// Package cache
    PackageCache,
    /// Thumbnail cache
    Thumbnails,
    /// Old kernels
    OldKernels { keep_count: u32 },
    /// Trash
    Trash { older_than_days: u32 },
}

/// Result of an action execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionResult {
    /// Whether the action succeeded
    pub success: bool,
    /// Output message
    pub message: Option<String>,
    /// Exit code (for commands)
    pub exit_code: Option<i32>,
    /// Execution time in milliseconds
    pub duration_ms: u64,
}

impl Action {
    /// Get the action type name for logging
    pub fn type_name(&self) -> &'static str {
        match self {
            Action::RunCommand { .. } => "RunCommand",
            Action::CreateSnapshot { .. } => "CreateSnapshot",
            Action::RestoreSnapshot { .. } => "RestoreSnapshot",
            Action::ListSnapshots { .. } => "ListSnapshots",
            Action::DeleteSnapshot { .. } => "DeleteSnapshot",
            Action::ShowNotification { .. } => "ShowNotification",
            Action::OpenFile { .. } => "OpenFile",
            Action::OpenUrl { .. } => "OpenUrl",
            Action::InstallPackage { .. } => "InstallPackage",
            Action::RemovePackage { .. } => "RemovePackage",
            Action::UpdatePackageLists => "UpdatePackageLists",
            Action::UpgradePackages { .. } => "UpgradePackages",
            Action::StartService { .. } => "StartService",
            Action::StopService { .. } => "StopService",
            Action::RestartService { .. } => "RestartService",
            Action::ReloadService { .. } => "ReloadService",
            Action::EnableService { .. } => "EnableService",
            Action::DisableService { .. } => "DisableService",
            Action::CreateDirectory { .. } => "CreateDirectory",
            Action::MoveFile { .. } => "MoveFile",
            Action::CopyFile { .. } => "CopyFile",
            Action::DeleteFile { .. } => "DeleteFile",
            Action::ChangePermissions { .. } => "ChangePermissions",
            Action::KillPortProcess { .. } => "KillPortProcess",
            Action::AddFirewallRule { .. } => "AddFirewallRule",
            Action::Reboot { .. } => "Reboot",
            Action::Shutdown { .. } => "Shutdown",
            Action::Suspend => "Suspend",
            Action::CleanPackageCache => "CleanPackageCache",
            Action::CleanSystem { .. } => "CleanSystem",
        }
    }

    /// Check if this action requires root privileges
    pub fn requires_root(&self) -> bool {
        matches!(
            self,
            Action::InstallPackage { .. }
                | Action::RemovePackage { .. }
                | Action::UpdatePackageLists
                | Action::UpgradePackages { .. }
                | Action::StartService { .. }
                | Action::StopService { .. }
                | Action::RestartService { .. }
                | Action::ReloadService { .. }
                | Action::EnableService { .. }
                | Action::DisableService { .. }
                | Action::CreateSnapshot { .. }
                | Action::RestoreSnapshot { .. }
                | Action::DeleteSnapshot { .. }
                | Action::AddFirewallRule { .. }
                | Action::Reboot { .. }
                | Action::Shutdown { .. }
                | Action::Suspend
                | Action::CleanPackageCache
        )
    }

    /// Check if this action is considered dangerous
    pub fn is_dangerous(&self) -> bool {
        matches!(
            self,
            Action::RestoreSnapshot { .. }
                | Action::DeleteSnapshot { .. }
                | Action::RemovePackage { .. }
                | Action::DeleteFile {
                    permanent: true,
                    ..
                }
                | Action::Reboot { .. }
                | Action::Shutdown { .. }
                | Action::CleanSystem { .. }
        )
    }

    /// Whether the system should be snapshotted before this action runs:
    /// package changes, which rewrite the system in ways only a rollback
    /// undoes. Not `RestoreSnapshot`: `zfs rollback -r` destroys every
    /// snapshot newer than its target, the one just taken included.
    pub fn should_snapshot_first(&self) -> bool {
        matches!(
            self,
            Action::InstallPackage { .. }
                | Action::RemovePackage { .. }
                | Action::UpgradePackages { .. }
        )
    }
}

/// Whether `name` is a valid Debian package name: lowercase letters, digits
/// and `+ - .`, starting with a letter or digit, at least two characters.
/// Anything else - an option like `--allow-downgrades`, a path, a glob -
/// never reaches apt or PackageKit as a package.
pub fn is_valid_package_name(name: &str) -> bool {
    let mut chars = name.chars();
    name.len() >= 2
        && chars
            .next()
            .is_some_and(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
        && chars
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || matches!(c, '+' | '-' | '.'))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn package_names_follow_debian_policy() {
        for good in [
            "nginx",
            "g++",
            "libc6",
            "python3.12",
            "ca-certificates",
            "7zip",
        ] {
            assert!(is_valid_package_name(good), "{good}");
        }
        for bad in [
            "",
            "x",
            "-o",
            "--allow-downgrades",
            "Nginx",
            "./x.deb",
            "a b",
            "nginx*",
            "a;b",
        ] {
            assert!(!is_valid_package_name(bad), "{bad:?}");
        }
    }

    #[test]
    fn test_action_serialization() {
        let action = Action::CreateSnapshot {
            dataset: "rpool/ROOT/druidos".into(),
            name: "test".into(),
            recursive: false,
        };

        let encoded = bincode::serialize(&action).unwrap();
        let decoded: Action = bincode::deserialize(&encoded).unwrap();

        assert_eq!(decoded.type_name(), "CreateSnapshot");
    }

    #[test]
    fn package_changes_are_snapshotted_first() {
        assert!(Action::InstallPackage {
            name: "nginx".into(),
            assume_yes: true
        }
        .should_snapshot_first());
        assert!(Action::RemovePackage {
            name: "nginx".into(),
            purge: false
        }
        .should_snapshot_first());
        assert!(Action::UpgradePackages { packages: vec![] }.should_snapshot_first());

        assert!(!Action::RestoreSnapshot {
            dataset: "rpool/ROOT/druidos".into(),
            snapshot: "hive-x".into()
        }
        .should_snapshot_first());
        assert!(!Action::RunCommand {
            cmd: "journalctl".into(),
            args: vec![],
            cwd: None,
            env: vec![]
        }
        .should_snapshot_first());
        assert!(!Action::RestartService {
            name: "nginx".into()
        }
        .should_snapshot_first());
    }

    #[test]
    fn test_requires_root() {
        assert!(Action::InstallPackage {
            name: "vim".into(),
            assume_yes: false
        }
        .requires_root());

        assert!(!Action::OpenFile {
            path: "/tmp/test".into(),
            editor: None,
            line: None
        }
        .requires_root());
    }
}
