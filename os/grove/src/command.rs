//! The command form builtins operate on, and their results.
//!
//! Parsing lives in the parser module, expansion in expand; by the time a
//! builtin runs its arguments are final strings.

/// A command name with its (already expanded) arguments
#[derive(Debug, Clone)]
pub struct Command {
    /// The command name
    pub name: String,
    /// Command arguments
    pub args: Vec<String>,
}

impl Command {
    /// Create a new command
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            args: Vec::new(),
        }
    }

    /// Add an argument
    pub fn arg(mut self, arg: &str) -> Self {
        self.args.push(arg.to_string());
        self
    }

    /// Add multiple arguments
    pub fn args(mut self, args: &[&str]) -> Self {
        for arg in args {
            self.args.push(arg.to_string());
        }
        self
    }

    /// Check if this is an empty command
    pub fn is_empty(&self) -> bool {
        self.name.is_empty()
    }
}

impl std::fmt::Display for Command {
    /// Format the full command line representation
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.name)?;
        for arg in &self.args {
            if arg.contains(' ') {
                write!(f, " \"{}\"", arg)?;
            } else {
                write!(f, " {}", arg)?;
            }
        }
        Ok(())
    }
}

/// Result of a builtin
#[derive(Debug, Clone)]
pub enum CommandResult {
    /// Command succeeded
    Success,
    /// Command succeeded with output
    Output(String),
    /// Command failed with error message (or just an exit code, as text)
    Error(String),
    /// Request to exit the shell
    Exit(i32),
    /// Command not found
    NotFound(String),
}

impl CommandResult {
    /// Check if the result is a success
    pub fn is_success(&self) -> bool {
        matches!(self, CommandResult::Success | CommandResult::Output(_))
    }

    /// Check if this is an exit request
    pub fn is_exit(&self) -> bool {
        matches!(self, CommandResult::Exit(_))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn displays_quoted_arguments() {
        let command = Command::new("echo").args(&["hello world", "x"]);
        assert_eq!(command.to_string(), "echo \"hello world\" x");
    }
}
