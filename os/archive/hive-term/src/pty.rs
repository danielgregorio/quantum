//! PTY (pseudo-terminal) handling.

use anyhow::{Context, Result};
use portable_pty::{native_pty_system, CommandBuilder, PtyPair, PtySize};
use std::io::{Read, Write};
use std::sync::Arc;
use tokio::sync::mpsc;
use tracing::{debug, error, info};

use crate::config::TermConfig;

/// PTY event
#[derive(Debug)]
pub enum PtyEvent {
    /// Data received from PTY
    Data(Vec<u8>),
    /// PTY closed
    Closed,
    /// Error occurred
    Error(String),
}

/// PTY command
#[derive(Debug)]
pub enum PtyCommand {
    /// Write data to PTY
    Write(Vec<u8>),
    /// Resize PTY
    Resize { cols: u16, rows: u16 },
    /// Close PTY
    Close,
}

/// Manages the pseudo-terminal
pub struct PtyManager {
    /// Command sender for PTY operations
    cmd_tx: mpsc::Sender<PtyCommand>,
    /// Current size
    size: PtySize,
}

impl PtyManager {
    /// Create a new PTY manager and spawn the shell
    pub fn new(
        config: &TermConfig,
        event_tx: mpsc::Sender<PtyEvent>,
    ) -> Result<Self> {
        let pty_system = native_pty_system();

        let size = PtySize {
            rows: config.window.rows,
            cols: config.window.columns,
            pixel_width: 0,
            pixel_height: 0,
        };

        // Create PTY pair
        let pair = pty_system
            .openpty(size)
            .context("Failed to create PTY")?;

        // Build command
        let shell = config.shell.program.clone()
            .or_else(|| std::env::var("SHELL").ok())
            .unwrap_or_else(|| "/bin/sh".to_string());

        let mut cmd = CommandBuilder::new(&shell);
        for arg in &config.shell.args {
            cmd.arg(arg);
        }

        if let Some(ref cwd) = config.shell.working_directory {
            cmd.cwd(cwd);
        }

        for (key, value) in &config.shell.env {
            cmd.env(key, value);
        }

        // Set TERM
        cmd.env("TERM", "xterm-256color");

        // Spawn the shell
        let mut child = pair
            .slave
            .spawn_command(cmd)
            .context("Failed to spawn shell")?;

        info!("Spawned shell: {}", shell);

        // Create command channel
        let (cmd_tx, cmd_rx) = mpsc::channel::<PtyCommand>(100);

        // Spawn reader thread
        let reader = pair.master.try_clone_reader()
            .context("Failed to clone PTY reader")?;
        let event_tx_clone = event_tx.clone();
        std::thread::spawn(move || {
            Self::read_loop(reader, event_tx_clone);
        });

        // Spawn writer thread
        let writer = pair.master.take_writer()
            .context("Failed to get PTY writer")?;
        let master = pair.master;
        std::thread::spawn(move || {
            Self::write_loop(writer, master, cmd_rx);
        });

        // Spawn child watcher
        std::thread::spawn(move || {
            let _ = child.wait();
            let _ = event_tx.blocking_send(PtyEvent::Closed);
        });

        Ok(Self {
            cmd_tx,
            size,
        })
    }

    /// Read loop for PTY output
    fn read_loop(
        mut reader: Box<dyn Read + Send>,
        event_tx: mpsc::Sender<PtyEvent>,
    ) {
        let mut buf = [0u8; 4096];
        loop {
            match reader.read(&mut buf) {
                Ok(0) => {
                    debug!("PTY reader EOF");
                    let _ = event_tx.blocking_send(PtyEvent::Closed);
                    break;
                }
                Ok(n) => {
                    let data = buf[..n].to_vec();
                    if event_tx.blocking_send(PtyEvent::Data(data)).is_err() {
                        break;
                    }
                }
                Err(e) => {
                    error!("PTY read error: {}", e);
                    let _ = event_tx.blocking_send(PtyEvent::Error(e.to_string()));
                    break;
                }
            }
        }
    }

    /// Write loop for PTY input
    fn write_loop(
        mut writer: Box<dyn Write + Send>,
        master: Box<dyn portable_pty::MasterPty + Send>,
        mut cmd_rx: mpsc::Receiver<PtyCommand>,
    ) {
        while let Some(cmd) = cmd_rx.blocking_recv() {
            match cmd {
                PtyCommand::Write(data) => {
                    if let Err(e) = writer.write_all(&data) {
                        error!("PTY write error: {}", e);
                        break;
                    }
                    let _ = writer.flush();
                }
                PtyCommand::Resize { cols, rows } => {
                    let size = PtySize {
                        rows,
                        cols,
                        pixel_width: 0,
                        pixel_height: 0,
                    };
                    if let Err(e) = master.resize(size) {
                        error!("PTY resize error: {}", e);
                    }
                }
                PtyCommand::Close => {
                    debug!("PTY close requested");
                    break;
                }
            }
        }
    }

    /// Write data to the PTY
    pub async fn write(&self, data: Vec<u8>) -> Result<()> {
        self.cmd_tx
            .send(PtyCommand::Write(data))
            .await
            .context("Failed to send write command")?;
        Ok(())
    }

    /// Resize the PTY
    pub async fn resize(&mut self, cols: u16, rows: u16) -> Result<()> {
        self.size.cols = cols;
        self.size.rows = rows;
        self.cmd_tx
            .send(PtyCommand::Resize { cols, rows })
            .await
            .context("Failed to send resize command")?;
        Ok(())
    }

    /// Close the PTY
    pub async fn close(&self) -> Result<()> {
        self.cmd_tx
            .send(PtyCommand::Close)
            .await
            .context("Failed to send close command")?;
        Ok(())
    }

    /// Get current size
    pub fn size(&self) -> (u16, u16) {
        (self.size.cols, self.size.rows)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pty_size() {
        let size = PtySize {
            rows: 24,
            cols: 80,
            pixel_width: 0,
            pixel_height: 0,
        };
        assert_eq!(size.rows, 24);
        assert_eq!(size.cols, 80);
    }
}
