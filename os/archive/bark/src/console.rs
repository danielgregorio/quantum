//! Console I/O for DruidOS
//!
//! Provides text input/output via VirtIO console or serial port.
//! Used by Grove shell for user interaction.

use crate::error::{BarkError, Result};
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Read, Write};
use std::os::unix::io::AsRawFd;
use std::path::Path;

/// Console device paths in order of preference
const CONSOLE_DEVICES: &[&str] = &[
    "/dev/hvc0",    // VirtIO console (preferred)
    "/dev/ttyS0",   // Serial port (fallback)
    "/dev/console", // Generic console
    "/dev/tty",     // Controlling terminal
];

/// Console device for text I/O
pub struct Console {
    /// Input file handle
    input: Option<File>,
    /// Output file handle
    output: Option<File>,
    /// Buffered reader for line input
    reader: Option<BufReader<File>>,
    /// Path of the opened device
    device_path: String,
    /// Is this a virtual console (for testing)?
    is_virtual: bool,
}

impl Console {
    /// Open the default console device
    ///
    /// Tries VirtIO console first, then falls back to serial.
    pub fn open_default() -> Result<Self> {
        for device in CONSOLE_DEVICES {
            if Path::new(device).exists() {
                match Self::open(device) {
                    Ok(console) => return Ok(console),
                    Err(_) => continue,
                }
            }
        }

        Err(BarkError::DeviceNotFound("No console device found".into()))
    }

    /// Open a specific console device
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self> {
        let path = path.as_ref();
        let path_str = path.display().to_string();

        let input = OpenOptions::new().read(true).open(path).map_err(|e| {
            if e.kind() == std::io::ErrorKind::PermissionDenied {
                BarkError::PermissionDenied(format!("Cannot open {}: {}", path_str, e))
            } else {
                BarkError::Io(e)
            }
        })?;

        let output = OpenOptions::new()
            .write(true)
            .open(path)
            .map_err(|e| BarkError::Io(e))?;

        let reader = BufReader::new(
            OpenOptions::new()
                .read(true)
                .open(path)
                .map_err(|e| BarkError::Io(e))?,
        );

        Ok(Self {
            input: Some(input),
            output: Some(output),
            reader: Some(reader),
            device_path: path_str,
            is_virtual: false,
        })
    }

    /// Create a virtual console using stdin/stdout (for testing)
    pub fn stdio() -> Self {
        Self {
            input: None,
            output: None,
            reader: None,
            device_path: "stdio".into(),
            is_virtual: true,
        }
    }

    /// Write a string to the console
    pub fn write(&mut self, s: &str) -> Result<()> {
        if self.is_virtual {
            print!("{}", s);
            std::io::stdout().flush().map_err(BarkError::Io)?;
        } else if let Some(ref mut output) = self.output {
            output.write_all(s.as_bytes()).map_err(BarkError::Io)?;
            output.flush().map_err(BarkError::Io)?;
        }
        Ok(())
    }

    /// Write a line to the console (with newline)
    pub fn writeln(&mut self, s: &str) -> Result<()> {
        self.write(s)?;
        self.write("\n")
    }

    /// Write formatted output to the console
    pub fn write_fmt(&mut self, args: std::fmt::Arguments<'_>) -> Result<()> {
        self.write(&format!("{}", args))
    }

    /// Read a single character (blocking)
    pub fn read_char(&mut self) -> Result<char> {
        let mut buf = [0u8; 4];

        if self.is_virtual {
            std::io::stdin()
                .read_exact(&mut buf[..1])
                .map_err(BarkError::Io)?;
        } else if let Some(ref mut input) = self.input {
            input.read_exact(&mut buf[..1]).map_err(BarkError::Io)?;
        } else {
            return Err(BarkError::Input("No input device".into()));
        }

        Ok(buf[0] as char)
    }

    /// Read a line of input (blocking)
    pub fn read_line(&mut self) -> Result<String> {
        let mut line = String::new();

        if self.is_virtual {
            std::io::stdin()
                .read_line(&mut line)
                .map_err(BarkError::Io)?;
        } else if let Some(ref mut reader) = self.reader {
            reader.read_line(&mut line).map_err(BarkError::Io)?;
        } else {
            return Err(BarkError::Input("No input device".into()));
        }

        // Remove trailing newline
        if line.ends_with('\n') {
            line.pop();
            if line.ends_with('\r') {
                line.pop();
            }
        }

        Ok(line)
    }

    /// Check if input is available (non-blocking)
    pub fn has_input(&self) -> bool {
        if self.is_virtual {
            // For stdio, we can't easily check without blocking
            // This would need termios configuration
            false
        } else if let Some(ref input) = self.input {
            // Use poll to check for available input
            let fd = input.as_raw_fd();
            let mut pollfd = libc::pollfd {
                fd,
                events: libc::POLLIN,
                revents: 0,
            };

            unsafe {
                let result = libc::poll(&mut pollfd, 1, 0);
                result > 0 && (pollfd.revents & libc::POLLIN) != 0
            }
        } else {
            false
        }
    }

