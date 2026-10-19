//! The pixel socket: where `quantum pixel` brings a page to the screen.
//! One client at a time connects to a Unix socket (/run/hive-screen/
//! pixel.sock as a daemon; wherever a test says in play mode), sends
//! JSON lines, and hears the window's events as JSON lines:
//!
//! ```text
//! -> {"op":"show","page":{"title":"Tarefas","flash":null,"view":[...]}}   the page, whole, each time it changes
//! -> {"op":"close"}                                                        the page goes
//! <- {"event":"click","id":7,"action":"remove","fields":{"id":"2"}}       a button
//! <- {"event":"submit","id":3,"action":"save","fields":{"name":"Ana"}}   a form, with what the user left
//! <- {"event":"change","id":4,"bind":"q","value":"ab"}                    a search field, after a pause
//! <- {"event":"navigate","id":9,"to":"/about"}                            a link
//! <- {"event":"reload"}                                                   F5
//! <- {"event":"close"}                                                    Esc: the window is gone
//! <- {"error":"..."}                                                      a line that was not a request
//! ```
//!
//! The socket is anyone's (mode 0666): any local user may open a page on
//! the console, as any may run `quantum console`. When the client goes
//! away its page goes with it. A second client while one is connected
//! is told so and dropped.

use anyhow::{Context as _, Result};
use serde_json::{json, Value};
use std::io::{ErrorKind, Read, Write};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::{Path, PathBuf};

pub const DEFAULT_PATH: &str = "/run/hive-screen/pixel.sock";

struct Client {
    stream: UnixStream,
    buf: Vec<u8>,
    /// Whether it has a page on the screen: its going closes the page.
    showing: bool,
}

pub struct PixelSocket {
    listener: UnixListener,
    client: Option<Client>,
    path: PathBuf,
}

impl PixelSocket {
    /// Binds the socket (a stale file from a run before is removed), for
    /// every local user, non-blocking.
    pub fn bind(path: &Path) -> Result<PixelSocket> {
        if path.exists() {
            std::fs::remove_file(path)
                .with_context(|| format!("removing the old socket {}", path.display()))?;
        }
        let listener = UnixListener::bind(path)
            .with_context(|| format!("binding the pixel socket {}", path.display()))?;
        std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o666))
            .with_context(|| format!("opening {} to every user", path.display()))?;
        listener.set_nonblocking(true)?;
        tracing::info!("pixel socket {}", path.display());
        Ok(PixelSocket {
            listener,
            client: None,
            path: path.to_path_buf(),
        })
    }

    /// The requests that came in since the last poll: a new client is
    /// taken (or turned away while one is connected), its lines are read,
    /// and a client that went away leaves a `close` behind when it had a
    /// page on the screen.
    pub fn poll(&mut self) -> Vec<Value> {
        self.accept();
        let mut requests = Vec::new();
        let Some(client) = &mut self.client else {
            return requests;
        };
        let mut gone = false;
        let mut chunk = [0u8; 65536];
        loop {
            match client.stream.read(&mut chunk) {
                Ok(0) => {
                    gone = true;
                    break;
                }
                Ok(n) => client.buf.extend_from_slice(&chunk[..n]),
                Err(e) if e.kind() == ErrorKind::WouldBlock => break,
                Err(e) if e.kind() == ErrorKind::Interrupted => continue,
                Err(_) => {
                    gone = true;
                    break;
                }
            }
        }
        while let Some(nl) = client.buf.iter().position(|&b| b == b'\n') {
            let line: Vec<u8> = client.buf.drain(..=nl).collect();
            let text = String::from_utf8_lossy(&line[..nl]).trim().to_string();
            if text.is_empty() {
                continue;
            }
            match serde_json::from_str::<Value>(&text) {
                Ok(req) => {
                    match req.get("op").and_then(Value::as_str) {
                        Some("show") => client.showing = true,
                        Some("close") => client.showing = false,
                        _ => {}
                    }
                    requests.push(req);
                }
                Err(e) => {
                    let _ = writeln!(
                        client.stream,
                        "{}",
                        json!({"error": format!("not a request: {}", e)})
                    );
                }
            }
        }
        if gone {
            let showing = client.showing;
            self.client = None;
            tracing::info!("the page's runtime went away");
            if showing {
                requests.push(json!({"op": "close"}));
            }
        }
        requests
    }

    fn accept(&mut self) {
        loop {
            match self.listener.accept() {
                Ok((mut stream, _)) => {
                    if self.client.is_some() {
                        let _ = writeln!(
                            stream,
                            "{}",
                            json!({"error": "the screen is showing another page; close it first"})
                        );
                        continue;
                    }
                    if stream.set_nonblocking(true).is_err() {
                        continue;
                    }
                    tracing::info!("a page's runtime connected");
                    self.client = Some(Client {
                        stream,
                        buf: Vec::new(),
                        showing: false,
                    });
                }
                Err(e) if e.kind() == ErrorKind::WouldBlock => return,
                Err(e) if e.kind() == ErrorKind::Interrupted => continue,
                Err(e) => {
                    tracing::warn!("accepting on the pixel socket: {}", e);
                    return;
                }
            }
        }
    }

    /// An event of the window, to the client (none: nothing is said).
    pub fn send(&mut self, event: &Value) {
        let Some(client) = &mut self.client else {
            return;
        };
        let line = format!("{}\n", event);
        if let Err(e) = write_all_blocking(&mut client.stream, line.as_bytes()) {
            tracing::warn!("the page's runtime stopped listening: {}", e);
            self.client = None;
        }
    }

    /// Whether a client is connected.
    pub fn connected(&self) -> bool {
        self.client.is_some()
    }
}

