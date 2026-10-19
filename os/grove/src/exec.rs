//! Running parsed command lists: builtins in the shell itself, everything
//! else as child processes wired together with pipes and redirections.

use crate::builtins;
use crate::command::{Command, CommandResult};
use crate::expand::{expand_single, expand_word};
use crate::parser::{Connector, ListItem, Pipeline, RedirectKind, SimpleCommand};
use crate::shell::Shell;
use std::fs::{File, OpenOptions};
use std::io::{self, Write};
use std::os::fd::{AsFd, FromRawFd, OwnedFd};
use std::os::unix::process::{CommandExt, ExitStatusExt};
use std::process::{Child, ExitStatus, Stdio};
use std::thread::JoinHandle;

/// A background pipeline the shell hasn't reported as finished yet.
pub(crate) struct Job {
    id: usize,
    text: String,
    children: Vec<Child>,
}

/// A simple command after expansion.
struct Expanded {
    assignments: Vec<(String, String)>,
    argv: Vec<String>,
    redirects: Vec<(RedirectKind, Option<String>)>,
}

/// One stage of a running pipeline.
enum Stage {
    Running(Child),
    Finished(i32),
}

/// Where a stage's output goes.
enum Output {
    Inherit,
    File(File),
    Pipe(OwnedFd),
}

impl Output {
    fn stdio(&self) -> io::Result<Stdio> {
        Ok(match self {
            Output::Inherit => Stdio::inherit(),
            Output::File(file) => Stdio::from(file.try_clone()?),
            Output::Pipe(fd) => Stdio::from(fd.try_clone()?),
        })
    }

    /// The same destination, for `2>&1`.
    fn duplicate(&self) -> io::Result<Stdio> {
        match self {
            Output::Inherit => Ok(Stdio::from(io::stdout().as_fd().try_clone_to_owned()?)),
            other => other.stdio(),
        }
    }
}

impl Shell {
    /// Run a parsed line, honoring `&&`, `||` and `&`.
    pub(crate) fn run_list(&mut self, items: &[ListItem]) {
        let mut previous = Connector::Sequence;
        for item in items {
            if !self.is_running() {
                break;
            }
            let skip = match previous {
                Connector::And => self.last_exit_code != 0,
                Connector::Or => self.last_exit_code == 0,
                _ => false,
            };
            previous = item.connector;
            if skip {
                continue;
            }
            if item.connector == Connector::Background {
                self.run_in_background(&item.pipeline);
                self.last_exit_code = 0;
            } else {
                self.last_exit_code = self.run_pipeline(&item.pipeline);
            }
        }
    }

    fn run_pipeline(&mut self, pipeline: &Pipeline) -> i32 {
        let commands: Vec<Expanded> = pipeline.commands.iter().map(|c| self.expand(c)).collect();

        // A lone builtin runs in the shell itself, so `cd`, `export` and
        // `exit` affect it; a bare `NAME=value` sets the variable.
        if let [only] = commands.as_slice() {
            if only.argv.is_empty() {
                for (name, value) in &only.assignments {
                    std::env::set_var(name, value);
                }
                return match open_redirects(only) {
                    Ok(_) => 0,
                    Err(status) => status,
                };
            }
            if builtins::is_builtin(&only.argv[0]) {
                let (stdout, stderr) = match open_redirects(only) {
                    Ok(targets) => targets,
                    Err(status) => return status,
                };
                return self.run_builtin(only, stdout, stderr, &mut Vec::new());
            }
        }

        let mut feeders = Vec::new();
        let stages = self.spawn_pipeline(&commands, false, &mut feeders);
        let mut status = 0;
        for stage in stages {
            status = match stage {
                Stage::Running(mut child) => match child.wait() {
                    Ok(exit) => exit_code(exit),
                    Err(e) => {
                        eprintln!("grove: wait failed: {}", e);
                        1
                    }
                },
                Stage::Finished(code) => code,
            };
        }
        for feeder in feeders {
            let _ = feeder.join();
        }
        status
    }

