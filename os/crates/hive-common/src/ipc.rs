//! Unix socket IPC helpers for Hive components.
//!
//! Provides a simple async interface for sending and receiving
//! [`HiveMessage`]s over Unix domain sockets.

use crate::messages::HiveMessage;
use std::io;
use std::path::Path;
use thiserror::Error;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{UnixListener, UnixStream};

/// IPC-related errors
#[derive(Debug, Error)]
pub enum IpcError {
    #[error("IO error: {0}")]
    Io(#[from] io::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] bincode::Error),

    #[error("System error: {0}")]
    Nix(#[from] nix::Error),

    #[error("Connection closed")]
    ConnectionClosed,

    #[error("Message too large: {size} bytes (max: {max})")]
    MessageTooLarge { size: usize, max: usize },

    #[error("Invalid message format")]
    InvalidFormat,
}

/// Maximum message size (1 MB)
pub const MAX_MESSAGE_SIZE: usize = 1024 * 1024;

/// A connected IPC socket for sending/receiving messages
pub struct IpcSocket {
    stream: UnixStream,
}

impl IpcSocket {
    /// Connect to a socket at the given path
    pub async fn connect<P: AsRef<Path>>(path: P) -> Result<Self, IpcError> {
        let stream = UnixStream::connect(path).await?;
        Ok(Self { stream })
    }

    /// Create from an existing stream
    pub fn from_stream(stream: UnixStream) -> Self {
        Self { stream }
    }

    /// Send a message
    ///
    /// Wire format:
    /// - 4 bytes: message length (u32, little-endian)
    /// - N bytes: bincode-encoded message
    pub async fn send(&mut self, msg: &HiveMessage) -> Result<(), IpcError> {
        let encoded = msg.encode()?;

        if encoded.len() > MAX_MESSAGE_SIZE {
            return Err(IpcError::MessageTooLarge {
                size: encoded.len(),
                max: MAX_MESSAGE_SIZE,
            });
        }

        let len = encoded.len() as u32;
        self.stream.write_all(&len.to_le_bytes()).await?;
        self.stream.write_all(&encoded).await?;
        self.stream.flush().await?;

        Ok(())
    }

    /// Receive a message
    pub async fn recv(&mut self) -> Result<HiveMessage, IpcError> {
        // Read length prefix
        let mut len_buf = [0u8; 4];
        match self.stream.read_exact(&mut len_buf).await {
            Ok(_) => {}
            Err(e) if e.kind() == io::ErrorKind::UnexpectedEof => {
                return Err(IpcError::ConnectionClosed);
            }
            Err(e) => return Err(e.into()),
        }

        let len = u32::from_le_bytes(len_buf) as usize;

        if len > MAX_MESSAGE_SIZE {
            return Err(IpcError::MessageTooLarge {
                size: len,
                max: MAX_MESSAGE_SIZE,
            });
        }

        // Read message body
        let mut buf = vec![0u8; len];
        self.stream.read_exact(&mut buf).await?;

        HiveMessage::decode(&buf).map_err(IpcError::from)
    }

    /// Get peer credentials (uid, gid, pid)
    ///
    /// This is used for authenticating connections.
    #[cfg(target_os = "linux")]
    pub fn peer_credentials(&self) -> Result<PeerCredentials, IpcError> {
        use std::os::fd::AsFd;

        let cred = nix::sys::socket::getsockopt(
            &self.stream.as_fd(),
            nix::sys::socket::sockopt::PeerCredentials,
        )?;

        Ok(PeerCredentials {
            uid: cred.uid(),
            gid: cred.gid(),
            pid: cred.pid(),
        })
    }

    #[cfg(not(target_os = "linux"))]
    pub fn peer_credentials(&self) -> Result<PeerCredentials, IpcError> {
        // Fallback for non-Linux systems
        Ok(PeerCredentials {
            uid: 0,
            gid: 0,
            pid: 0,
        })
    }
}

/// Credentials of the peer process
#[derive(Debug, Clone, Copy)]
pub struct PeerCredentials {
    pub uid: u32,
    pub gid: u32,
    pub pid: i32,
}

/// An IPC server that accepts connections
pub struct IpcServer {
    listener: UnixListener,
}

impl IpcServer {
    /// Create a new server listening on the given path, for the Hive's own
    /// components: mode 0660, group `hive`.
    ///
    /// Removes any existing socket file first.
    pub async fn bind<P: AsRef<Path>>(path: P) -> Result<Self, IpcError> {
        Self::bind_with_access(path, 0o660, Some("hive")).await
    }

    /// Create a server any local user can connect to (mode 0666, the
    /// creator's group) - for sockets whose handler authorizes each message
    /// by the peer's credentials instead (hive-cortex's user socket).
    pub async fn bind_for_all_users<P: AsRef<Path>>(path: P) -> Result<Self, IpcError> {
        Self::bind_with_access(path, 0o666, None).await
    }

    async fn bind_with_access<P: AsRef<Path>>(
        path: P,
        mode: u32,
        group: Option<&str>,
    ) -> Result<Self, IpcError> {
        let path = path.as_ref();

        // Remove existing socket if present
        if path.exists() {
            std::fs::remove_file(path)?;
        }

        // Create parent directory if needed
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        let listener = UnixListener::bind(path)?;

        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(path, std::fs::Permissions::from_mode(mode))?;
        }

        // A group mode only grants access to whichever group the socket
        // happens to be created with — by default that's the creating
        // process's effective gid, which is only "hive" if the caller was
        // launched with `Group=hive` (e.g. via systemd). Set it explicitly so
        // a bare `hive-cortex` (run as plain root, no Group= directive) still
        // produces a socket the other Hive components can actually connect to.
        #[cfg(unix)]
        if let Some(group) = group {
            match nix::unistd::Group::from_name(group) {
                Ok(Some(group)) => {
                    if let Err(e) = nix::unistd::chown(path, None, Some(group.gid)) {
                        tracing::warn!(
                            "Failed to set 'hive' group ownership on {}: {e} \
                             (non-root components may fail to connect)",
                            path.display()
                        );
                    }
                }
                Ok(None) => {
                    tracing::warn!(
                        "Group 'hive' does not exist; leaving {} with its default group \
                         (fine for single-user dev/test, but non-root Hive components \
                         will get Permission denied in a privilege-separated deployment)",
                        path.display()
                    );
                }
                Err(e) => {
                    tracing::warn!("Failed to look up group 'hive': {e}");
                }
            }
        }

        Ok(Self { listener })
    }

    /// Accept a new connection
    pub async fn accept(&self) -> Result<IpcSocket, IpcError> {
        let (stream, _addr) = self.listener.accept().await?;
        Ok(IpcSocket::from_stream(stream))
    }
}

/// The same wire format over a blocking `std` socket, for tools that have
/// no async runtime (grove).
pub mod blocking {
    use super::{IpcError, MAX_MESSAGE_SIZE};
    use crate::messages::HiveMessage;
    use std::io::{self, Read, Write};
    use std::os::unix::net::UnixStream;
    use std::path::Path;

