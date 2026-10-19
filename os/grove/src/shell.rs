//! The main shell implementation
//!
//! Handles the read-eval-print loop; parsing, expansion and execution live
//! in the parser, expand and exec modules.

use crate::exec::{self, Job};
use crate::history::History;
use crate::hive::{AskError, Hive};
use crate::parser;
use crate::prompt::Prompt;
use crate::BANNER;
use std::io::{self, BufRead, Write};

/// The Grove shell
pub struct Shell {
    /// Command history
    pub history: History,
    /// Prompt configuration
    pub prompt: Prompt,
    /// Should we exit?
    running: bool,
    /// Last exit code
    pub(crate) last_exit_code: i32,
    /// Show banner on startup
    show_banner: bool,
    /// Interactive mode
    interactive: bool,
    /// Background jobs not yet reported as done
    pub(crate) jobs: Vec<Job>,
    pub(crate) next_job_id: usize,
    /// The connection to the Hive, once one has been made
    hive: Option<Hive>,
    /// `anon` is on: the Hive leaves this shell alone
    anonymous: bool,
    /// Programs the current line tried to run that don't exist (recorded
    /// while spawning, handled once the line is done)
    pub(crate) not_found: std::cell::RefCell<Vec<String>>,
}

impl Shell {
    /// Create a new shell
    pub fn new() -> Self {
        Self {
            history: History::new(),
            prompt: Prompt::default(),
            running: true,
            last_exit_code: 0,
            show_banner: true,
            interactive: true,
            jobs: Vec::new(),
            next_job_id: 0,
            hive: None,
            anonymous: false,
            not_found: std::cell::RefCell::new(Vec::new()),
        }
    }

    /// Create a non-interactive shell (for `-c` and scripts)
    pub fn non_interactive() -> Self {
        Self {
            show_banner: false,
            interactive: false,
            ..Self::new()
        }
    }

    /// Set whether to show banner
    pub fn set_show_banner(&mut self, show: bool) {
        self.show_banner = show;
    }

    /// Run the shell main loop
    pub fn run(&mut self) {
        if self.interactive {
            exec::install_interactive_signal_handlers();
            if self.show_banner {
                println!("{}", BANNER);
            }
            // Connect up front, so notices reach this shell while it runs.
            self.connected_hive();
        }

        let stdin = io::stdin();
        let mut stdout = io::stdout();

        while self.running {
            self.reap_jobs();

            // Show prompt (only in interactive mode), after whatever the
            // Hive had to say meanwhile
            if self.interactive {
                if let Some(hive) = self.hive.as_mut() {
                    for notice in hive.take_notices() {
                        println!("{notice}");
                    }
                }
                self.prompt.update_cwd();
                self.prompt.set_exit_code(self.last_exit_code);
                if self.anonymous {
                    print!("(anon) ");
                }
                print!("{}", self.prompt.render());
                let _ = stdout.flush();
            }

            // Read a line
            let mut line = String::new();
            match stdin.lock().read_line(&mut line) {
                Ok(0) => {
                    // EOF
                    if self.interactive {
                        println!();
                    }
                    break;
                }
                Ok(_) => {
                    let line = line.trim();
                    if !line.is_empty() {
                        self.history.add(line);
                        self.execute_line(line);
                    }
                }
                Err(e) => {
                    eprintln!("grove: read error: {}", e);
                    break;
                }
            }
        }
    }

    /// Execute a single line of input
    pub fn execute_line(&mut self, line: &str) {
        let trimmed = line.trim();
        // Not command lines: a question for the Hive, and anonymous mode.
        if let Some(question) = trimmed.strip_prefix('?') {
            self.ask_hive(question.trim());
            return;
        }
        if trimmed == "anon" || trimmed.starts_with("anon ") {
            self.anon(trimmed["anon".len()..].trim());
            return;
        }
        match parser::parse(line) {
            Ok(items) => {
                self.run_list(&items);
                let missing = self.not_found.take();
                for command in missing {
                    self.command_not_found(&command);
                }
            }
            Err(e) => {
                eprintln!("grove: {}", e);
                self.last_exit_code = 2;
            }
        }
    }

    /// The Hive connection, connecting (again) if there is none. A new
    /// connection restores anonymous mode: cortex forgets it with the old one.
    fn connected_hive(&mut self) -> Option<&mut Hive> {
        if self.hive.is_none() {
            let mut hive = Hive::connect()?;
            if self.anonymous {
                hive.set_anonymous(true);
            }
            self.hive = Some(hive);
        }
        self.hive.as_mut()
    }

    /// A program the user ran isn't installed. If a package of that name is
    /// available, say so - and tell the Hive, which offers an administrator
    /// to install it.
    pub(crate) fn command_not_found(&mut self, command: &str) {
        let Some(package) = crate::hive::package_for_command(command) else {
            return;
        };
        let offered = self
            .connected_hive()
            .is_some_and(|hive| hive.offer_package(command, &package));
        if offered {
            eprintln!(
                "grove: the package {package} would provide it; the Hive has offered to install \
                 it (an administrator can approve that in hive-dashboard)"
            );
        } else {
            eprintln!("grove: the package {package} would provide it: sudo apt install {package}");
        }
    }