    fn run_in_background(&mut self, pipeline: &Pipeline) {
        let commands: Vec<Expanded> = pipeline.commands.iter().map(|c| self.expand(c)).collect();
        let mut feeders = Vec::new();
        let children: Vec<Child> = self
            .spawn_pipeline(&commands, true, &mut feeders)
            .into_iter()
            .filter_map(|stage| match stage {
                Stage::Running(child) => Some(child),
                Stage::Finished(_) => None,
            })
            .collect();
        if children.is_empty() {
            return;
        }

        self.next_job_id += 1;
        let job = Job {
            id: self.next_job_id,
            text: commands
                .iter()
                .map(|c| c.argv.join(" "))
                .collect::<Vec<_>>()
                .join(" | "),
            children,
        };
        if self.is_interactive() {
            let last_pid = job.children.last().map_or(0, Child::id);
            println!("[{}] {}", job.id, last_pid);
        }
        self.jobs.push(job);
    }

    /// Report background jobs that have finished (before each prompt).
    pub(crate) fn reap_jobs(&mut self) {
        let interactive = self.is_interactive();
        self.jobs.retain_mut(|job| {
            let done = job
                .children
                .iter_mut()
                .all(|child| matches!(child.try_wait(), Ok(Some(_))));
            if done && interactive {
                println!("[{}]  Done    {}", job.id, job.text);
            }
            !done
        });
    }

    fn expand(&self, command: &SimpleCommand) -> Expanded {
        let status = self.last_exit_code;
        Expanded {
            assignments: command
                .assignments
                .iter()
                .map(|(name, value)| (name.clone(), expand_single(value, status)))
                .collect(),
            argv: command
                .words
                .iter()
                .flat_map(|word| expand_word(word, status))
                .collect(),
            redirects: command
                .redirects
                .iter()
                .map(|r| (r.kind, r.target.as_ref().map(|t| expand_single(t, status))))
                .collect(),
        }
    }

    fn spawn_pipeline(
        &mut self,
        commands: &[Expanded],
        background: bool,
        feeders: &mut Vec<JoinHandle<()>>,
    ) -> Vec<Stage> {
        let mut stages = Vec::new();
        let mut previous_read: Option<OwnedFd> = None;

        for (index, command) in commands.iter().enumerate() {
            let last = index + 1 == commands.len();
            let input = previous_read.take();

            // The pipe to the next stage, if there is one.
            let (next_read, pipe_write) = if last {
                (None, None)
            } else {
                match pipe() {
                    Ok((read, write)) => (Some(read), Some(write)),
                    Err(e) => {
                        eprintln!("grove: pipe: {}", e);
                        stages.push(Stage::Finished(1));
                        break;
                    }
                }
            };
            previous_read = next_read;

            let (file_out, file_err) = match open_redirects(command) {
                Ok(targets) => targets,
                Err(status) => {
                    stages.push(Stage::Finished(status));
                    continue;
                }
            };
            let stdout = match (file_out, pipe_write) {
                (Some(file), _) => Output::File(file),
                (None, Some(fd)) => Output::Pipe(fd),
                (None, None) => Output::Inherit,
            };

            if command.argv.is_empty() {
                stages.push(Stage::Finished(0));
                continue;
            }
            if builtins::is_builtin(&command.argv[0]) {
                let status = self.run_builtin(command, stdout, file_err, feeders);
                stages.push(Stage::Finished(status));
                continue;
            }

            stages.push(self.spawn(command, input, stdout, file_err, background));
        }
        stages
    }

