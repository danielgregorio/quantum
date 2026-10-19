//! Configuration loading and structures for Hive components.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

/// Main configuration for all Hive components
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Config {
    /// General settings
    #[serde(default)]
    pub general: GeneralConfig,

    /// Cortex (orchestrator) settings
    #[serde(default)]
    pub cortex: CortexConfig,

    /// Synapse (SLM) settings
    #[serde(default)]
    pub synapse: SynapseConfig,

    /// Actuator settings
    #[serde(default)]
    pub actuator: ActuatorConfig,

    /// Housekeeping of the Hive's ZFS safety snapshots
    #[serde(default)]
    pub zfs: ZfsConfig,

    /// Shell/UI settings
    #[serde(default)]
    pub shell: ShellConfig,

    /// Nerve (observer) settings
    #[serde(default)]
    pub nerves: NervesConfig,
}

impl Config {
    /// Load configuration from the default path
    pub fn load_default() -> Result<Self> {
        let path = Path::new(crate::CONFIG_PATH);
        if path.exists() {
            Self::load(path)
        } else {
            Ok(Self::default())
        }
    }

    /// Load configuration from a specific path
    pub fn load<P: AsRef<Path>>(path: P) -> Result<Self> {
        let path = path.as_ref();
        let content = std::fs::read_to_string(path)
            .with_context(|| format!("Failed to read config from {:?}", path))?;

        toml::from_str(&content).with_context(|| format!("Failed to parse config from {:?}", path))
    }

    /// Load with user overrides
    ///
    /// Loads system config first, then merges user-specific overrides
    pub fn load_with_user_overrides() -> Result<Self> {
        let mut config = Self::load_default()?;

        if let Some(user_dir) = crate::user_config_dir() {
            let user_config = user_dir.join("config.toml");
            if user_config.exists() {
                let user = Self::load(&user_config)?;
                config.merge(user);
            }
        }

        Ok(config)
    }

    /// Merge another config into this one (other takes precedence)
    pub fn merge(&mut self, other: Config) {
        // Merge general settings
        if other.general.log_level.is_some() {
            self.general.log_level = other.general.log_level;
        }
        self.general.anonymous_mode = other.general.anonymous_mode;

        // Merge synapse settings
        if other.synapse.model_path.is_some() {
            self.synapse.model_path = other.synapse.model_path;
        }

        // Merge shell settings
        self.shell.notifications_enabled = other.shell.notifications_enabled;
        self.shell.theme = other.shell.theme;
    }

    /// Save configuration to a file
    pub fn save<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let content = toml::to_string_pretty(self)?;
        std::fs::write(path.as_ref(), content)?;
        Ok(())
    }
}

/// General settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneralConfig {
    /// Log level (trace, debug, info, warn, error)
    pub log_level: Option<String>,

    /// Global anonymous mode
    #[serde(default)]
    pub anonymous_mode: bool,

    /// Data directory for knowledge base, etc.
    pub data_dir: Option<PathBuf>,
}

impl Default for GeneralConfig {
    fn default() -> Self {
        Self {
            log_level: Some("info".into()),
            anonymous_mode: false,
            data_dir: None,
        }
    }
}

/// Cortex orchestrator settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CortexConfig {
    /// Socket path
    pub socket_path: PathBuf,

    /// Maximum concurrent connections
    pub max_connections: u32,

    /// User to run as (for privilege dropping)
    pub user: Option<String>,

    /// Group to run as
    pub group: Option<String>,
}

impl Default for CortexConfig {
    fn default() -> Self {
        Self {
            socket_path: PathBuf::from("/run/hive/cortex.sock"),
            max_connections: 100,
            user: Some("root".into()),
            group: Some("hive".into()),
        }
    }
}

