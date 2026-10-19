//! Hive Term - Hive-integrated terminal emulator
//!
//! A terminal emulator designed for DruidOS with deep integration into the
//! Hive Stack. Features include:
//!
//! - Anonymous mode support for privacy
//! - Inline suggestions from Hive
//! - Command reporting for intelligent assistance
//! - DruidOS theme integration
//!
//! # Usage
//!
//! ```bash
//! # Normal mode
//! hive-term
//!
//! # Quiet mode (no notifications)
//! HIVE_ANONYMOUS=quiet hive-term
//!
//! # Detached mode (invisible to Hive)
//! HIVE_ANONYMOUS=detach hive-term
//!
//! # Full anonymous mode
//! HIVE_ANONYMOUS=full hive-term
//! ```

mod config;
mod hive;
mod pty;
mod terminal;

use anyhow::Result;
use crossterm::{
    cursor,
    event::{self, Event, KeyCode, KeyEvent, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use std::io::{stdout, Write};
use tokio::sync::mpsc;
use tracing::{error, info};

use crate::config::TermConfig;
use crate::hive::{HiveEvent, HiveIntegration};
use crate::pty::{PtyEvent, PtyManager};
use crate::terminal::Terminal;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("hive_term=info".parse()?),
        )
        .init();

    info!("Hive Term starting...");

    // Load configuration
    let config = TermConfig::load_default();

    // Run the terminal
    let result = run_terminal(config).await;

    // Handle any errors
    if let Err(e) = &result {
        error!("Terminal error: {}", e);
    }

    result
}

async fn run_terminal(config: TermConfig) -> Result<()> {
    // Create channels
    let (pty_event_tx, mut pty_event_rx) = mpsc::channel::<PtyEvent>(100);
    let (hive_event_tx, mut hive_event_rx) = mpsc::channel::<HiveEvent>(100);

    // Initialize PTY
    let pty = PtyManager::new(&config, pty_event_tx)?;

    // Initialize Hive integration
    let mut hive = HiveIntegration::new(config.hive.clone(), hive_event_tx).await?;

    // Initialize terminal state
    let (cols, rows) = pty.size();
    let mut term = Terminal::new(cols as usize, rows as usize);

    // Set up terminal
    enable_raw_mode()?;
    let mut stdout = stdout();
    execute!(stdout, EnterAlternateScreen)?;

    info!("Terminal ready");

    // Main loop
    let result = main_loop(&mut term, &pty, &mut hive, &mut pty_event_rx, &mut hive_event_rx).await;

    // Cleanup
    disable_raw_mode()?;
    execute!(stdout, LeaveAlternateScreen)?;

    result
}

async fn main_loop(
    term: &mut Terminal,
    pty: &PtyManager,
    hive: &mut HiveIntegration,
    pty_events: &mut mpsc::Receiver<PtyEvent>,
    hive_events: &mut mpsc::Receiver<HiveEvent>,
) -> Result<()> {
    let mut stdout = stdout();

    loop {
        // Check for keyboard input (non-blocking)
        if event::poll(std::time::Duration::from_millis(10))? {
            if let Event::Key(key) = event::read()? {
                if handle_key(key, pty, hive).await? {
                    break; // Exit requested
                }
            }
        }

        // Process PTY events
        while let Ok(event) = pty_events.try_recv() {
            match event {
                PtyEvent::Data(data) => {
                    term.process(&data);
                    render(term, &mut stdout)?;
                }
                PtyEvent::Closed => {
                    info!("Shell exited");
                    return Ok(());
                }
                PtyEvent::Error(e) => {
                    error!("PTY error: {}", e);
                    return Ok(());
                }
            }
        }

        // Process Hive events
        while let Ok(event) = hive_events.try_recv() {
            match event {
                HiveEvent::Suggestion(suggestion) => {
                    // Could display inline suggestion
                    info!("Suggestion: {}", suggestion.title);
                }
                HiveEvent::Connected => {
                    info!("Connected to Hive");
                }
                HiveEvent::Disconnected => {
                    info!("Disconnected from Hive");
                }
            }
        }
    }

    Ok(())
}

