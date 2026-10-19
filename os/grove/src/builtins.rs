//! Built-in shell commands
//!
//! Commands that are handled directly by the shell rather than
//! executing external programs.

use crate::command::{Command, CommandResult};
use crate::history::History;
use std::env;
use std::path::Path;

/// Check if a command is a builtin
pub fn is_builtin(name: &str) -> bool {
    matches!(
        name,
        "cd" | "pwd"
            | "echo"
            | "exit"
            | "help"
            | "history"
            | "clear"
            | "export"
            | "unset"
            | "env"
            | "alias"
            | "type"
            | "source"
            | "true"
            | "false"
            | "test"
            | "["
    )
}

/// Execute a builtin command
pub fn execute(cmd: &Command, history: &History) -> CommandResult {
    match cmd.name.as_str() {
        "cd" => builtin_cd(cmd),
        "pwd" => builtin_pwd(),
        "echo" => builtin_echo(cmd),
        "exit" => builtin_exit(cmd),
        "help" => builtin_help(),
        "history" => builtin_history(cmd, history),
        "clear" => builtin_clear(),
        "export" => builtin_export(cmd),
        "unset" => builtin_unset(cmd),
        "env" => builtin_env(),
        "type" => builtin_type(cmd),
        "true" => CommandResult::Success,
        "false" => CommandResult::Error("false".to_string()),
        "test" | "[" => builtin_test(cmd),
        _ => CommandResult::NotFound(cmd.name.clone()),
    }
}

/// Change directory
fn builtin_cd(cmd: &Command) -> CommandResult {
    let target = if cmd.args.is_empty() {
        // Default to HOME
        env::var("HOME").unwrap_or_else(|_| "/".to_string())
    } else if cmd.args[0] == "-" {
        // Go to previous directory
        env::var("OLDPWD").unwrap_or_else(|_| ".".to_string())
    } else if cmd.args[0].starts_with('~') {
        // Expand tilde
        let home = env::var("HOME").unwrap_or_else(|_| "/".to_string());
        cmd.args[0].replacen('~', &home, 1)
    } else {
        cmd.args[0].clone()
    };

    // Save current directory as OLDPWD
    if let Ok(current) = env::current_dir() {
        env::set_var("OLDPWD", current);
    }

    match env::set_current_dir(&target) {
        Ok(()) => {
            // Update PWD
            if let Ok(new_pwd) = env::current_dir() {
                env::set_var("PWD", new_pwd);
            }
            CommandResult::Success
        }
        Err(e) => CommandResult::Error(format!("cd: {}: {}", target, e)),
    }
}

/// Print working directory
fn builtin_pwd() -> CommandResult {
    match env::current_dir() {
        Ok(path) => CommandResult::Output(path.display().to_string()),
        Err(e) => CommandResult::Error(format!("pwd: {}", e)),
    }
}

/// Echo arguments
fn builtin_echo(cmd: &Command) -> CommandResult {
    let mut interpret_escapes = false;
    let mut no_newline = false;
    let mut args_start = 0;

    // Parse echo flags
    for (i, arg) in cmd.args.iter().enumerate() {
        match arg.as_str() {
            "-e" => interpret_escapes = true,
            "-n" => no_newline = true,
            "-E" => interpret_escapes = false,
            _ => {
                args_start = i;
                break;
            }
        }
        args_start = i + 1;
    }

    let text = cmd.args[args_start..].join(" ");

    let output = if interpret_escapes {
        interpret_escape_sequences(&text)
    } else {
        text
    };

    let output = if no_newline { output } else { output + "\n" };

    CommandResult::Output(output.trim_end_matches('\n').to_string())
}

