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
    // The machine's settings: what a user asks for through the Ajustes app
    // (HiveMessage::UserRequest) and an administrator approves
    // =========================================================================
    /// Name the machine (`hostnamectl set-hostname`)
    SetHostname {
        /// A host label: letters, digits and hyphens, up to 63
        name: String,
    },

    /// The keyboard's layout, for the console and the Hive's screen
    /// (`localectl set-x11-keymap`, which writes /etc/default/keyboard)
    SetKeyboard {
        /// `us` or `br`: the layouts the screen reads
        layout: String,
        /// `pc105`, `abnt2`, or empty for the default
        model: String,
    },

    /// Pin the screen's presentation level, or let it be chosen by the
    /// measure again (None): a file the screen watches, no root needed
    SetScreenLevel {
        /// 0 plain, 1 effects, 2 fine; None lets the measure choose
        level: Option<u8>,
    },

    /// One interface's address: by DHCP, or fixed (netplan, through the
    /// root unit quantum-network-apply.service, which keeps the file
    /// before and comes back to it when the interface does not come up).
    /// Dangerous: a wrong address takes the machine off the network.
    SetNetwork {
        /// The interface (enp0s1)
        interface: String,
        /// By DHCP; the rest is then ignored
        dhcp: bool,
        /// A fixed address with its prefix (10.0.2.20/24)
        address: String,
        /// The gateway (10.0.2.2), or empty
        gateway: String,
        /// The DNS servers, or none
        dns: Vec<String>,
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
            Action::SetHostname { .. } => "SetHostname",
            Action::SetKeyboard { .. } => "SetKeyboard",
            Action::SetScreenLevel { .. } => "SetScreenLevel",
            Action::SetNetwork { .. } => "SetNetwork",
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
                | Action::SetHostname { .. }
                | Action::SetKeyboard { .. }
                | Action::SetNetwork { .. }
        )
    }

    /// Whether this is a setting of the machine a user may ask for
    /// (HiveMessage::UserRequest): the only actions a request may carry.
    pub fn is_a_setting(&self) -> bool {
        matches!(
            self,
            Action::SetHostname { .. }
                | Action::SetKeyboard { .. }
                | Action::SetScreenLevel { .. }
                | Action::SetNetwork { .. }
        )
    }

    /// What a setting does, in words: the title of the offer a request
    /// becomes ("name the machine forja").
    pub fn describe_setting(&self) -> Option<String> {
        Some(match self {
            Action::SetHostname { name } => format!("name the machine {}", name),
            Action::SetKeyboard { layout, model } if model.is_empty() => {
                format!("keyboard {}", layout)
            }
            Action::SetKeyboard { layout, model } => format!("keyboard {} ({})", layout, model),
            Action::SetScreenLevel { level: Some(l) } => format!(
                "screen level {}",
                match l {
                    0 => "plain",
                    1 => "effects",
                    2 => "fine",
                    _ => "?",
                }
            ),
            Action::SetScreenLevel { level: None } => {
                "screen level chosen by the measure".to_string()
            }
            Action::SetNetwork {
                interface,
                dhcp: true,
                ..
            } => format!("{} by DHCP", interface),
            Action::SetNetwork {
                interface,
                address,
                gateway,
                dns,
                ..
            } => {
                let mut what = format!("{} at {}", interface, address);
                if !gateway.is_empty() {
                    what.push_str(&format!(" via {}", gateway));
                }
                if !dns.is_empty() {
                    what.push_str(&format!(", dns {}", dns.join(" ")));
                }
                what
            }
            _ => return None,
        })
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
                | Action::SetNetwork { .. }
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
/// A host label as `hostnamectl` accepts it and the top bar shows it:
/// letters, digits and hyphens, 1 to 63 of them, not starting or ending
/// with a hyphen.
pub fn is_valid_hostname(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 63
        && !name.starts_with('-')
        && !name.ends_with('-')
        && name
            .chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-')
}

/// The keyboard layouts the screen reads, and the models each takes.
pub const KEYBOARD_LAYOUTS: &[(&str, &[&str])] =
    &[("us", &["", "pc105"]), ("br", &["", "abnt2", "pc105"])];

/// An interface name as the kernel allows it: up to 15 of letters,
/// digits, dots, hyphens and underscores, starting with a letter.
pub fn is_valid_interface(name: &str) -> bool {
    let mut chars = name.chars();
    !name.is_empty()
        && name.len() <= 15
        && chars.next().is_some_and(|c| c.is_ascii_lowercase())
        && chars
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || matches!(c, '.' | '-' | '_'))
}

/// A dotted IPv4 address.
pub fn is_valid_ipv4(text: &str) -> bool {
    text.parse::<std::net::Ipv4Addr>().is_ok()
}