async fn handle_key(
    key: KeyEvent,
    pty: &PtyManager,
    hive: &mut HiveIntegration,
) -> Result<bool> {
    // Handle special keys
    match (key.modifiers, key.code) {
        // Ctrl+Shift+Q to quit
        (m, KeyCode::Char('q')) if m.contains(KeyModifiers::CONTROL) && m.contains(KeyModifiers::SHIFT) => {
            return Ok(true);
        }
        // Ctrl+Shift+H to toggle Hive suggestions
        (m, KeyCode::Char('h')) if m.contains(KeyModifiers::CONTROL) && m.contains(KeyModifiers::SHIFT) => {
            hive.request_suggestions(None).await?;
            return Ok(false);
        }
        _ => {}
    }

    // Convert key to bytes and send to PTY
    let bytes = key_to_bytes(key);
    if !bytes.is_empty() {
        pty.write(bytes).await?;
    }

    Ok(false)
}

fn key_to_bytes(key: KeyEvent) -> Vec<u8> {
    let mut bytes = Vec::new();

    match key.code {
        KeyCode::Char(c) => {
            if key.modifiers.contains(KeyModifiers::CONTROL) {
                // Ctrl+letter sends control character
                if c.is_ascii_lowercase() {
                    bytes.push((c as u8) - b'a' + 1);
                } else if c.is_ascii_uppercase() {
                    bytes.push((c.to_ascii_lowercase() as u8) - b'a' + 1);
                }
            } else if key.modifiers.contains(KeyModifiers::ALT) {
                // Alt+key sends ESC followed by key
                bytes.push(0x1b);
                let mut s = String::new();
                s.push(c);
                bytes.extend(s.as_bytes());
            } else {
                let mut s = String::new();
                s.push(c);
                bytes.extend(s.as_bytes());
            }
        }
        KeyCode::Enter => bytes.push(b'\r'),
        KeyCode::Backspace => bytes.push(0x7f),
        KeyCode::Tab => bytes.push(b'\t'),
        KeyCode::Esc => bytes.push(0x1b),
        KeyCode::Up => bytes.extend(b"\x1b[A"),
        KeyCode::Down => bytes.extend(b"\x1b[B"),
        KeyCode::Right => bytes.extend(b"\x1b[C"),
        KeyCode::Left => bytes.extend(b"\x1b[D"),
        KeyCode::Home => bytes.extend(b"\x1b[H"),
        KeyCode::End => bytes.extend(b"\x1b[F"),
        KeyCode::PageUp => bytes.extend(b"\x1b[5~"),
        KeyCode::PageDown => bytes.extend(b"\x1b[6~"),
        KeyCode::Insert => bytes.extend(b"\x1b[2~"),
        KeyCode::Delete => bytes.extend(b"\x1b[3~"),
        KeyCode::F(n) => {
            let seq = match n {
                1 => b"\x1bOP".to_vec(),
                2 => b"\x1bOQ".to_vec(),
                3 => b"\x1bOR".to_vec(),
                4 => b"\x1bOS".to_vec(),
                5 => b"\x1b[15~".to_vec(),
                6 => b"\x1b[17~".to_vec(),
                7 => b"\x1b[18~".to_vec(),
                8 => b"\x1b[19~".to_vec(),
                9 => b"\x1b[20~".to_vec(),
                10 => b"\x1b[21~".to_vec(),
                11 => b"\x1b[23~".to_vec(),
                12 => b"\x1b[24~".to_vec(),
                _ => vec![],
            };
            bytes.extend(seq);
        }
        _ => {}
    }

    bytes
}

fn render(term: &Terminal, stdout: &mut impl Write) -> Result<()> {
    // Move to top-left
    execute!(stdout, cursor::MoveTo(0, 0))?;

    let grid = term.grid();
    let (cols, rows) = grid.size();

    // Render each cell
    for row in 0..rows {
        for col in 0..cols {
            if let Some(cell) = grid.get(col, row) {
                // Simple rendering - just print the character
                write!(stdout, "{}", cell.c)?;
            }
        }
        if row < rows - 1 {
            write!(stdout, "\r\n")?;
        }
    }

    // Move cursor to terminal cursor position
    let (cursor_col, cursor_row) = term.cursor();
    execute!(stdout, cursor::MoveTo(cursor_col as u16, cursor_row as u16))?;

    stdout.flush()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_key_to_bytes_char() {
        let key = KeyEvent::new(KeyCode::Char('a'), KeyModifiers::NONE);
        assert_eq!(key_to_bytes(key), b"a");
    }

    #[test]
    fn test_key_to_bytes_ctrl() {
        let key = KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL);
        assert_eq!(key_to_bytes(key), vec![3]); // Ctrl+C = 0x03
    }

    #[test]
    fn test_key_to_bytes_arrow() {
        let key = KeyEvent::new(KeyCode::Up, KeyModifiers::NONE);
        assert_eq!(key_to_bytes(key), b"\x1b[A");
    }
}
