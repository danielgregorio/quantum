//! A real program (hive-dashboard, grove) in a pseudo-terminal, its screen
//! read as text through a terminal emulator: what a person would see, with
//! no screenshot and no OCR.

use anyhow::{bail, Context as _, Result};
use std::io::{Read, Write};
use std::process::Stdio;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use tokio::process::{Child, Command};

pub struct Tui {
    child: Child,
    writer: std::fs::File,
    parser: Arc<Mutex<vt100::Parser>>,
}

/// What a screen shows: its text, one line per row, and where the cursor is.
#[derive(Debug, Clone, serde::Serialize)]
pub struct Screen {
    pub text: String,
    pub cursor: (u16, u16),
}

impl Tui {
    /// Starts `cmd` with a pseudo-terminal of `rows` x `cols` as its
    /// controlling terminal. `setup` runs in the child before exec, after
    /// the terminal is attached (the lab's namespace, a user to become).
    pub fn spawn(
        mut cmd: Command,
        rows: u16,
        cols: u16,
        setup: impl FnMut() -> std::io::Result<()> + Send + Sync + 'static,
    ) -> Result<Tui> {
        let size = nix::pty::Winsize {
            ws_row: rows,
            ws_col: cols,
            ws_xpixel: 0,
            ws_ypixel: 0,
        };
        let pty = nix::pty::openpty(Some(&size), None).context("openpty")?;
        let slave = std::fs::File::from(pty.slave);
        cmd.stdin(Stdio::from(slave.try_clone()?))
            .stdout(Stdio::from(slave.try_clone()?))
            .stderr(Stdio::from(slave))
            .env("TERM", "xterm-256color")
            .env("LANG", "C.UTF-8")
            .kill_on_drop(true);
        let mut setup = setup;
        // SAFETY: runs in the child between fork and exec; only syscalls.
        unsafe {
            cmd.pre_exec(move || {
                nix::unistd::setsid().map_err(|e| std::io::Error::from_raw_os_error(e as i32))?;
                if libc::ioctl(0, libc::TIOCSCTTY, 0) < 0 {
                    return Err(std::io::Error::last_os_error());
                }
                setup()
            });
        }
        let child = cmd
            .spawn()
            .context("cannot start the program in a pseudo-terminal")?;
        let master = std::fs::File::from(pty.master);
        let mut reader = master.try_clone()?;
        let parser = Arc::new(Mutex::new(vt100::Parser::new(rows, cols, 0)));
        let feeding = parser.clone();
        std::thread::spawn(move || {
            let mut buf = [0u8; 8192];
            loop {
                match reader.read(&mut buf) {
                    Ok(0) | Err(_) => break,
                    Ok(n) => feeding.lock().unwrap().process(&buf[..n]),
                }
            }
        });
        Ok(Tui {
            child,
            writer: master,
            parser,
        })
    }

    pub fn screen(&self) -> Screen {
        let parser = self.parser.lock().unwrap();
        let screen = parser.screen();
        let text = screen
            .contents()
            .lines()
            .map(str::trim_end)
            .collect::<Vec<_>>()
            .join("\n");
        Screen {
            text,
            cursor: screen.cursor_position(),
        }
    }

    /// Types: named keys (Enter, Esc, Up, Down, Left, Right, Tab, Backspace,
    /// Ctrl-C, Ctrl-D) or plain text.
    pub fn keys(&mut self, keys: &[String]) -> Result<()> {
        for key in keys {
            let bytes: Vec<u8> = match key.as_str() {
                "Enter" => b"\r".to_vec(),
                "Esc" => b"\x1b".to_vec(),
                "Tab" => b"\t".to_vec(),
                "Backspace" => b"\x7f".to_vec(),
                "Up" => b"\x1b[A".to_vec(),
                "Down" => b"\x1b[B".to_vec(),
                "Right" => b"\x1b[C".to_vec(),
                "Left" => b"\x1b[D".to_vec(),
                "Ctrl-C" => b"\x03".to_vec(),
                "Ctrl-D" => b"\x04".to_vec(),
                text => text.as_bytes().to_vec(),
            };
            self.writer.write_all(&bytes)?;
            self.writer.flush()?;
            // one key at a time, as a person types: a TUI reads its events
            // one by one, and an escape sequence must not merge with the next
            std::thread::sleep(Duration::from_millis(15));
        }
        Ok(())
    }

    /// Waits until the screen shows `text` (and, with `excludes`, does not
    /// show that).
    pub async fn until(
        &self,
        text: &str,
        excludes: Option<&str>,
        timeout: Duration,
    ) -> Result<Screen> {
        let deadline = Instant::now() + timeout;
        loop {
            let screen = self.screen();
            if screen.text.contains(text) && excludes.map_or(true, |x| !screen.text.contains(x)) {
                return Ok(screen);
            }
            if Instant::now() > deadline {
                bail!(
                    "the screen never showed {:?}{}; it shows:\n{}",
                    text,
                    excludes
                        .map(|x| format!(" without {:?}", x))
                        .unwrap_or_default(),
                    screen.text
                );
            }
            tokio::time::sleep(Duration::from_millis(20)).await;
        }
    }

    pub async fn stop(mut self) {
        let _ = self.child.kill().await;
    }
}