/// Interpret escape sequences in a string
fn interpret_escape_sequences(s: &str) -> String {
    let mut result = String::new();
    let mut chars = s.chars().peekable();

    while let Some(c) = chars.next() {
        if c == '\\' {
            if let Some(&next) = chars.peek() {
                chars.next();
                match next {
                    'n' => result.push('\n'),
                    't' => result.push('\t'),
                    'r' => result.push('\r'),
                    '\\' => result.push('\\'),
                    '0' => result.push('\0'),
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

/// Exit the shell
fn builtin_exit(cmd: &Command) -> CommandResult {
    let code = cmd.args.first().and_then(|s| s.parse().ok()).unwrap_or(0);
    CommandResult::Exit(code)
}

/// Show help
fn builtin_help() -> CommandResult {
    let help = r#"Grove Shell - DruidOS Command Interface

Built-in commands:
  cd [dir]        Change directory
  pwd             Print working directory
  echo [args]     Display arguments
  exit [code]     Exit the shell
  help            Show this help
  history [n]     Show command history
  clear           Clear the screen
  export VAR=val  Set environment variable
  unset VAR       Remove environment variable
  env             Show all environment variables
  type cmd        Show command type

The Hive:
  ? question      Ask the Hive in plain language
  anon [on|off]   Keep the Hive from acting on what this shell runs

Use 'command --help' for more information on specific commands.
"#;
    CommandResult::Output(help.to_string())
}

/// Show command history
fn builtin_history(cmd: &Command, history: &History) -> CommandResult {
    let count = cmd
        .args
        .first()
        .and_then(|s| s.parse().ok())
        .unwrap_or(history.len());

    let mut output = String::new();
    let entries = history.last_n(count);
    let start = history.len().saturating_sub(count);

    for (i, entry) in entries.iter().enumerate() {
        output.push_str(&format!("{:5}  {}\n", start + i + 1, entry));
    }

    CommandResult::Output(output.trim_end().to_string())
}

/// Clear screen
fn builtin_clear() -> CommandResult {
    // ANSI escape sequence to clear screen and move cursor to top-left
    CommandResult::Output("\x1b[2J\x1b[H".to_string())
}

/// Export environment variable
fn builtin_export(cmd: &Command) -> CommandResult {
    if cmd.args.is_empty() {
        // Show all exports
        let mut output = String::new();
        for (key, value) in env::vars() {
            output.push_str(&format!("export {}=\"{}\"\n", key, value));
        }
        return CommandResult::Output(output.trim_end().to_string());
    }

    for arg in &cmd.args {
        if let Some((key, value)) = arg.split_once('=') {
            env::set_var(key, value);
        } else {
            // Just mark as exported (in bash this tracks export status)
            // For simplicity, we just ensure the variable exists
            if env::var(arg).is_err() {
                env::set_var(arg, "");
            }
        }
    }

    CommandResult::Success
}

/// Unset environment variable
fn builtin_unset(cmd: &Command) -> CommandResult {
    for arg in &cmd.args {
        env::remove_var(arg);
    }
    CommandResult::Success
}

/// Show environment variables
fn builtin_env() -> CommandResult {
    let mut output = String::new();
    for (key, value) in env::vars() {
        output.push_str(&format!("{}={}\n", key, value));
    }
    CommandResult::Output(output.trim_end().to_string())
}

/// Show command type
fn builtin_type(cmd: &Command) -> CommandResult {
    if cmd.args.is_empty() {
        return CommandResult::Error("type: missing argument".to_string());
    }

    let mut output = String::new();
    for arg in &cmd.args {
        if is_builtin(arg) {
            output.push_str(&format!("{} is a shell builtin\n", arg));
        } else if let Some(path) = find_in_path(arg) {
            output.push_str(&format!("{} is {}\n", arg, path));
        } else {
            output.push_str(&format!("{}: not found\n", arg));
        }
    }

    CommandResult::Output(output.trim_end().to_string())
}

/// Find a command in PATH
fn find_in_path(cmd: &str) -> Option<String> {
    let path = env::var("PATH").unwrap_or_default();
    for dir in path.split(':') {
        let full_path = Path::new(dir).join(cmd);
        if full_path.exists() && full_path.is_file() {
            return Some(full_path.display().to_string());
        }
    }
    None
}

/// Test command (simplified)
fn builtin_test(cmd: &Command) -> CommandResult {
    // Handle [ ] syntax
    let args = if cmd.name == "[" {
        // Remove trailing ]
        let mut args = cmd.args.clone();
        if args.last().map(|s| s.as_str()) == Some("]") {
            args.pop();
        }
        args
    } else {
        cmd.args.clone()
    };

    if args.is_empty() {
        return CommandResult::Error("1".to_string()); // false
    }

    // Handle unary operators
    if args.len() == 2 {
        let op = &args[0];
        let arg = &args[1];

        match op.as_str() {
            "-e" => {
                // File exists
                if Path::new(arg).exists() {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            "-f" => {
                // Is regular file
                if Path::new(arg).is_file() {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            "-d" => {
                // Is directory
                if Path::new(arg).is_dir() {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            "-n" => {
                // String is non-empty
                if !arg.is_empty() {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            "-z" => {
                // String is empty
                if arg.is_empty() {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            _ => {}
        }
    }

    // Handle binary operators
    if args.len() == 3 {
        let left = &args[0];
        let op = &args[1];
        let right = &args[2];

        match op.as_str() {
            "=" | "==" => {
                if left == right {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            "!=" => {
                if left != right {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            "-eq" => {
                let l: i64 = left.parse().unwrap_or(0);
                let r: i64 = right.parse().unwrap_or(0);
                if l == r {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            "-ne" => {
                let l: i64 = left.parse().unwrap_or(0);
                let r: i64 = right.parse().unwrap_or(0);
                if l != r {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            "-lt" => {
                let l: i64 = left.parse().unwrap_or(0);
                let r: i64 = right.parse().unwrap_or(0);
                if l < r {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            "-gt" => {
                let l: i64 = left.parse().unwrap_or(0);
                let r: i64 = right.parse().unwrap_or(0);
                if l > r {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            "-le" => {
                let l: i64 = left.parse().unwrap_or(0);
                let r: i64 = right.parse().unwrap_or(0);
                if l <= r {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            "-ge" => {
                let l: i64 = left.parse().unwrap_or(0);
                let r: i64 = right.parse().unwrap_or(0);
                if l >= r {
                    return CommandResult::Success;
                } else {
                    return CommandResult::Error("1".to_string());
                }
            }
            _ => {}
        }
    }

    // Default: check if single string is non-empty
    if args.len() == 1 && !args[0].is_empty() {
        return CommandResult::Success;
    }

    CommandResult::Error("1".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_builtin() {
        assert!(is_builtin("cd"));
        assert!(is_builtin("exit"));
        assert!(!is_builtin("ls"));
        assert!(!is_builtin("cat"));
    }

    #[test]
    fn test_echo() {
        let cmd = Command::new("echo").arg("hello").arg("world");
        let result = builtin_echo(&cmd);
        assert!(matches!(result, CommandResult::Output(s) if s == "hello world"));
    }

    #[test]
    fn test_pwd() {
        let result = builtin_pwd();
        assert!(matches!(result, CommandResult::Output(_)));
    }

    #[test]
    fn test_exit() {
        let cmd = Command::new("exit").arg("42");
        let result = builtin_exit(&cmd);
        assert!(matches!(result, CommandResult::Exit(42)));
    }

    #[test]
    fn test_test_string() {
        let cmd = Command::new("test").arg("-n").arg("hello");
        let result = builtin_test(&cmd);
        assert!(result.is_success());

        let cmd = Command::new("test").arg("-z").arg("");
        let result = builtin_test(&cmd);
        assert!(result.is_success());
    }

    #[test]
    fn test_test_comparison() {
        let cmd = Command::new("test").arg("5").arg("-eq").arg("5");
        let result = builtin_test(&cmd);
        assert!(result.is_success());

        let cmd = Command::new("test").arg("5").arg("-gt").arg("3");
        let result = builtin_test(&cmd);
        assert!(result.is_success());
    }
}
