//! Hive integration for the terminal.

use anyhow::{Context, Result};
use hive_common::ipc::IpcSocket;
use hive_common::messages::{AnonymousLevel, HiveMessage, ProcessInfo, Suggestion};
use hive_common::anonymous::{parse_anonymous_level, should_enter_anonymous};
use std::path::PathBuf;
use tokio::sync::mpsc;
use tracing::{debug, info, warn};

use crate::config::HiveConfig;

/// Events from Hive
#[derive(Debug)]
pub enum HiveEvent {
    /// Received a suggestion
    Suggestion(Suggestion),
    /// Connection established
    Connected,
    /// Connection lost
    Disconnected,
}

/// Hive integration manager
pub struct HiveIntegration {
    /// Socket connection to cortex
    socket: Option<IpcSocket>,
    /// Event sender
    event_tx: mpsc::Sender<HiveEvent>,
    /// Configuration
    config: HiveConfig,
    /// Current anonymous level
    anonymous_level: Option<AnonymousLevel>,
    /// Our process ID
    pid: u32,
}

impl HiveIntegration {
    /// Create a new Hive integration
    pub async fn new(
        config: HiveConfig,
        event_tx: mpsc::Sender<HiveEvent>,
    ) -> Result<Self> {
        let pid = std::process::id();

        // Check for anonymous mode from environment
        let anonymous_level = if should_enter_anonymous() {
            hive_common::anonymous::anonymous_level_from_env()
        } else if let Some(ref mode) = config.anonymous_mode {
            parse_anonymous_level(mode)
        } else {
            None
        };

        let mut integration = Self {
            socket: None,
            event_tx,
            config,
            anonymous_level,
            pid,
        };

        // Connect if enabled
        if integration.config.enabled {
            integration.connect().await?;
        }

        Ok(integration)
    }

    /// Connect to cortex
    async fn connect(&mut self) -> Result<()> {
        let socket_path = std::env::var("HIVE_CORTEX_SOCKET")
            .unwrap_or_else(|_| hive_common::CORTEX_SOCKET.to_string());

        match IpcSocket::connect(&socket_path).await {
            Ok(socket) => {
                info!("Connected to Hive cortex");
                self.socket = Some(socket);
                let _ = self.event_tx.send(HiveEvent::Connected).await;

                // Enter anonymous mode if configured
                if let Some(level) = self.anonymous_level {
                    self.enter_anonymous_mode(level).await?;
                }

                Ok(())
            }
            Err(e) => {
                warn!("Could not connect to Hive: {}", e);
                Ok(()) // Not a fatal error
            }
        }
    }

    /// Enter anonymous mode
    async fn enter_anonymous_mode(&mut self, level: AnonymousLevel) -> Result<()> {
        if let Some(ref mut socket) = self.socket {
            let msg = HiveMessage::AnonymousModeEnter {
                level,
                pid: Some(self.pid),
            };
            socket.send(&msg).await?;
            info!("Entered anonymous mode: {:?}", level);
        }
        self.anonymous_level = Some(level);
        Ok(())
    }

    /// Exit anonymous mode
    pub async fn exit_anonymous_mode(&mut self) -> Result<()> {
        if let Some(ref mut socket) = self.socket {
            let msg = HiveMessage::AnonymousModeExit {
                pid: Some(self.pid),
            };
            socket.send(&msg).await?;
            info!("Exited anonymous mode");
        }
        self.anonymous_level = None;
        Ok(())
    }

    /// Report a command execution
    pub async fn report_command(&mut self, cmd: &str, cwd: Option<PathBuf>) -> Result<()> {
        // Don't report if anonymous or disabled
        if self.anonymous_level.is_some() || !self.config.report_commands {
            return Ok(());
        }

        if let Some(ref mut socket) = self.socket {
            let process = ProcessInfo {
                pid: self.pid,
                uid: unsafe { libc::getuid() },
                name: "hive-term".to_string(),
                cmdline: vec![cmd.to_string()],
                cwd,
                ppid: Some(unsafe { libc::getppid() as u32 }),
            };

            let msg = HiveMessage::CommandObserved {
                process,
                cmd: cmd.to_string(),
                timestamp: chrono::Utc::now(),
            };

            if let Err(e) = socket.send(&msg).await {
                debug!("Failed to report command: {}", e);
            }
        }
        Ok(())
    }

    /// Request suggestions for current context
    pub async fn request_suggestions(&mut self, query: Option<String>) -> Result<()> {
        if let Some(ref mut socket) = self.socket {
            let context = hive_common::messages::Context {
                recent_commands: vec![],
                cwd: std::env::current_dir().ok(),
                active_services: vec![],
                recent_logs: vec![],
                resources: None,
                trigger: None,
            };

            let msg = HiveMessage::SuggestionRequest {
                request_id: uuid::Uuid::new_v4(),
                context,
                user_query: query,
                max_suggestions: 3,
            };

            socket.send(&msg).await?;
        }
        Ok(())
    }

    /// Process incoming messages
    pub async fn process_messages(&mut self) -> Result<()> {
        if let Some(ref mut socket) = self.socket {
            match socket.recv().await {
                Ok(msg) => {
                    self.handle_message(msg).await?;
                }
                Err(hive_common::ipc::IpcError::ConnectionClosed) => {
                    warn!("Hive connection closed");
                    self.socket = None;
                    let _ = self.event_tx.send(HiveEvent::Disconnected).await;
                }
                Err(e) => {
                    debug!("Error receiving message: {}", e);
                }
            }
        }
        Ok(())
    }

    /// Handle a message from cortex
    async fn handle_message(&mut self, msg: HiveMessage) -> Result<()> {
        match msg {
            HiveMessage::SuggestionResponse { suggestions, .. } => {
                for suggestion in suggestions {
                    let _ = self.event_tx.send(HiveEvent::Suggestion(suggestion)).await;
                }
            }
            HiveMessage::Notification { title, body, .. } => {
                // Could display inline in terminal
                debug!("Notification: {} - {}", title, body);
            }
            _ => {}
        }
        Ok(())
    }

    /// Check if connected
    pub fn is_connected(&self) -> bool {
        self.socket.is_some()
    }

    /// Get anonymous level
    pub fn anonymous_level(&self) -> Option<AnonymousLevel> {
        self.anonymous_level
    }

    /// Set anonymous level
    pub async fn set_anonymous_level(&mut self, level: Option<AnonymousLevel>) -> Result<()> {
        match (self.anonymous_level, level) {
            (Some(_), None) => {
                self.exit_anonymous_mode().await?;
            }
            (None, Some(l)) | (Some(_), Some(l)) => {
                self.enter_anonymous_mode(l).await?;
            }
            (None, None) => {}
        }
        Ok(())
    }
}

impl Drop for HiveIntegration {
    fn drop(&mut self) {
        // Try to exit anonymous mode on drop
        if self.anonymous_level.is_some() {
            // Can't do async in drop, but the session will be cleaned up
            // when the connection closes anyway
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_anonymous_level_parsing() {
        assert!(matches!(
            parse_anonymous_level("quiet"),
            Some(AnonymousLevel::Quiet)
        ));
        assert!(matches!(
            parse_anonymous_level("detach"),
            Some(AnonymousLevel::Detach)
        ));
        assert!(matches!(
            parse_anonymous_level("full"),
            Some(AnonymousLevel::Full)
        ));
    }
}
