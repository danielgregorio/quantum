//! # Grove - DruidOS Interactive Shell
//!
//! Grove is the primary user interface for DruidOS, providing
//! a natural language-aware command shell.
//!
//! ## Features
//!
//! - Traditional command-line interface
//! - Command history and editing
//! - Tab completion
//! - Built-in commands for system management
//! - Talks to the Hive: `? question`, notices at the prompt, `anon`
//!
//! ## Example
//!
//! ```rust,no_run
//! use grove::Shell;
//!
//! let mut shell = Shell::new();
//! shell.run();
//! ```

pub mod builtins;
pub mod command;
mod exec;
pub mod expand;
pub mod history;
pub mod hive;
pub mod parser;
pub mod prompt;
pub mod shell;

// Re-exports
pub use command::{Command, CommandResult};
pub use history::History;
pub use shell::Shell;

/// Grove version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// DruidOS welcome banner
pub const BANNER: &str = r#"
    ____             _     ____  ____
   / __ \____  _____(_)___/ / / / /  \___
  / / / / __ \/ ___/ / __  / / / /\__ \__ \
 / /_/ / / / / /  / / /_/ / /_/ /___/ /__/ /
/_____/_/ /_/_/  /_/\__,_/\____//____/____/

        The Living Operating System
                   v0.1.0
"#;

/// Shell prompt string
pub const DEFAULT_PROMPT: &str = "grove> ";