/// An IPv4 address with its prefix, 10.0.2.20/24.
pub fn is_valid_ipv4_cidr(text: &str) -> bool {
    match text.split_once('/') {
        Some((addr, prefix)) => {
            is_valid_ipv4(addr) && prefix.parse::<u8>().is_ok_and(|p| (1..=32).contains(&p))
        }
        None => false,
    }
}

/// Whether a network setting is one netplan would take and the machine
/// would keep: by DHCP, or a fixed address with an optional gateway and
/// DNS servers, every one an IPv4 (at most four).
pub fn is_valid_network(
    interface: &str,
    dhcp: bool,
    address: &str,
    gateway: &str,
    dns: &[String],
) -> bool {
    is_valid_interface(interface)
        && dns.len() <= 4
        && dns.iter().all(|d| is_valid_ipv4(d))
        && (dhcp || (is_valid_ipv4_cidr(address) && (gateway.is_empty() || is_valid_ipv4(gateway))))
}

pub fn is_valid_keyboard(layout: &str, model: &str) -> bool {
    KEYBOARD_LAYOUTS
        .iter()
        .any(|(l, models)| *l == layout && models.contains(&model))
}

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
    fn a_setting_is_validated_and_described() {
        assert!(is_valid_hostname("forja"));
        assert!(is_valid_hostname("web-01"));
        assert!(!is_valid_hostname(""));
        assert!(!is_valid_hostname("-x"));
        assert!(!is_valid_hostname("Forja"));
        assert!(!is_valid_hostname("a b"));
        assert!(!is_valid_hostname(&"a".repeat(64)));
        assert!(is_valid_keyboard("br", "abnt2"));
        assert!(is_valid_keyboard("us", ""));
        assert!(!is_valid_keyboard("fr", ""));
        assert!(!is_valid_keyboard("us", "abnt2"));
        let name = Action::SetHostname {
            name: "forja".into(),
        };
        assert!(name.is_a_setting());
        assert_eq!(name.describe_setting().unwrap(), "name the machine forja");
        assert_eq!(
            Action::SetKeyboard {
                layout: "br".into(),
                model: "abnt2".into()
            }
            .describe_setting()
            .unwrap(),
            "keyboard br (abnt2)"
        );
        assert_eq!(
            Action::SetScreenLevel { level: Some(2) }
                .describe_setting()
                .unwrap(),
            "screen level fine"
        );
        assert_eq!(
            Action::SetScreenLevel { level: None }
                .describe_setting()
                .unwrap(),
            "screen level chosen by the measure"
        );
        assert!(!Action::RestartService {
            name: "nginx".into()
        }
        .is_a_setting());
        assert!(!name.is_dangerous());
    }

    #[test]
    fn a_network_setting_is_validated_described_and_dangerous() {
        assert!(is_valid_interface("enp0s1"));
        assert!(is_valid_interface("eth0"));
        assert!(!is_valid_interface("Eth0"));
        assert!(!is_valid_interface("enp0s1; rm"));
        assert!(!is_valid_interface("abcdefghijklmnop"));
        assert!(is_valid_ipv4_cidr("10.0.2.20/24"));
        assert!(!is_valid_ipv4_cidr("10.0.2.20"));
        assert!(!is_valid_ipv4_cidr("10.0.2.300/24"));
        assert!(!is_valid_ipv4_cidr("10.0.2.20/33"));
        assert!(is_valid_network("enp0s1", true, "", "", &[]));
        assert!(is_valid_network(
            "enp0s1",
            false,
            "10.0.2.20/24",
            "10.0.2.2",
            &["10.0.2.3".into()]
        ));
        assert!(!is_valid_network("enp0s1", false, "", "", &[]));
        assert!(!is_valid_network(
            "enp0s1",
            false,
            "10.0.2.20/24",
            "gw",
            &[]
        ));
        assert!(!is_valid_network(
            "enp0s1",
            true,
            "",
            "",
            &["1".into(), "2".into(), "3".into(), "4".into(), "5".into()]
        ));
        let fixed = Action::SetNetwork {
            interface: "enp0s1".into(),
            dhcp: false,
            address: "10.0.2.20/24".into(),
            gateway: "10.0.2.2".into(),
            dns: vec!["10.0.2.3".into()],
        };
        assert!(fixed.is_a_setting());
        assert!(
            fixed.is_dangerous(),
            "a wrong address takes the machine off the network"
        );
        assert_eq!(
            fixed.describe_setting().unwrap(),
            "enp0s1 at 10.0.2.20/24 via 10.0.2.2, dns 10.0.2.3"
        );
        let dhcp = Action::SetNetwork {
            interface: "enp0s1".into(),
            dhcp: true,
            address: String::new(),
            gateway: String::new(),
            dns: vec![],
        };
        assert_eq!(dhcp.describe_setting().unwrap(), "enp0s1 by DHCP");
    }

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
