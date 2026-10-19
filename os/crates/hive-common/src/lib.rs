//! # hive-common
//!
//! Shared types, messages, and utilities for the DruidOS Hive Stack.
//!
//! This crate provides:
//! - [`messages`]: Inter-process communication message types
//! - [`actions`]: Executable actions for the actuator
//! - [`config`]: Configuration loading and structures
//! - [`ipc`]: Unix socket IPC helpers
//! - [`logging`]: tracing setup shared by the Hive binaries
//! - [`systemd`]: readiness notification for the `Type=notify` units
//! - [`zfs`]: finding the system's ZFS dataset and snapshotting it
//!
//! ## Architecture
//!
//! The Hive Stack uses typed messages for all communication:
//!
//! ```text
//! ┌─────────────────┐     ┌─────────────────┐
//! │  hive-nerve-*   │────▶│   hive-cortex   │
//! │   (observers)   │     │  (orchestrator) │
//! └─────────────────┘     └────────┬────────┘
//!                                  │
//!                    ┌─────────────┼─────────────┐
//!                    ▼             ▼             ▼
//!             ┌──────────┐  ┌──────────┐  ┌──────────┐
//!             │  synapse │  │ actuator │  │  shell   │
//!             │  (SLM)   │  │ (actions)│  │  (UI)    │
//!             └──────────┘  └──────────┘  └──────────┘
//! ```

pub mod actions;
pub mod anonymous;
pub mod config;
pub mod events;
pub mod ipc;
pub mod logging;
pub mod messages;
pub mod systemd;
pub mod zfs;

// Re-exports for convenience
pub use actions::{Action, ActionResult};
pub use anonymous::{AnonymousManager, AnonymousSession};
pub use config::Config;
pub use ipc::IpcSocket;
pub use messages::{AnonymousLevel, HiveMessage, Severity, Suggestion};

/// Crate version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Default socket path for cortex
pub const CORTEX_SOCKET: &str = "/run/hive/cortex.sock";

/// hive-cortex's socket for users (grove): open to every local user, and
/// only accepting user messages - questions and anonymous mode for the
/// connecting process itself. `HIVE_USER_SOCKET` overrides it.
pub const USER_SOCKET: &str = "/run/hive/user.sock";

/// Default configuration path
pub const CONFIG_PATH: &str = "/etc/hive/config.toml";

/// User-specific config directory
pub fn user_config_dir() -> Option<std::path::PathBuf> {
    dirs::config_dir().map(|p| p.join("hive"))
}

/// User-specific data directory (knowledge base, etc.)
pub fn user_data_dir() -> Option<std::path::PathBuf> {
    dirs::data_dir().map(|p| p.join("hive"))
}