    /// Try to read a character (non-blocking)
    ///
    /// Returns None if no input is available.
    pub fn try_read_char(&mut self) -> Result<Option<char>> {
        if self.has_input() {
            Ok(Some(self.read_char()?))
        } else {
            Ok(None)
        }
    }

    /// Clear the screen (ANSI escape sequence)
    pub fn clear(&mut self) -> Result<()> {
        self.write("\x1b[2J\x1b[H")
    }

    /// Move cursor to position (1-indexed)
    pub fn move_cursor(&mut self, row: u32, col: u32) -> Result<()> {
        self.write(&format!("\x1b[{};{}H", row, col))
    }

    /// Set text color (ANSI)
    pub fn set_color(&mut self, color: ConsoleColor) -> Result<()> {
        self.write(&format!("\x1b[{}m", color.to_ansi_code()))
    }

    /// Reset text formatting
    pub fn reset_format(&mut self) -> Result<()> {
        self.write("\x1b[0m")
    }

    /// Get the device path
    pub fn device_path(&self) -> &str {
        &self.device_path
    }

    /// Enable raw mode (no line buffering, no echo)
    pub fn set_raw_mode(&self, enabled: bool) -> Result<()> {
        if self.is_virtual {
            // For stdio, use termios
            return Ok(()); // TODO: implement for stdio
        }

        if let Some(ref input) = self.input {
            let fd = input.as_raw_fd();
            let mut termios = std::mem::MaybeUninit::<libc::termios>::uninit();

            unsafe {
                if libc::tcgetattr(fd, termios.as_mut_ptr()) < 0 {
                    return Err(BarkError::Io(std::io::Error::last_os_error()));
                }

                let mut termios = termios.assume_init();

                if enabled {
                    // Disable canonical mode and echo
                    termios.c_lflag &= !(libc::ICANON | libc::ECHO);
                    termios.c_cc[libc::VMIN] = 1;
                    termios.c_cc[libc::VTIME] = 0;
                } else {
                    // Enable canonical mode and echo
                    termios.c_lflag |= libc::ICANON | libc::ECHO;
                }

                if libc::tcsetattr(fd, libc::TCSANOW, &termios) < 0 {
                    return Err(BarkError::Io(std::io::Error::last_os_error()));
                }
            }
        }

        Ok(())
    }
}

impl Default for Console {
    fn default() -> Self {
        Self::stdio()
    }
}

/// ANSI console colors
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConsoleColor {
    Black,
    Red,
    Green,
    Yellow,
    Blue,
    Magenta,
    Cyan,
    White,
    BrightBlack,
    BrightRed,
    BrightGreen,
    BrightYellow,
    BrightBlue,
    BrightMagenta,
    BrightCyan,
    BrightWhite,
    Reset,
}

impl ConsoleColor {
    /// Convert to ANSI escape code
    pub fn to_ansi_code(self) -> u8 {
        match self {
            ConsoleColor::Black => 30,
            ConsoleColor::Red => 31,
            ConsoleColor::Green => 32,
            ConsoleColor::Yellow => 33,
            ConsoleColor::Blue => 34,
            ConsoleColor::Magenta => 35,
            ConsoleColor::Cyan => 36,
            ConsoleColor::White => 37,
            ConsoleColor::BrightBlack => 90,
            ConsoleColor::BrightRed => 91,
            ConsoleColor::BrightGreen => 92,
            ConsoleColor::BrightYellow => 93,
            ConsoleColor::BrightBlue => 94,
            ConsoleColor::BrightMagenta => 95,
            ConsoleColor::BrightCyan => 96,
            ConsoleColor::BrightWhite => 97,
            ConsoleColor::Reset => 0,
        }
    }
}

/// Simple logging macros for console output
#[macro_export]
macro_rules! console_log {
    ($console:expr, $($arg:tt)*) => {
        let _ = $console.writeln(&format!($($arg)*));
    };
}

#[macro_export]
macro_rules! console_print {
    ($console:expr, $($arg:tt)*) => {
        let _ = $console.write(&format!($($arg)*));
    };
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_console_color_codes() {
        assert_eq!(ConsoleColor::Red.to_ansi_code(), 31);
        assert_eq!(ConsoleColor::Green.to_ansi_code(), 32);
        assert_eq!(ConsoleColor::BrightWhite.to_ansi_code(), 97);
        assert_eq!(ConsoleColor::Reset.to_ansi_code(), 0);
    }

    #[test]
    fn test_virtual_console() {
        let console = Console::stdio();
        assert_eq!(console.device_path(), "stdio");
        assert!(console.is_virtual);
    }
}