    /// `? question`: ask the Hive, print its answer.
    fn ask_hive(&mut self, question: &str) {
        if question.is_empty() {
            eprintln!("grove: ?: ask the Hive something, e.g. `? why did nginx stop`");
            self.last_exit_code = 2;
            return;
        }
        let interactive = self.interactive;
        let cwd = std::env::current_dir().ok();
        let Some(hive) = self.connected_hive() else {
            eprintln!("grove: the Hive is not reachable (is hive-cortex running?)");
            self.last_exit_code = 1;
            return;
        };
        if interactive {
            eprintln!("[hive] thinking... (the local model takes a moment; Ctrl-C stops waiting)");
        }
        exec::clear_interrupt();
        self.last_exit_code = match hive.ask(question, cwd, exec::interrupted) {
            Ok(lines) => {
                for line in lines {
                    println!("{line}");
                }
                0
            }
            Err(AskError::Interrupted) => {
                eprintln!("grove: stopped waiting for the Hive");
                130
            }
            Err(AskError::TimedOut) => {
                eprintln!("grove: the Hive did not answer in time");
                1
            }
            Err(AskError::Disconnected) => {
                self.hive = None;
                eprintln!("grove: lost the connection to the Hive");
                1
            }
        };
    }

    /// `anon [on|off|status]`: whether the Hive acts on this shell.
    fn anon(&mut self, arg: &str) {
        let on = match arg {
            "" | "on" => true,
            "off" => false,
            "status" => {
                println!("anon: {}", if self.anonymous { "on" } else { "off" });
                self.last_exit_code = 0;
                return;
            }
            other => {
                eprintln!("grove: anon: unknown argument '{other}' (use on, off or status)");
                self.last_exit_code = 2;
                return;
            }
        };
        let Some(hive) = self.connected_hive() else {
            eprintln!("grove: anon: the Hive is not reachable, so it isn't watching anyway");
            self.last_exit_code = 1;
            return;
        };
        if !hive.set_anonymous(on) {
            self.hive = None;
            eprintln!("grove: anon: lost the connection to the Hive");
            self.last_exit_code = 1;
            return;
        }
        self.anonymous = on;
        if on {
            println!(
                "[hive] anonymous: the Hive won't act on or answer to what this shell runs \
                 until `anon off` (the kernel's audit log still records commands)"
            );
        } else {
            println!("[hive] anonymous mode off");
        }
        self.last_exit_code = 0;
    }

    /// Execute a script: one command line per line, stopping at `exit`.
    pub fn execute_script(&mut self, script: &str) {
        for line in script.lines() {
            if !self.running {
                break;
            }
            self.execute_line(line);
        }
    }

    /// Get the last exit code
    pub fn exit_code(&self) -> i32 {
        self.last_exit_code
    }

    /// Check if shell is still running
    pub fn is_running(&self) -> bool {
        self.running
    }

    pub(crate) fn is_interactive(&self) -> bool {
        self.interactive
    }

    /// Exit the shell with a code
    pub fn exit(&mut self, code: i32) {
        self.running = false;
        self.last_exit_code = code;
    }
}

impl Default for Shell {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_shell_creation() {
        let shell = Shell::new();
        assert!(shell.is_running());
        assert_eq!(shell.exit_code(), 0);
    }

    #[test]
    fn test_builtin_execution() {
        let mut shell = Shell::non_interactive();
        shell.execute_line("echo hello");
        assert_eq!(shell.exit_code(), 0);
    }

    #[test]
    fn test_exit_command() {
        let mut shell = Shell::non_interactive();
        shell.execute_line("exit 42");
        assert!(!shell.is_running());
        assert_eq!(shell.exit_code(), 42);
    }

    #[test]
    fn test_unknown_command() {
        let mut shell = Shell::non_interactive();
        shell.execute_line("nonexistent_command_xyz");
        assert_eq!(shell.exit_code(), 127);
    }

    #[test]
    fn test_syntax_error_status() {
        let mut shell = Shell::non_interactive();
        shell.execute_line("echo 'unterminated");
        assert_eq!(shell.exit_code(), 2);
    }

    #[test]
    fn questions_and_anon_without_a_hive_fail_cleanly() {
        std::env::set_var("HIVE_USER_SOCKET", "/nonexistent/grove-test/user.sock");
        let mut shell = Shell::non_interactive();
        shell.execute_line("? why is the sky blue");
        assert_eq!(shell.exit_code(), 1);
        shell.execute_line("?");
        assert_eq!(shell.exit_code(), 2);
        shell.execute_line("anon sideways");
        assert_eq!(shell.exit_code(), 2);
        shell.execute_line("anon status");
        assert_eq!(shell.exit_code(), 0);
    }

    #[test]
    fn test_exit_stops_a_script() {
        let mut shell = Shell::non_interactive();
        shell.execute_script("exit 3\nexit 4\n");
        assert_eq!(shell.exit_code(), 3);
    }
}