    fn spawn(
        &self,
        command: &Expanded,
        input: Option<OwnedFd>,
        stdout: Output,
        stderr_file: Option<Stderr>,
        background: bool,
    ) -> Stage {
        let name = &command.argv[0];
        let mut process = std::process::Command::new(name);
        process
            .args(&command.argv[1..])
            .envs(command.assignments.iter().cloned());

        let stdin_file = command
            .redirects
            .iter()
            .rev()
            .find(|(kind, _)| *kind == RedirectKind::In)
            .and_then(|(_, target)| target.as_ref());
        let stdin = match (stdin_file, input) {
            (Some(path), _) => match File::open(path) {
                Ok(file) => Stdio::from(file),
                Err(e) => {
                    eprintln!("grove: {}: {}", path, e);
                    return Stage::Finished(1);
                }
            },
            (None, Some(fd)) => Stdio::from(fd),
            (None, None) if background => Stdio::null(),
            (None, None) => Stdio::inherit(),
        };
        process.stdin(stdin);

        let wired = stdout.stdio().and_then(|out| {
            process.stdout(out);
            match stderr_file {
                Some(Stderr::File(file)) => process.stderr(Stdio::from(file)),
                Some(Stderr::ToStdout) => process.stderr(stdout.duplicate()?),
                None => process.stderr(Stdio::inherit()),
            };
            Ok(())
        });
        if let Err(e) = wired {
            eprintln!("grove: {}: {}", name, e);
            return Stage::Finished(1);
        }

        if self.is_interactive() {
            // No job control yet: a stopped foreground job would leave the
            // shell waiting forever, so Ctrl-Z is ignored by what it runs.
            // SAFETY: signal(2) is async-signal-safe.
            unsafe {
                process.pre_exec(|| {
                    libc::signal(libc::SIGTSTP, libc::SIG_IGN);
                    Ok(())
                });
            }
        }

        let spawned = process.spawn();
        // Drop the parent's copies of the pipe ends now, or readers
        // downstream never see end-of-file.
        drop(process);
        drop(stdout);
        match spawned {
            Ok(child) => Stage::Running(child),
            Err(e) if e.kind() == io::ErrorKind::NotFound => {
                eprintln!("grove: {}: command not found", name);
                self.not_found.borrow_mut().push(name.clone());
                Stage::Finished(127)
            }
            Err(e) if e.kind() == io::ErrorKind::PermissionDenied => {
                eprintln!("grove: {}: permission denied", name);
                Stage::Finished(126)
            }
            Err(e) => {
                eprintln!("grove: {}: {}", name, e);
                Stage::Finished(126)
            }
        }
    }

    /// Run a builtin with its output going to `stdout` and its errors to
    /// `stderr` (a redirection) or the terminal. Returns its status.
    fn run_builtin(
        &mut self,
        command: &Expanded,
        stdout: impl Into<Destination>,
        stderr: Option<Stderr>,
        feeders: &mut Vec<JoinHandle<()>>,
    ) -> i32 {
        let mut builtin = Command::new(&command.argv[0]);
        builtin.args = command.argv[1..].to_vec();
        let result = builtins::execute(&builtin, &self.history);

        let (text, error, status) = match result {
            CommandResult::Success => (None, None, 0),
            CommandResult::Output(text) => (Some(text + "\n"), None, 0),
            CommandResult::Error(e) => match e.parse::<i32>() {
                Ok(code) => (None, None, code),
                Err(_) => (None, Some(format!("grove: {}\n", e)), 1),
            },
            CommandResult::Exit(code) => {
                self.exit(code);
                (None, None, code)
            }
            CommandResult::NotFound(name) => (
                None,
                Some(format!("grove: {}: command not found\n", name)),
                127,
            ),
        };

        if let Some(text) = text {
            match stdout.into() {
                Destination::Output(Output::Inherit) | Destination::Terminal => {
                    print!("{}", text);
                    let _ = io::stdout().flush();
                }
                Destination::Output(Output::File(mut file)) | Destination::File(mut file) => {
                    let _ = file.write_all(text.as_bytes());
                }
                Destination::Output(Output::Pipe(fd)) => {
                    // A thread, since the reader may not drain the pipe
                    // until after we start waiting on it.
                    feeders.push(std::thread::spawn(move || {
                        let _ = File::from(fd).write_all(text.as_bytes());
                    }));
                }
            }
        }
        if let Some(error) = error {
            match stderr {
                Some(Stderr::File(mut file)) => {
                    let _ = file.write_all(error.as_bytes());
                }
                _ => eprint!("{}", error),
            }
        }
        status
    }
}

/// Where a builtin's output goes: a pipeline stage's output, or the
/// redirection/terminal of a builtin running on its own.
enum Destination {
    Output(Output),
    File(File),
    Terminal,
}

