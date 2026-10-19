//! Hive Shell - Layer-shell Overlay
//!
//! Provides a desktop overlay for showing Hive suggestions, notifications,
//! and system alerts using the Wayland layer-shell protocol.
//!
//! # Features
//!
//! - Notification popups for Hive suggestions
//! - System alert overlays
//! - Keyboard shortcuts for interacting with suggestions
//! - Transparent overlay that doesn't block input

mod overlay;
mod render;

use anyhow::{Context, Result};
use hive_common::config::Config;
use hive_common::ipc::IpcSocket;
use hive_common::messages::{HiveMessage, Suggestion};
use std::collections::VecDeque;
use std::path::Path;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::signal;
use tokio::sync::RwLock;
use tracing::{error, info, warn};

use crate::overlay::OverlayWindow;

/// Default socket path for cortex connection
const CORTEX_SOCKET: &str = "/run/hive/cortex.sock";

/// Maximum notifications to show at once
const MAX_VISIBLE_NOTIFICATIONS: usize = 5;

/// How long notifications stay visible (seconds)
const NOTIFICATION_TIMEOUT_SECS: u64 = 10;

/// A queued notification
struct Notification {
    suggestion: Suggestion,
    shown_at: Instant,
}

/// Shell state
struct ShellState {
    notifications: VecDeque<Notification>,
    overlay: Option<OverlayWindow>,
}

impl ShellState {
    fn new() -> Self {
        Self {
            notifications: VecDeque::new(),
            overlay: None,
        }
    }

    fn add_notification(&mut self, suggestion: Suggestion) {
        // Remove oldest if at capacity
        while self.notifications.len() >= MAX_VISIBLE_NOTIFICATIONS {
            self.notifications.pop_front();
        }

        self.notifications.push_back(Notification {
            suggestion,
            shown_at: Instant::now(),
        });
    }

    fn expire_old_notifications(&mut self) {
        let timeout = Duration::from_secs(NOTIFICATION_TIMEOUT_SECS);
        self.notifications
            .retain(|n| n.shown_at.elapsed() < timeout);
    }

    fn get_visible_suggestions(&self) -> Vec<Suggestion> {
        self.notifications.iter().map(|n| n.suggestion.clone()).collect()
    }

    fn update_overlay(&mut self) -> Result<()> {
        if let Some(ref mut overlay) = self.overlay {
            let suggestions: Vec<Suggestion> = self.notifications.iter().map(|n| n.suggestion.clone()).collect();
            let refs: Vec<&Suggestion> = suggestions.iter().collect();
            overlay.update(&refs)?;
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
                .add_directive("hive_shell=info".parse()?),
        )
        .init();

    info!("Hive Shell starting...");

    // Load configuration
    let config = load_config().await?;

    // Initialize shell state
    let state = Arc::new(RwLock::new(ShellState::new()));

    // Try to initialize Wayland overlay
    match OverlayWindow::new() {
        Ok(overlay) => {
            let mut state_guard = state.write().await;
            state_guard.overlay = Some(overlay);
            info!("Wayland overlay initialized");
        }
        Err(e) => {
            warn!("Could not initialize Wayland overlay: {}. Running in headless mode.", e);
        }
    }

    // Connect to cortex
    let cortex_socket = std::env::var("HIVE_CORTEX_SOCKET")
        .unwrap_or_else(|_| CORTEX_SOCKET.to_string());

    info!("Connecting to cortex at {}", cortex_socket);
    let mut cortex = IpcSocket::connect(&cortex_socket)
        .await
        .context("Failed to connect to cortex")?;

    info!("Hive Shell ready");

    // Create a timer for expiring old notifications
    let mut expire_interval = tokio::time::interval(Duration::from_secs(1));

    // Main event loop
    loop {
        tokio::select! {
            result = cortex.recv() => {
                match result {
                    Ok(msg) => {
                        if let Err(e) = handle_message(msg, &state).await {
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
            _ = expire_interval.tick() => {
                let mut state_guard = state.write().await;
                state_guard.expire_old_notifications();

                // Update overlay if we have one
                if let Err(e) = state_guard.update_overlay() {
                    error!("Failed to update overlay: {}", e);
                }
            }
            _ = signal::ctrl_c() => {
                info!("Received shutdown signal");
                break;
            }
        }
    }

    info!("Hive Shell shutting down");
    Ok(())
}

async fn load_config() -> Result<Config> {
    let config_path = std::env::var("HIVE_CONFIG")
        .unwrap_or_else(|_| "/etc/hive/config.toml".to_string());

    if Path::new(&config_path).exists() {
        Config::load(&config_path)
    } else {
        warn!("Config file not found, using defaults");
        Ok(Config::default())
    }
}

async fn handle_message(msg: HiveMessage, state: &Arc<RwLock<ShellState>>) -> Result<()> {
    match msg {
        HiveMessage::SuggestionResponse {
            suggestions,
            processing_time_ms,
            ..
        } => {
            info!(
                "Received {} suggestions (processed in {}ms)",
                suggestions.len(),
                processing_time_ms
            );

            let mut state_guard = state.write().await;
            for suggestion in suggestions {
                state_guard.add_notification(suggestion);
            }

            // Update overlay
            state_guard.update_overlay()?;
        }

        HiveMessage::Notification {
            title,
            body,
            severity,
            ..
        } => {
            info!("Received notification: {} - {}", title, body);

            // Create a suggestion-like notification
            let suggestion = Suggestion {
                id: 0,
                title,
                description: body,
                action: None,
                learn_more: None,
                confidence: match severity {
                    hive_common::messages::Severity::Critical => 1.0,
                    hive_common::messages::Severity::Error => 0.9,
                    hive_common::messages::Severity::Warning => 0.7,
                    hive_common::messages::Severity::Notice => 0.5,
                    hive_common::messages::Severity::Info => 0.3,
                },
            };

            let mut state_guard = state.write().await;
            state_guard.add_notification(suggestion);

            state_guard.update_overlay()?;
        }

        _ => {
            // Ignore other message types
        }
    }

    Ok(())
}