/// Synapse SLM settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SynapseConfig {
    /// Path to the SLM model file (GGUF)
    pub model_path: Option<PathBuf>,

    /// Path to the model's tokenizer.json (defaults to the one shipped
    /// next to the production model)
    #[serde(default)]
    pub tokenizer_path: Option<PathBuf>,

    /// Model name (for downloading)
    pub model_name: String,

    /// Context window size
    pub context_size: u32,

    /// Maximum tokens to generate
    pub max_tokens: u32,

    /// Temperature for generation
    pub temperature: f32,

    /// Whether to preload the model at startup
    pub preload: bool,

    /// Memory limit in MB
    pub memory_limit_mb: u32,

    /// User to run as
    pub user: String,

    /// Inference backend: "candle" (default — the local GGUF model; falls
    /// back to the mock if the model files are missing), "mock" (canned
    /// responses) or "ollama" (dev/test only, talks to a remote Ollama
    /// server; see hive-synapse's inference module docs). Production
    /// deployments should never use "ollama" — and hive-synapse.service's
    /// `PrivateNetwork=yes` blocks the network at the OS level even if
    /// it were misconfigured.
    #[serde(default = "default_synapse_backend")]
    pub backend: String,

    /// Base URL for the Ollama backend, e.g. "http://10.10.1.125:11434".
    /// Only read when `backend = "ollama"`.
    #[serde(default)]
    pub ollama_url: Option<String>,

    /// Ollama model name to request, e.g. "qwen2.5:7b". Only read when
    /// `backend = "ollama"`.
    #[serde(default)]
    pub ollama_model: Option<String>,

    /// The Hive's rules: what synapse offers on an event, written by Quantum
    /// from config/hive/hive.q (config/hive/rules.toml). When the file is
    /// missing, the rules this build was made with are used.
    #[serde(default = "default_rules_path")]
    pub rules_path: PathBuf,
}

fn default_synapse_backend() -> String {
    "candle".to_string()
}

fn default_rules_path() -> PathBuf {
    PathBuf::from("/etc/hive/rules.toml")
}

impl Default for SynapseConfig {
    fn default() -> Self {
        Self {
            model_path: None,
            tokenizer_path: None,
            model_name: "Qwen/Qwen2.5-0.5B-Instruct-GGUF".into(),
            context_size: 2048,
            max_tokens: 128,
            temperature: 0.7,
            preload: false,
            memory_limit_mb: 512,
            user: "_hive-ai".into(),
            backend: default_synapse_backend(),
            ollama_url: None,
            ollama_model: None,
            rules_path: default_rules_path(),
        }
    }
}

/// Actuator settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActuatorConfig {
    /// Path to whitelist configuration
    pub whitelist_path: PathBuf,

    /// Rate limit (actions per minute)
    pub rate_limit: u32,

    /// Whether dangerous actions require confirmation
    pub confirm_dangerous: bool,

    /// User to run as
    pub user: String,

    /// Auto-snapshot before dangerous operations
    pub auto_snapshot: bool,

    /// ZFS dataset to snapshot. Unset (the default) means the datasets the
    /// system is mounted from - `/` and `/boot` - whatever the installer
    /// named them (see [`crate::zfs::system_datasets`]).
    #[serde(default)]
    pub snapshot_dataset: Option<String>,
}

impl Default for ActuatorConfig {
    fn default() -> Self {
        Self {
            whitelist_path: PathBuf::from("/etc/hive/whitelist.toml"),
            rate_limit: 30,
            confirm_dangerous: true,
            user: "_hive-act".into(),
            auto_snapshot: true,
            snapshot_dataset: None,
        }
    }
}

/// Housekeeping of the Hive's ZFS safety snapshots (`hive-zfs prune`, run
/// daily by `hive-zfs-prune.timer`).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct ZfsConfig {
    /// Prune a Hive snapshot once it is this many days old...
    pub prune_after_days: u32,

    /// ...except for this many of the newest, whatever their age, so there
    /// is always a recent point to roll back to.
    pub keep_newest: u32,
}

impl Default for ZfsConfig {
    fn default() -> Self {
        Self {
            prune_after_days: 14,
            keep_newest: 3,
        }
    }
}

