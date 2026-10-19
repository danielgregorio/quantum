//! Grove shell binary
//!
//! The main entry point for the DruidOS shell.

use grove::Shell;
use std::env;
use std::process;

fn main() {
    let args: Vec<String> = env::args().collect();

    // Parse command line options
    let mut shell = if args.len() > 1 {
        match args[1].as_str() {
            "-c" => {
                // Execute command and exit
                if args.len() > 2 {
                    let mut shell = Shell::non_interactive();
                    shell.execute_line(&args[2..].join(" "));
                    process::exit(shell.exit_code());
                } else {
                    eprintln!("grove: -c requires an argument");
                    process::exit(1);
                }
            }
            "--help" | "-h" => {
                print_help();
                process::exit(0);
            }
            "--version" | "-v" => {
                println!("Grove shell version {}", grove::VERSION);
                process::exit(0);
            }
            script => match std::fs::read_to_string(script) {
                Ok(contents) => {
                    let mut shell = Shell::non_interactive();
                    shell.execute_script(&contents);
                    process::exit(shell.exit_code());
                }
                Err(e) => {
                    eprintln!("grove: {}: {}", script, e);
                    process::exit(127);
                }
            },
        }
    } else {
        Shell::new()
    };

    // Run the interactive shell
    shell.run();

    process::exit(shell.exit_code());
}

fn print_help() {
    println!(
        r#"Grove shell - DruidOS command interpreter

Usage: grove [options] [script]

Options:
  -c COMMAND    Execute COMMAND and exit
  -h, --help    Show this help message
  -v, --version Show version information

When invoked without arguments, Grove starts an interactive shell; given a
file, it runs it one line at a time.

Command lines: programs from PATH, pipes (|), lists (; && ||), background
jobs (&), redirections (< > >> 2> 2>> 2>&1), NAME=value assignments, $VAR,
${{VAR}}, $?, ~ and globs (* ? [...]).

Built-in commands:
  cd, pwd, echo, exit, help, history, clear,
  export, unset, env, type, test, true, false

The Hive (DruidOS's assistant):
  ? QUESTION      Ask the Hive in plain language
  anon [on|off]   Keep the Hive from acting on what this shell runs
  Notices about the system (a crashed service, a full disk) appear at the
  prompt.

For more information, run 'help' in the shell.
"#
    );
}
