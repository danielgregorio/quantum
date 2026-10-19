//! Hive Dock - Application Dock Bar
//!
//! Provides a dock/taskbar for launching applications and showing running apps.
//! Uses the Wayland layer-shell protocol for desktop integration.
//!
//! # Features
//!
//! - Pinned application shortcuts
//! - Running application indicators
//! - Click to launch or focus applications
//! - Auto-hide support
//! - Configurable position (bottom, top, left, right)

mod apps;
mod dock;
mod render;

use anyhow::{Context, Result};
use hive_common::config::Config;
use hive_common::ipc::IpcSocket;
use hive_common::messages::HiveMessage;
use std::path::Path;
use std::sync::Arc;
use std::time::Duration;
use tokio::signal;
use tokio::sync::RwLock;
use tracing::{error, info, warn};

use crate::apps::AppManager;
use crate::dock::{DockPosition, DockWindow};

/// Default socket path for cortex connection
const CORTEX_SOCKET: &str = "/run/hive/cortex.sock";

/// Default icon size in pixels
const DEFAULT_ICON_SIZE: u32 = 48;

/// Default pinned applications
const DEFAULT_PINNED: &[&str] = &[
    "org.mozilla.firefox",
    "org.gnome.Nautilus",
    "org.gnome.Terminal",
];

/// Dock configuration
#[derive(Debug, Clone)]
struct DockConfig {
    position: DockPosition,
    icon_size: u32,
    auto_hide: bool,
    pinned_apps: Vec<String>,
}

impl Default for DockConfig {
    fn default() -> Self {
        Self {
            position: DockPosition::Bottom,
            icon_size: DEFAULT_ICON_SIZE,
            auto_hide: false,
            pinned_apps: DEFAULT_PINNED.iter().map(|s| s.to_string()).collect(),
        }
    }
}

/// Dock state
struct DockState {
    app_manager: AppManager,
    dock_window: Option<DockWindow>,
    config: DockConfig,
    running_app_ids: Vec<String>,
}

impl DockState {
    fn new(config: DockConfig) -> Self {
        Self {
            app_manager: AppManager::new(),
            dock_window: None,
            config,
            running_app_ids: Vec::new(),
        }
    }

    fn update_dock(&mut self) -> Result<()> {
        if let Some(ref mut dock) = self.dock_window {
            let pinned: Vec<_> = self.config.pinned_apps
                .iter()
                .filter_map(|id| self.app_manager.get_app(id))
                .collect();

            let running: Vec<_> = self.running_app_ids
                .iter()
                .filter_map(|id| self.app_manager.get_app(id))
                .collect();

            dock.update(&pinned, &running)?;
        }
        Ok(())
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("hive_dock=info".parse()?),
        )
        .init();

    info!("Hive Dock starting...");

    // Load configuration
    let config = load_config().await?;

    // Initialize dock state
    let state = Arc::new(RwLock::new(DockState::new(config.clone())));

    // Scan for installed applications
    {
        let mut state_guard = state.write().await;
        if let Err(e) = state_guard.app_manager.scan_applications() {
            warn!("Failed to scan applications: {}", e);
        }

        // Set pinned apps from config
        state_guard.app_manager.set_pinned(config.pinned_apps.clone());

        info!("Found {} applications", state_guard.app_manager.get_visible_apps().len());
    }

    // Try to initialize Wayland dock window
    match DockWindow::new(config.position, config.icon_size) {
        Ok(dock) => {
            let mut state_guard = state.write().await;
            state_guard.dock_window = Some(dock);
            info!("Wayland dock window initialized");

            // Initial render
            if let Err(e) = state_guard.update_dock() {
                error!("Failed to update dock: {}", e);
            }
        }
        Err(e) => {
            warn!("Could not initialize Wayland dock: {}. Running in headless mode.", e);
        }
    }

    // Connect to cortex
    let cortex_socket = std::env::var("HIVE_CORTEX_SOCKET")
        .unwrap_or_else(|_| CORTEX_SOCKET.to_string());

    info!("Connecting to cortex at {}", cortex_socket);
    let mut cortex = match IpcSocket::connect(&cortex_socket).await {
        Ok(socket) => {
            info!("Connected to cortex");
            Some(socket)
        }
        Err(e) => {
            warn!("Could not connect to cortex: {}. Running standalone.", e);
            None
        }
    };

    // Create interval for app rescan
    let mut rescan_interval = tokio::time::interval(Duration::from_secs(60));

    info!("Hive Dock ready");

    // Main event loop
    loop {
        tokio::select! {
            // Handle messages from cortex if connected
            result = async {
                match &mut cortex {
                    Some(ref mut c) => Some(c.recv().await),
                    None => {
                        // No cortex connection, just wait
                        std::future::pending::<Option<Result<HiveMessage, hive_common::ipc::IpcError>>>().await
                    }
                }
            } => {
                if let Some(result) = result {
                    match result {
                        Ok(msg) => {
                            if let Err(e) = handle_message(msg, &state).await {
                                error!("Error handling message: {}", e);
                            }
                        }
                        Err(hive_common::ipc::IpcError::ConnectionClosed) => {
                            warn!("Connection to cortex closed");
                            cortex = None;
                        }
                        Err(e) => {
                            error!("Error receiving message: {}", e);
                        }
                    }
                }
            }
            // Periodic app rescan
            _ = rescan_interval.tick() => {
                let mut state_guard = state.write().await;
                if let Err(e) = state_guard.app_manager.scan_applications() {
                    warn!("Failed to rescan applications: {}", e);
                }
            }
            // Handle shutdown
            _ = signal::ctrl_c() => {
                info!("Received shutdown signal");
                break;
            }
        }
    }

    info!("Hive Dock shutting down");
    Ok(())
}

async fn load_config() -> Result<DockConfig> {
    let config_path = std::env::var("HIVE_CONFIG")
        .unwrap_or_else(|_| "/etc/hive/config.toml".to_string());

    if Path::new(&config_path).exists() {
        // Could extend Config to include dock settings
        // For now, use defaults
        info!("Using default dock configuration");
    }

    Ok(DockConfig::default())
}

async fn handle_message(msg: HiveMessage, state: &Arc<RwLock<DockState>>) -> Result<()> {
    match msg {
        HiveMessage::Notification { title, body, .. } => {
            // Could show notification badge on dock
            info!("Received notification: {} - {}", title, body);
        }

        _ => {
            // Ignore other message types
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = DockConfig::default();
        assert_eq!(config.position, DockPosition::Bottom);
        assert_eq!(config.icon_size, 48);
        assert!(!config.pinned_apps.is_empty());
    }
}