/// Shell/UI settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShellConfig {
    /// Whether to show notifications
    pub notifications_enabled: bool,

    /// Notification timeout in seconds (0 = no timeout)
    pub notification_timeout: u32,

    /// Theme name
    pub theme: String,

    /// Position of the overlay
    pub overlay_position: OverlayPosition,

    /// Whether to show the dock
    pub dock_enabled: bool,

    /// Dock position
    pub dock_position: DockPosition,
}

impl Default for ShellConfig {
    fn default() -> Self {
        Self {
            notifications_enabled: true,
            notification_timeout: 10,
            theme: "default".into(),
            overlay_position: OverlayPosition::TopRight,
            dock_enabled: true,
            dock_position: DockPosition::Bottom,
        }
    }
}

/// Overlay position
#[derive(Debug, Clone, Copy, Serialize, Deserialize, Default)]
pub enum OverlayPosition {
    TopLeft,
    #[default]
    TopRight,
    BottomLeft,
    BottomRight,
}

/// Dock position
#[derive(Debug, Clone, Copy, Serialize, Deserialize, Default)]
pub enum DockPosition {
    Left,
    Right,
    Top,
    #[default]
    Bottom,
}

/// Nerve observer settings
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct NervesConfig {
    /// Process observer settings
    #[serde(default)]
    pub process: ProcessNerveConfig,

    /// Journal observer settings
    #[serde(default)]
    pub journal: JournalNerveConfig,

    /// Network observer settings
    #[serde(default)]
    pub network: NetworkNerveConfig,

    /// Filesystem observer settings
    #[serde(default)]
    pub filesystem: FilesystemNerveConfig,
}

/// Process observer config
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessNerveConfig {
    /// Whether to intercept commands
    pub intercept_enabled: bool,

    /// Commands to always intercept
    pub intercept_commands: Vec<String>,

    /// User to run as
    pub user: String,
}

impl Default for ProcessNerveConfig {
    fn default() -> Self {
        Self {
            intercept_enabled: true,
            intercept_commands: vec![
                "rm".into(),
                "chmod".into(),
                "chown".into(),
                "dd".into(),
                "mkfs".into(),
            ],
            user: "_hive-sense".into(),
        }
    }
}

/// Journal observer config
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JournalNerveConfig {
    /// Minimum priority to report (0-7, lower = more severe)
    pub min_priority: u8,

    /// Services to watch (empty = all)
    pub watch_services: Vec<String>,

    /// User to run as
    pub user: String,
}

impl Default for JournalNerveConfig {
    fn default() -> Self {
        Self {
            min_priority: 4, // warning and above
            watch_services: vec![],
            user: "_hive-sense".into(),
        }
    }
}

/// Network observer config
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkNerveConfig {
    /// Only report port conflicts on these ports; empty means every port.
    /// (A service failing to bind its port is worth knowing about whichever
    /// port it is, so the default is empty.)
    #[serde(default)]
    pub watch_ports: Vec<u16>,

    /// User to run as
    pub user: String,
}

impl Default for NetworkNerveConfig {
    fn default() -> Self {
        Self {
            watch_ports: vec![],
            user: "_hive-sense".into(),
        }
    }
}

/// Filesystem observer config
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FilesystemNerveConfig {
    /// Directories to watch
    pub watch_paths: Vec<PathBuf>,

    /// Patterns to ignore
    pub ignore_patterns: Vec<String>,

    /// User to run as
    pub user: String,
}

impl Default for FilesystemNerveConfig {
    fn default() -> Self {
        Self {
            watch_paths: vec![PathBuf::from("/etc"), PathBuf::from("/home")],
            ignore_patterns: vec!["*.swp".into(), "*.tmp".into(), "*~".into()],
            user: "_hive-sense".into(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = Config::default();
        assert!(!config.general.anonymous_mode);
        assert!(config.shell.notifications_enabled);
    }

    #[test]
    fn test_config_serialization() {
        let config = Config::default();
        let toml = toml::to_string(&config).unwrap();
        let parsed: Config = toml::from_str(&toml).unwrap();
        assert_eq!(parsed.synapse.model_name, config.synapse.model_name);
    }
}
