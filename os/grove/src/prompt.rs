//! Prompt configuration and rendering
//!
//! Handles the shell prompt display and customization.

use std::env;
use std::path::PathBuf;

/// Prompt configuration
pub struct Prompt {
    /// Custom prompt format string
    format: String,
    /// Current working directory
    cwd: PathBuf,
    /// Username
    username: String,
    /// Hostname
    hostname: String,
    /// Last command exit code
    last_exit_code: i32,
}

impl Prompt {
    /// Create a new prompt with default format
    pub fn new() -> Self {
        Self {
            format: "[\\u@\\h \\W]\\$ ".to_string(),
            cwd: env::current_dir().unwrap_or_else(|_| PathBuf::from("/")),
            username: env::var("USER").unwrap_or_else(|_| "user".to_string()),
            hostname: Self::get_hostname(),
            last_exit_code: 0,
        }
    }

    /// Create a simple prompt
    pub fn simple() -> Self {
        Self {
            format: "grove> ".to_string(),
            ..Self::new()
        }
    }

    /// Get hostname
    fn get_hostname() -> String {
        // Try to read from /etc/hostname
        if let Ok(hostname) = std::fs::read_to_string("/etc/hostname") {
            return hostname.trim().to_string();
        }
        // Fall back to environment variable
        env::var("HOSTNAME").unwrap_or_else(|_| "druidos".to_string())
    }

    /// Set the prompt format string
    ///
    /// Supported escape sequences:
    /// - \u - username
    /// - \h - hostname
    /// - \H - full hostname
    /// - \w - current working directory (full)
    /// - \W - current working directory (basename)
    /// - \$ - # for root, $ for users
    /// - \n - newline
    /// - \t - time (HH:MM:SS)
    /// - \? - last exit code
    pub fn set_format(&mut self, format: &str) {
        self.format = format.to_string();
    }

    /// Update current working directory
    pub fn update_cwd(&mut self) {
        self.cwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("/"));
    }

    /// Set last exit code
    pub fn set_exit_code(&mut self, code: i32) {
        self.last_exit_code = code;
    }

    /// Render the prompt string
    pub fn render(&self) -> String {
        let mut result = String::new();
        let mut chars = self.format.chars().peekable();

        while let Some(c) = chars.next() {
            if c == '\\' {
                if let Some(&next) = chars.peek() {
                    chars.next();
                    match next {
                        'u' => result.push_str(&self.username),
                        'h' => {
                            // Short hostname (up to first dot)
                            let short = self.hostname.split('.').next().unwrap_or(&self.hostname);
                            result.push_str(short);
                        }
                        'H' => result.push_str(&self.hostname),
                        'w' => {
                            // Full path, with ~ for home
                            let path = self.cwd.display().to_string();
                            if let Ok(home) = env::var("HOME") {
                                if path.starts_with(&home) {
                                    result.push('~');
                                    result.push_str(&path[home.len()..]);
                                } else {
                                    result.push_str(&path);
                                }
                            } else {
                                result.push_str(&path);
                            }
                        }
                        'W' => {
                            // Basename only
                            if let Some(name) = self.cwd.file_name() {
                                result.push_str(&name.to_string_lossy());
                            } else {
                                result.push('/');
                            }
                        }
                        '$' => {
                            // # for root, $ for normal users
                            if self.username == "root" {
                                result.push('#');
                            } else {
                                result.push('$');
                            }
                        }
                        'n' => result.push('\n'),
                        't' => {
                            // Current time
                            // Simple implementation without chrono
                            result.push_str("??:??:??");
                        }
                        '?' => {
                            result.push_str(&self.last_exit_code.to_string());
                        }
                        '\\' => result.push('\\'),
                        '[' | ']' => {
                            // Terminal escape sequences (ignored for now)
                        }
                        other => {
                            result.push('\\');
                            result.push(other);
                        }
                    }
                } else {
                    result.push(c);
                }
            } else {
                result.push(c);
            }
        }

        result
    }

    /// Get a colored prompt (ANSI)
    pub fn render_colored(&self) -> String {
        let prompt = self.render();

        // Add color codes
        if self.last_exit_code == 0 {
            format!("\x1b[32m{}\x1b[0m", prompt) // Green for success
        } else {
            format!("\x1b[31m{}\x1b[0m", prompt) // Red for error
        }
    }
}

impl Default for Prompt {
    fn default() -> Self {
        Self::simple()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simple_prompt() {
        let prompt = Prompt::simple();
        assert_eq!(prompt.render(), "grove> ");
    }

    #[test]
    fn test_escape_sequences() {
        let mut prompt = Prompt::new();
        prompt.format = "\\$ ".to_string();
        let rendered = prompt.render();
        // Should be either $ or # depending on user
        assert!(rendered == "$ " || rendered == "# ");
    }

    #[test]
    fn test_exit_code() {
        let mut prompt = Prompt::new();
        prompt.format = "[\\?] ".to_string();
        prompt.set_exit_code(42);
        assert_eq!(prompt.render(), "[42] ");
    }
}