    /// A connected, blocking IPC socket.
    pub struct Connection {
        stream: UnixStream,
    }

    impl Connection {
        pub fn connect<P: AsRef<Path>>(path: P) -> Result<Self, IpcError> {
            Ok(Self {
                stream: UnixStream::connect(path)?,
            })
        }

        /// Wrap an already-connected stream (e.g. one accepted by a test's
        /// listener).
        pub fn from_std(stream: UnixStream) -> Self {
            Self { stream }
        }

        /// A second handle to the same socket, e.g. one to read on another
        /// thread while this one sends.
        pub fn try_clone(&self) -> Result<Self, IpcError> {
            Ok(Self {
                stream: self.stream.try_clone()?,
            })
        }

        pub fn send(&mut self, msg: &HiveMessage) -> Result<(), IpcError> {
            let encoded = msg.encode()?;
            if encoded.len() > MAX_MESSAGE_SIZE {
                return Err(IpcError::MessageTooLarge {
                    size: encoded.len(),
                    max: MAX_MESSAGE_SIZE,
                });
            }
            self.stream
                .write_all(&(encoded.len() as u32).to_le_bytes())?;
            self.stream.write_all(&encoded)?;
            self.stream.flush()?;
            Ok(())
        }

        pub fn recv(&mut self) -> Result<HiveMessage, IpcError> {
            let mut len_buf = [0u8; 4];
            match self.stream.read_exact(&mut len_buf) {
                Ok(()) => {}
                Err(e) if e.kind() == io::ErrorKind::UnexpectedEof => {
                    return Err(IpcError::ConnectionClosed)
                }
                Err(e) => return Err(e.into()),
            }
            let len = u32::from_le_bytes(len_buf) as usize;
            if len > MAX_MESSAGE_SIZE {
                return Err(IpcError::MessageTooLarge {
                    size: len,
                    max: MAX_MESSAGE_SIZE,
                });
            }
            let mut buf = vec![0u8; len];
            self.stream.read_exact(&mut buf)?;
            HiveMessage::decode(&buf).map_err(IpcError::from)
        }
    }
}

/// Helper to drop privileges after binding sockets
pub fn drop_privileges(user: &str) -> Result<(), IpcError> {
    use nix::unistd::{setgid, setuid, Gid, Uid, User};

    let user = User::from_name(user)
        .map_err(|e| io::Error::new(io::ErrorKind::NotFound, e))?
        .ok_or_else(|| {
            io::Error::new(io::ErrorKind::NotFound, format!("User {} not found", user))
        })?;

    // Set group first (must be done before setuid)
    setgid(Gid::from_raw(user.gid.as_raw()))
        .map_err(|e| io::Error::new(io::ErrorKind::PermissionDenied, e))?;

    // Set user
    setuid(Uid::from_raw(user.uid.as_raw()))
        .map_err(|e| io::Error::new(io::ErrorKind::PermissionDenied, e))?;

    tracing::info!("Dropped privileges to user: {} ({})", user.name, user.uid);

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;

    #[tokio::test]
    async fn test_ipc_roundtrip() {
        let dir = tempfile::tempdir().unwrap();
        let socket_path = dir.path().join("test.sock");

        // Start server
        let server = IpcServer::bind(&socket_path).await.unwrap();

        // Connect client
        let client_handle = tokio::spawn({
            let socket_path = socket_path.clone();
            async move {
                let mut client = IpcSocket::connect(&socket_path).await.unwrap();

                // Send a message
                let msg = HiveMessage::Ping {
                    timestamp: Utc::now(),
                };
                client.send(&msg).await.unwrap();

                // Receive response
                let response: HiveMessage = client.recv().await.unwrap();
                response
            }
        });

        // Accept connection and echo
        let mut conn = server.accept().await.unwrap();
        let received: HiveMessage = conn.recv().await.unwrap();
        assert_eq!(received.type_name(), "Ping");

        let response = HiveMessage::Pong {
            ping_timestamp: Utc::now(),
            component: "test".into(),
        };
        conn.send(&response).await.unwrap();

        let client_received = client_handle.await.unwrap();
        assert_eq!(client_received.type_name(), "Pong");
    }

    #[tokio::test]
    async fn blocking_client_talks_to_async_server() {
        use std::os::unix::fs::PermissionsExt;

        let dir = tempfile::tempdir().unwrap();
        let socket_path = dir.path().join("user.sock");
        let server = IpcServer::bind_for_all_users(&socket_path).await.unwrap();
        let mode = std::fs::metadata(&socket_path)
            .unwrap()
            .permissions()
            .mode()
            & 0o777;
        assert_eq!(mode, 0o666);

        let client = tokio::task::spawn_blocking({
            let socket_path = socket_path.clone();
            move || {
                let mut conn = blocking::Connection::connect(&socket_path).unwrap();
                let mut reader = conn.try_clone().unwrap();
                conn.send(&HiveMessage::Ping {
                    timestamp: Utc::now(),
                })
                .unwrap();
                reader.recv().unwrap()
            }
        });

        let mut conn = server.accept().await.unwrap();
        assert_eq!(conn.recv().await.unwrap().type_name(), "Ping");
        conn.send(&HiveMessage::Pong {
            ping_timestamp: Utc::now(),
            component: "test".into(),
        })
        .await
        .unwrap();
        assert_eq!(client.await.unwrap().type_name(), "Pong");
    }
}
