//! The screen as a client of the Hive: hive-cortex's user socket, the same
//! handshake and the same messages as hive-dashboard, read on a thread.

use anyhow::{bail, Context as _, Result};
use hive_common::ipc::blocking::Connection;
use hive_common::ipc::IpcError;
use hive_common::messages::HiveMessage;
use std::sync::mpsc::{self, Receiver, RecvTimeoutError};
use std::time::Duration;

const HANDSHAKE: Duration = Duration::from_secs(5);

pub struct Hive {
    writer: Connection,
    pub incoming: Receiver<HiveMessage>,
}

impl Hive {
    /// Connects, pings, and waits for the pong that says cortex let us in:
    /// it closes the connection at once on a client it does not accept.
    pub fn connect(path: &str) -> Result<Hive> {
        let writer = Connection::connect(path)
            .with_context(|| format!("cannot reach hive-cortex at {} (is it running?)", path))?;
        let mut reader = writer.try_clone()?;
        let (tx, incoming) = mpsc::channel();
        std::thread::Builder::new()
            .name("hive".into())
            .spawn(move || loop {
                match reader.recv() {
                    Ok(msg) => {
                        if tx.send(msg).is_err() {
                            break;
                        }
                    }
                    Err(IpcError::ConnectionClosed) => break,
                    Err(e) => {
                        tracing::warn!("the Hive's connection failed: {}", e);
                        break;
                    }
                }
            })?;
        let mut hive = Hive { writer, incoming };
        hive.send(&HiveMessage::Ping {
            timestamp: chrono::Utc::now(),
        })?;
        let deadline = std::time::Instant::now() + HANDSHAKE;
        loop {
            let left = deadline.saturating_duration_since(std::time::Instant::now());
            match hive.incoming.recv_timeout(left) {
                Ok(HiveMessage::Pong { .. }) => return Ok(hive),
                Ok(_) => continue,
                Err(RecvTimeoutError::Timeout) => {
                    bail!("hive-cortex did not answer within {:?}", HANDSHAKE)
                }
                Err(RecvTimeoutError::Disconnected) => bail!(
                    "hive-cortex turned hive-screen away: approving the Hive's offers takes an \
                     administrator (root, or a member of sudo, admin or wheel)"
                ),
            }
        }
    }

    pub fn send(&mut self, msg: &HiveMessage) -> Result<()> {
        self.writer.send(msg).context("cannot send to hive-cortex")
    }
}