impl From<Output> for Destination {
    fn from(output: Output) -> Self {
        Destination::Output(output)
    }
}

impl From<Option<File>> for Destination {
    fn from(file: Option<File>) -> Self {
        match file {
            Some(file) => Destination::File(file),
            None => Destination::Terminal,
        }
    }
}

/// Where stderr goes when redirected.
enum Stderr {
    File(File),
    ToStdout,
}

/// Open a command's output redirections (the last of each kind wins, as in
/// other shells; earlier ones are still created). Input redirection is
/// opened when spawning. On failure the error is reported and the status
/// returned.
fn open_redirects(command: &Expanded) -> Result<(Option<File>, Option<Stderr>), i32> {
    let mut stdout = None;
    let mut stderr = None;
    for (kind, target) in &command.redirects {
        let open = |append: bool| -> Result<File, i32> {
            let path = target.as_deref().unwrap_or_default();
            OpenOptions::new()
                .write(true)
                .create(true)
                .append(append)
                .truncate(!append)
                .open(path)
                .map_err(|e| {
                    eprintln!("grove: {}: {}", path, e);
                    1
                })
        };
        match kind {
            RedirectKind::Out => stdout = Some(open(false)?),
            RedirectKind::Append => stdout = Some(open(true)?),
            RedirectKind::ErrOut => stderr = Some(Stderr::File(open(false)?)),
            RedirectKind::ErrAppend => stderr = Some(Stderr::File(open(true)?)),
            RedirectKind::ErrToOut => stderr = Some(Stderr::ToStdout),
            RedirectKind::In => {}
        }
    }
    Ok((stdout, stderr))
}

/// A pipe whose ends are close-on-exec, so children only inherit the end
/// that's explicitly wired to their stdin/stdout.
fn pipe() -> io::Result<(OwnedFd, OwnedFd)> {
    let mut fds = [0; 2];
    // SAFETY: pipe2 fills both descriptors on success; each is owned once.
    unsafe {
        if libc::pipe2(fds.as_mut_ptr(), libc::O_CLOEXEC) != 0 {
            return Err(io::Error::last_os_error());
        }
        Ok((OwnedFd::from_raw_fd(fds[0]), OwnedFd::from_raw_fd(fds[1])))
    }
}

/// Exit code as shells report it: the program's own, or 128 + the signal
/// that killed it.
fn exit_code(status: ExitStatus) -> i32 {
    status
        .code()
        .unwrap_or_else(|| 128 + status.signal().unwrap_or(0))
}

/// Set when Ctrl-C reaches the shell itself (not a foreground program), for
/// the few things grove waits on in-process - an answer from the Hive.
static INTERRUPTED: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

/// Whether Ctrl-C was pressed since the last `clear_interrupt`.
pub(crate) fn interrupted() -> bool {
    INTERRUPTED.load(std::sync::atomic::Ordering::Relaxed)
}

pub(crate) fn clear_interrupt() {
    INTERRUPTED.store(false, std::sync::atomic::Ordering::Relaxed);
}

/// In an interactive shell, Ctrl-C and Ctrl-\ should stop the running
/// program, not grove. A handler (rather than ignoring the signals) is reset
/// to the default in children by exec, so they still die.
pub(crate) fn install_interactive_signal_handlers() {
    // Only records the signal: an atomic store is async-signal-safe.
    extern "C" fn note_interrupt(signal: libc::c_int) {
        if signal == libc::SIGINT {
            INTERRUPTED.store(true, std::sync::atomic::Ordering::Relaxed);
        }
    }
    // SAFETY: installing a handler that only stores to an atomic; sigaction
    // is set up fully (empty mask, no flags beyond SA_RESTART).
    unsafe {
        let mut action: libc::sigaction = std::mem::zeroed();
        action.sa_sigaction = note_interrupt as extern "C" fn(libc::c_int) as libc::sighandler_t;
        action.sa_flags = libc::SA_RESTART;
        libc::sigemptyset(&mut action.sa_mask);
        libc::sigaction(libc::SIGINT, &action, std::ptr::null_mut());
        libc::sigaction(libc::SIGQUIT, &action, std::ptr::null_mut());
    }
}
