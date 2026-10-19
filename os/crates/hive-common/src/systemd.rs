//! Minimal systemd readiness notification (the `sd_notify` protocol).
//!
//! Every `hive-*.service` unit is `Type=notify`: systemd considers the
//! service started — and only then starts the units ordered after it —
//! once the process sends `READY=1` as a datagram to the socket named by
//! `$NOTIFY_SOCKET`. A daemon that never sends it sits in "activating"
//! until the start timeout kills it, taking every dependent unit down too.

use std::ffi::OsStr;
use std::io;

/// Tell systemd this service has finished starting up.
///
/// A no-op when not running under systemd (`$NOTIFY_SOCKET` unset), so
/// daemons started by hand keep working.
pub fn notify_ready() -> io::Result<()> {
    notify("READY=1")
}

/// [`notify_ready`] for daemon startup paths: a failure to reach systemd is
/// logged, not propagated — the daemon itself is fine, and systemd will
/// report the start timeout on its own.
pub fn report_ready() {
    if let Err(e) = notify_ready() {
        tracing::warn!("Failed to notify systemd of readiness: {e}");
    }
}

/// Send a raw `sd_notify` state string (e.g. `"READY=1"`, `"STOPPING=1"`).
pub fn notify(state: &str) -> io::Result<()> {
    match std::env::var_os("NOTIFY_SOCKET") {
        Some(socket) => notify_to(&socket, state),
        None => Ok(()),
    }
}

/// Send `state` to a specific notification socket. `@`-prefixed names are
/// Linux abstract-namespace sockets, as systemd uses by default.
#[cfg(target_os = "linux")]
pub fn notify_to(socket: &OsStr, state: &str) -> io::Result<()> {
    use std::os::linux::net::SocketAddrExt;
    use std::os::unix::ffi::OsStrExt;
    use std::os::unix::net::{SocketAddr, UnixDatagram};

    let name = socket.as_bytes();
    let addr = match name.strip_prefix(b"@") {
        Some(abstract_name) => SocketAddr::from_abstract_name(abstract_name)?,
        None => SocketAddr::from_pathname(socket)?,
    };
    UnixDatagram::unbound()?.send_to_addr(state.as_bytes(), &addr)?;
    Ok(())
}

#[cfg(not(target_os = "linux"))]
pub fn notify_to(_socket: &OsStr, _state: &str) -> io::Result<()> {
    Ok(())
}

#[cfg(all(test, target_os = "linux"))]
mod tests {
    use super::*;
    use std::os::linux::net::SocketAddrExt;
    use std::os::unix::net::{SocketAddr, UnixDatagram};

    fn recv(listener: &UnixDatagram) -> String {
        let mut buf = [0u8; 64];
        let n = listener.recv(&mut buf).unwrap();
        String::from_utf8_lossy(&buf[..n]).into_owned()
    }

    #[test]
    fn sends_ready_to_a_pathname_socket() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("notify.sock");
        let listener = UnixDatagram::bind(&path).unwrap();

        notify_to(path.as_os_str(), "READY=1").unwrap();

        assert_eq!(recv(&listener), "READY=1");
    }

    #[test]
    fn sends_ready_to_an_abstract_socket() {
        let name = format!("hive-common-notify-test-{}", std::process::id());
        let addr = SocketAddr::from_abstract_name(name.as_bytes()).unwrap();
        let listener = UnixDatagram::bind_addr(&addr).unwrap();

        notify_to(OsStr::new(&format!("@{name}")), "READY=1").unwrap();

        assert_eq!(recv(&listener), "READY=1");
    }

    #[test]
    fn missing_socket_is_an_error_not_a_panic() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("nobody-listens.sock");

        assert!(notify_to(path.as_os_str(), "READY=1").is_err());
    }
}
