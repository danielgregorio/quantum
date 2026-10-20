//! Action whitelist management.
//!
//! Only actions matching the whitelist can be executed by the actuator.
//! Fails closed: an empty or missing config denies everything, and each
//! field here corresponds to a real `Action` variant (see
//! `hive_common::actions::Action`) rather than an independent schema that
//! can silently drift out of sync with it.

use anyhow::{Context, Result};
use hive_common::actions::{is_valid_hostname, is_valid_keyboard, is_valid_package_name, Action};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::path::Path;

/// A `*`-wildcard glob pattern (no `?`, no character classes — just `*`
/// matching any run of characters, matched with the standard greedy
/// backtracking algorithm).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(transparent)]
pub struct GlobPattern(String);

impl GlobPattern {
    pub fn matches(&self, text: &str) -> bool {
        wildcard_match(self.0.as_bytes(), text.as_bytes())
    }
}

fn wildcard_match(pattern: &[u8], text: &[u8]) -> bool {
    let (mut p, mut t) = (0usize, 0usize);
    let mut star: Option<usize> = None;
    let mut match_from = 0usize;

    while t < text.len() {
        if p < pattern.len() && (pattern[p] == b'*' || pattern[p] == text[t]) {
            if pattern[p] == b'*' {
                star = Some(p);
                match_from = t;
                p += 1;
            } else {
                p += 1;
                t += 1;
            }
        } else if let Some(sp) = star {
            p = sp + 1;
            match_from += 1;
            t = match_from;
        } else {
            return false;
        }
    }

    while p < pattern.len() && pattern[p] == b'*' {
        p += 1;
    }
    p == pattern.len()
}

/// One allowed `(command, args)` pair for `Action::RunCommand`. Matching is
/// exact on the command name and positional on args — `"*"` matches any
/// single argument at that position, but the argument count must match
/// exactly (no "and anything after this").
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CommandPattern {
    pub command: String,
    #[serde(default)]
    pub args: Vec<String>,
}