/// Writes whole on a non-blocking stream: an event is a few hundred
/// bytes, and a client that cannot take them within a moment is gone.
fn write_all_blocking(stream: &mut UnixStream, mut bytes: &[u8]) -> std::io::Result<()> {
    let started = std::time::Instant::now();
    while !bytes.is_empty() {
        match stream.write(bytes) {
            Ok(0) => return Err(std::io::Error::new(ErrorKind::WriteZero, "nothing written")),
            Ok(n) => bytes = &bytes[n..],
            Err(e) if e.kind() == ErrorKind::WouldBlock => {
                if started.elapsed() > std::time::Duration::from_secs(2) {
                    return Err(std::io::Error::new(
                        ErrorKind::TimedOut,
                        "the client does not read",
                    ));
                }
                std::thread::sleep(std::time::Duration::from_millis(5));
            }
            Err(e) if e.kind() == ErrorKind::Interrupted => continue,
            Err(e) => return Err(e),
        }
    }
    Ok(())
}

impl Drop for PixelSocket {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.path);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{BufRead, BufReader};

    #[test]
    fn one_client_shows_a_page_and_hears_events_a_second_is_turned_away() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("pixel.sock");
        let mut socket = PixelSocket::bind(&path).unwrap();
        assert_eq!(
            std::fs::metadata(&path).unwrap().permissions().mode() & 0o777,
            0o666
        );
        assert!(socket.poll().is_empty());

        let mut first = UnixStream::connect(&path).unwrap();
        writeln!(first, r#"{{"op":"show","page":{{"title":"T","view":[]}}}}"#).unwrap();
        writeln!(first, "not json").unwrap();
        let mut got = Vec::new();
        while got.is_empty() {
            got = socket.poll();
        }
        assert_eq!(got.len(), 1);
        assert_eq!(got[0]["op"], "show");
        assert!(socket.connected());
        socket.send(&json!({"event": "click", "id": 1}));
        {
            let mut lines = BufReader::new(first.try_clone().unwrap()).lines();
            let error = lines.next().unwrap().unwrap();
            assert!(error.contains("not a request"), "{}", error);
            let event = lines.next().unwrap().unwrap();
            assert_eq!(event, r#"{"event":"click","id":1}"#);
        }

        let second = UnixStream::connect(&path).unwrap();
        socket.poll();
        let refused = BufReader::new(second).lines().next().unwrap().unwrap();
        assert!(refused.contains("another page"), "{}", refused);

        // the first goes away with its page on the screen: a close is left behind
        drop(first);
        let mut got = Vec::new();
        for _ in 0..200 {
            got = socket.poll();
            if !got.is_empty() {
                break;
            }
            std::thread::sleep(std::time::Duration::from_millis(5));
        }
        assert_eq!(got, vec![json!({"op": "close"})]);
        assert!(!socket.connected());
        drop(socket);
        assert!(!path.exists());
    }
}