impl CommandPattern {
    pub fn matches(&self, cmd: &str, args: &[String]) -> bool {
        self.command == cmd
            && self.args.len() == args.len()
            && self
                .args
                .iter()
                .zip(args.iter())
                .all(|(pattern, actual)| pattern == "*" || pattern == actual)
    }
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct RunCommandRule {
    #[serde(default)]
    pub allowed: Vec<CommandPattern>,
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct ServiceRule {
    #[serde(default)]
    pub allowed: HashSet<String>,
    #[serde(default)]
    pub blocked: Vec<GlobPattern>,
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct AptRemoveRule {
    #[serde(default)]
    pub blocked_packages: Vec<GlobPattern>,
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct FileOpsRule {
    #[serde(default)]
    pub allowed_paths: Vec<GlobPattern>,
    #[serde(default)]
    pub blocked_paths: Vec<GlobPattern>,
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct ZfsRule {
    #[serde(default)]
    pub allowed_datasets: Vec<GlobPattern>,
    #[serde(default)]
    pub destroy_snapshot_pattern: Option<GlobPattern>,
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct MiscRule {
    #[serde(default)]
    pub kill_port_process: bool,
    #[serde(default)]
    pub open_url: bool,
    #[serde(default)]
    pub firewall: bool,
    /// The machine's settings a user may ask for (`<qh:allow action=>`):
    /// its name, its keyboard, its screen's level.
    #[serde(default)]
    pub set_hostname: bool,
    #[serde(default)]
    pub set_keyboard: bool,
    #[serde(default)]
    pub set_screen_level: bool,
}

/// Whitelist configuration. Everything defaults to empty/false (deny) —
/// see `Whitelist::load`.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct WhitelistConfig {
    #[serde(default)]
    pub run_command: RunCommandRule,
    #[serde(default)]
    pub service: ServiceRule,
    #[serde(default)]
    pub apt_remove: AptRemoveRule,
    #[serde(default)]
    pub file_ops: FileOpsRule,
    #[serde(default)]
    pub zfs: ZfsRule,
    #[serde(default)]
    pub misc: MiscRule,
    /// Per-action-type rate limit overrides, keyed by `Action::type_name()`
    /// (e.g. "InstallPackage"). The actuator's global rate limit lives in
    /// `ActuatorConfig.rate_limit`, not here — this only tightens specific
    /// types further.
    #[serde(default)]
    pub rate_limits: HashMap<String, u32>,
}

/// Action whitelist checker
pub struct Whitelist {
    config: WhitelistConfig,
}

impl Whitelist {
    /// Construct directly from a config (used by tests in sibling modules,
    /// where `Whitelist`'s private `config` field isn't visible).
    #[cfg(test)]
    pub(crate) fn from_config(config: WhitelistConfig) -> Self {
        Self { config }
    }

    /// Load whitelist from file, or deny everything if it doesn't exist.
    pub fn load(path: &str) -> Result<Self> {
        let config = if Path::new(path).exists() {
            let content = std::fs::read_to_string(path).context("Failed to read whitelist file")?;
            toml::from_str(&content).context("Failed to parse whitelist")?
        } else {
            tracing::warn!(
                "Whitelist file not found at {} — denying all actions by default",
                path
            );
            WhitelistConfig::default()
        };

        Ok(Self { config })
    }

    /// Check if an action is allowed
    pub fn is_allowed(&self, action: &Action) -> bool {
        match action {
            Action::RunCommand { cmd, args, .. } => self
                .config
                .run_command
                .allowed
                .iter()
                .any(|pattern| pattern.matches(cmd, args)),

            Action::CreateSnapshot { dataset, .. } | Action::RestoreSnapshot { dataset, .. } => {
                self.dataset_allowed(dataset)
            }

            Action::ListSnapshots { dataset } => match dataset {
                Some(d) => self.dataset_allowed(d),
                None => true,
            },

            Action::DeleteSnapshot { dataset, snapshot } => {
                self.dataset_allowed(dataset)
                    && match &self.config.zfs.destroy_snapshot_pattern {
                        Some(pattern) => pattern.matches(snapshot),
                        None => false,
                    }
            }

            // One package per action; throughput is bounded by the
            // per-type rate limit instead of a per-call count here. The name
            // must be a real package name, never an option or a path.
            Action::InstallPackage { name, .. } => is_valid_package_name(name),

            Action::RemovePackage { name, .. } => {
                is_valid_package_name(name)
                    && !self
                        .config
                        .apt_remove
                        .blocked_packages
                        .iter()
                        .any(|pattern| pattern.matches(name))
            }

            Action::UpgradePackages { packages } => {
                packages.iter().all(|name| is_valid_package_name(name))
            }

            Action::UpdatePackageLists | Action::CleanPackageCache => true,

            Action::StartService { name }
            | Action::StopService { name }
            | Action::RestartService { name }
            | Action::ReloadService { name }
            | Action::EnableService { name, .. }
            | Action::DisableService { name, .. } => {
                self.config.service.allowed.contains(name)
                    && !self
                        .config
                        .service
                        .blocked
                        .iter()
                        .any(|pattern| pattern.matches(name))
            }

            Action::KillPortProcess { .. } => self.config.misc.kill_port_process,

            Action::OpenUrl { url } => {
                self.config.misc.open_url
                    && (url.starts_with("http://") || url.starts_with("https://"))
            }

            Action::ShowNotification { .. } | Action::OpenFile { .. } => true,

            Action::CreateDirectory { path, .. } => self.path_allowed(path),
            Action::MoveFile { to, .. } => self.path_allowed(to),
            Action::CopyFile { to, .. } => self.path_allowed(to),
            Action::DeleteFile { path, .. } => self.path_allowed(path),
            Action::ChangePermissions { path, .. } => self.path_allowed(path),

            Action::AddFirewallRule { .. } => self.config.misc.firewall,

            // The settings: switched on one by one, and never with a value
            // hostnamectl or localectl would refuse (or take as an option)
            Action::SetHostname { name } => {
                self.config.misc.set_hostname && is_valid_hostname(name)
            }
            Action::SetKeyboard { layout, model } => {
                self.config.misc.set_keyboard && is_valid_keyboard(layout, model)
            }
            Action::SetScreenLevel { level } => {
                self.config.misc.set_screen_level && level.map_or(true, |l| l <= 2)
            }

            // System power operations always need explicit permission —
            // there's no config knob for these on purpose.
            Action::Reboot { .. } | Action::Shutdown { .. } | Action::Suspend => false,

            Action::CleanSystem { .. } => true,
        }
    }

    /// Rate limit overrides for specific `Action::type_name()`s, layered
    /// on top of the actuator's global limit.
    pub fn rate_limit_overrides(&self) -> &HashMap<String, u32> {
        &self.config.rate_limits
    }

    fn dataset_allowed(&self, dataset: &str) -> bool {
        self.config
            .zfs
            .allowed_datasets
            .iter()
            .any(|pattern| pattern.matches(dataset))
    }

    fn path_allowed(&self, path: &std::path::Path) -> bool {
        let path_str = path.to_string_lossy();
        self.config
            .file_ops
            .allowed_paths
            .iter()
            .any(|pattern| pattern.matches(&path_str))
            && !self
                .config
                .file_ops
                .blocked_paths
                .iter()
                .any(|pattern| pattern.matches(&path_str))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_config() -> WhitelistConfig {
        WhitelistConfig {
            run_command: RunCommandRule {
                allowed: vec![
                    CommandPattern {
                        command: "ip".into(),
                        args: vec!["addr".into()],
                    },
                    CommandPattern {
                        command: "systemctl".into(),
                        args: vec!["status".into(), "*".into()],
                    },
                ],
            },
            service: ServiceRule {
                allowed: ["nginx".to_string()].into_iter().collect(),
                blocked: vec![GlobPattern("hive-*".into())],
            },
            ..Default::default()
        }
    }

    #[test]
    fn glob_pattern_matching() {
        assert!(GlobPattern("hive-*".into()).matches("hive-cortex"));
        assert!(!GlobPattern("hive-*".into()).matches("nginx"));
        assert!(GlobPattern("/home/*/.ssh/*".into()).matches("/home/daniel/.ssh/id_rsa"));
        assert!(!GlobPattern("/home/*/.ssh/*".into()).matches("/home/daniel/docs/file.txt"));
        assert!(GlobPattern("*".into()).matches("anything"));
        assert!(GlobPattern("exact".into()).matches("exact"));
        assert!(!GlobPattern("exact".into()).matches("exactly"));
        assert!(!GlobPattern("exactly".into()).matches("exact"));
    }

    #[test]
    fn default_config_denies_everything() {
        let whitelist = Whitelist {
            config: WhitelistConfig::default(),
        };

        assert!(!whitelist.is_allowed(&Action::RunCommand {
            cmd: "ls".into(),
            args: vec![],
            cwd: None,
            env: vec![],
        }));
        assert!(!whitelist.is_allowed(&Action::RestartService {
            name: "nginx".into(),
        }));
        assert!(!whitelist.is_allowed(&Action::KillPortProcess {
            port: 8080,
            signal: None,
        }));
        assert!(!whitelist.is_allowed(&Action::OpenUrl {
            url: "https://example.com".into(),
        }));
        assert!(!whitelist.is_allowed(&Action::CreateDirectory {
            path: "/home/user/x".into(),
            parents: false,
            mode: None,
        }));
        assert!(!whitelist.is_allowed(&Action::SetHostname {
            name: "forja".into()
        }));
        assert!(!whitelist.is_allowed(&Action::SetScreenLevel { level: None }));
    }

    #[test]
    fn a_setting_needs_its_permit_and_a_value_the_tool_takes() {
        let mut config = WhitelistConfig::default();
        config.misc.set_hostname = true;
        config.misc.set_keyboard = true;
        config.misc.set_screen_level = true;
        let whitelist = Whitelist { config };
        assert!(whitelist.is_allowed(&Action::SetHostname {
            name: "forja".into()
        }));
        assert!(!whitelist.is_allowed(&Action::SetHostname {
            name: "--help".into()
        }));
        assert!(!whitelist.is_allowed(&Action::SetHostname {
            name: "Forja Nova".into()
        }));
        assert!(whitelist.is_allowed(&Action::SetKeyboard {
            layout: "br".into(),
            model: "abnt2".into()
        }));
        assert!(!whitelist.is_allowed(&Action::SetKeyboard {
            layout: "br; rm -rf /".into(),
            model: "".into()
        }));
        assert!(whitelist.is_allowed(&Action::SetScreenLevel { level: Some(2) }));
        assert!(!whitelist.is_allowed(&Action::SetScreenLevel { level: Some(3) }));
    }

    #[test]
    fn power_operations_are_always_denied() {
        let whitelist = Whitelist {
            config: sample_config(),
        };
        assert!(!whitelist.is_allowed(&Action::Reboot { delay_secs: 0 }));
        assert!(!whitelist.is_allowed(&Action::Shutdown { delay_secs: 0 }));
        assert!(!whitelist.is_allowed(&Action::Suspend));
    }

    #[test]
    fn run_command_matches_exact_command_and_positional_args() {
        let whitelist = Whitelist {
            config: sample_config(),
        };

        assert!(whitelist.is_allowed(&Action::RunCommand {
            cmd: "systemctl".into(),
            args: vec!["status".into(), "nginx".into()],
            cwd: None,
            env: vec![],
        }));
        assert!(!whitelist.is_allowed(&Action::RunCommand {
            cmd: "systemctl".into(),
            args: vec!["stop".into(), "nginx".into()],
            cwd: None,
            env: vec![],
        }));
        assert!(!whitelist.is_allowed(&Action::RunCommand {
            cmd: "systemctl".into(),
            args: vec!["status".into()],
            cwd: None,
            env: vec![],
        }));
    }

    #[test]
    fn run_command_prefix_bypass_is_closed() {
        // "iptables" must not match just because "ip" is allowed — this is
        // the exact bug the previous starts_with()-based matcher had.
        let whitelist = Whitelist {
            config: sample_config(),
        };
        assert!(!whitelist.is_allowed(&Action::RunCommand {
            cmd: "iptables".into(),
            args: vec!["addr".into()],
            cwd: None,
            env: vec![],
        }));
    }

    #[test]
    fn service_blocklist_wins_over_allowlist() {
        let whitelist = Whitelist {
            config: sample_config(),
        };
        // "nginx" is allowed and doesn't match "hive-*", so this passes...
        assert!(whitelist.is_allowed(&Action::RestartService {
            name: "nginx".into(),
        }));
        // ...but anything matching the blocklist is denied even if an
        // admin also (mistakenly) allowlisted it.
        let mut config = sample_config();
        config.service.allowed.insert("hive-cortex".into());
        let whitelist = Whitelist { config };
        assert!(!whitelist.is_allowed(&Action::RestartService {
            name: "hive-cortex".into(),
        }));
    }

    #[test]
    fn file_ops_require_an_allowed_path_and_no_blocked_path() {
        let config = WhitelistConfig {
            file_ops: FileOpsRule {
                allowed_paths: vec![GlobPattern("/home/*".into())],
                blocked_paths: vec![GlobPattern("/home/*/.ssh/*".into())],
            },
            ..Default::default()
        };
        let whitelist = Whitelist { config };

        assert!(whitelist.is_allowed(&Action::DeleteFile {
            path: "/home/user/notes.txt".into(),
            permanent: false,
        }));
        assert!(!whitelist.is_allowed(&Action::DeleteFile {
            path: "/home/user/.ssh/id_rsa".into(),
            permanent: true,
        }));
        assert!(!whitelist.is_allowed(&Action::DeleteFile {
            path: "/etc/passwd".into(),
            permanent: false,
        }));
    }
}
