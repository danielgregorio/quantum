//! Deciding whether an execution is dangerous.
//!
//! Judged on the program actually run and its parsed arguments, with paths
//! resolved against the process's working directory — never on text found
//! somewhere in a command line. `grep "rm -rf /"` or `echo rm -rf /` only
//! mention a command; `sh -c "rm -rf /"` is harmless itself, and the `rm` it
//! starts is an execution of its own that gets judged when it happens.
//! Conversely `cd / && rm -rf *` never contains the text "rm -rf /" at all:
//! the shell expands `*` to `bin boot etc ...`, which only resolve to
//! top-level directories through the working directory.

use std::path::{Component, Path, PathBuf};

/// A dangerous execution: which intercepted command, and why.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Finding {
    pub command: String,
    pub reason: String,
}

/// Directories whose immediate children are each a whole subsystem (a
/// user's home, /etc/nginx, /usr/lib, /var/lib): removing one wholesale is
/// dangerous, while anything deeper (/home/me/project/node_modules,
/// /var/lib/apt/lists) is routine.
const SYSTEM_DIRS: &[&str] = &[
    "/bin", "/boot", "/etc", "/home", "/lib", "/lib32", "/lib64", "/opt", "/root", "/sbin", "/srv",
    "/usr", "/var",
];

/// Character devices that are safe to write to with `dd of=`.
const HARMLESS_DEVICES: &[&str] = &[
    "/dev/null",
    "/dev/zero",
    "/dev/full",
    "/dev/random",
    "/dev/urandom",
    "/dev/stdout",
    "/dev/stderr",
    "/dev/tty",
];

/// Judge one execution. `program` is the executable that ran (the kernel's
/// `exe`, or argv[0] when that isn't known), `argv` includes argv[0], and
/// only commands listed in `intercept` are judged at all.
pub fn assess(
    program: &str,
    argv: &[String],
    cwd: Option<&Path>,
    intercept: &[String],
) -> Option<Finding> {
    let name = Path::new(program).file_name()?.to_str()?;
    let command = intercept
        .iter()
        .find(|c| name == c.as_str() || name.starts_with(&format!("{c}.")))?;
    let args = argv.get(1..).unwrap_or_default();

    let reason = match command.as_str() {
        "rm" => rm(args, cwd),
        "chmod" | "chown" => recursive_on_system_path(args, cwd, command),
        "dd" => dd(args),
        "mkfs" => device_argument(args).map(|dev| format!("creates a filesystem on {dev}")),
        "fdisk" => fdisk(args),
        "parted" => parted(args),
        "mv" => mv(args, cwd),
        _ => None,
    }?;

    Some(Finding {
        command: command.clone(),
        reason,
    })
}

/// Arguments split into options and operands, honoring `--`.
fn split_args(args: &[String]) -> (Vec<&str>, Vec<&str>) {
    let mut options = Vec::new();
    let mut operands = Vec::new();
    let mut only_operands = false;
    for arg in args {
        if only_operands {
            operands.push(arg.as_str());
        } else if arg == "--" {
            only_operands = true;
        } else if arg.starts_with('-') && arg.len() > 1 {
            options.push(arg.as_str());
        } else {
            operands.push(arg.as_str());
        }
    }
    (options, operands)
}

/// `--recursive`, or a short option cluster containing one of `letters`
/// (`-rf` for rm). chmod and chown only take `-R`: to chmod, `-rwx` is a mode.
fn is_recursive(options: &[&str], letters: &[char]) -> bool {
    options.iter().any(|o| {
        *o == "--recursive"
            || (!o.starts_with("--") && o[1..].chars().any(|c| letters.contains(&c)))
    })
}

fn rm(args: &[String], cwd: Option<&Path>) -> Option<String> {
    let (options, operands) = split_args(args);
    if options.contains(&"--no-preserve-root") {
        return Some("deletes with root protection explicitly turned off".to_string());
    }
    if !is_recursive(&options, &['r', 'R']) {
        return None;
    }
    system_path(&operands, cwd).map(|path| format!("recursively deletes {}", path.display()))
}

fn recursive_on_system_path(args: &[String], cwd: Option<&Path>, command: &str) -> Option<String> {
    let (options, operands) = split_args(args);
    if !is_recursive(&options, &['R']) {
        return None;
    }
    // The first operand is the mode / owner, the rest are paths.
    let paths = operands.get(1..).unwrap_or_default();
    let verb = if command == "chmod" {
        "changes permissions"
    } else {
        "changes ownership"
    };
    system_path(paths, cwd).map(|path| format!("recursively {verb} of {}", path.display()))
}

fn dd(args: &[String]) -> Option<String> {
    args.iter()
        .filter_map(|a| a.strip_prefix("of="))
        .find(|target| target.starts_with("/dev/") && !HARMLESS_DEVICES.contains(target))
        .map(|device| format!("writes directly to {device}"))
}

fn fdisk(args: &[String]) -> Option<String> {
    if args.iter().any(|a| a == "-l" || a == "--list") {
        return None;
    }
    device_argument(args).map(|dev| format!("repartitions {dev}"))
}

fn parted(args: &[String]) -> Option<String> {
    if args.iter().any(|a| a == "-l" || a == "--list") || args.last().is_some_and(|a| a == "print")
    {
        return None;
    }
    device_argument(args).map(|dev| format!("repartitions {dev}"))
}

fn mv(args: &[String], cwd: Option<&Path>) -> Option<String> {
    let (_, operands) = split_args(args);
    let (destination, sources) = operands.split_last()?;
    if *destination == "/dev/null" {
        return Some("moves files to /dev/null".to_string());
    }
    system_path(sources, cwd).map(|path| format!("moves {} away", path.display()))
}

fn device_argument(args: &[String]) -> Option<&str> {
    args.iter()
        .map(String::as_str)
        .find(|a| a.starts_with("/dev/"))
}

/// The first operand that resolves to `/`, a top-level directory, or a
/// direct child of one of [`SYSTEM_DIRS`].
fn system_path(operands: &[&str], cwd: Option<&Path>) -> Option<PathBuf> {
    operands
        .iter()
        .filter_map(|operand| normalize(operand, cwd))
        .find(|path| is_system_path(path))
}

fn is_system_path(path: &Path) -> bool {
    let depth = path.components().count() - 1; // minus the root
    match depth {
        0 | 1 => true,
        2 => path
            .parent()
            .and_then(Path::to_str)
            .is_some_and(|parent| SYSTEM_DIRS.contains(&parent)),
        _ => false,
    }
}

/// Lexically normalize `path`, relative to `cwd` if it isn't absolute:
/// `.` dropped, `..` removes the previous component (never above `/`).
/// Symlinks aren't resolved — the path may not even exist. A relative path
/// with no known working directory can't be placed, so it's `None`.
fn normalize(path: &str, cwd: Option<&Path>) -> Option<PathBuf> {
    let path = Path::new(path);
    let joined = if path.is_absolute() {
        path.to_path_buf()
    } else {
        cwd.filter(|c| c.is_absolute())?.join(path)
    };

    let mut normalized = PathBuf::from("/");
    for component in joined.components() {
        match component {
            Component::Normal(part) => normalized.push(part),
            Component::ParentDir => {
                normalized.pop();
            }
            Component::RootDir | Component::CurDir | Component::Prefix(_) => {}
        }
    }
    Some(normalized)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn intercept() -> Vec<String> {
        [
            "rm", "chmod", "chown", "dd", "mkfs", "fdisk", "parted", "mv",
        ]
        .iter()
        .map(|s| s.to_string())
        .collect()
    }

    fn judge(program: &str, cmdline: &str, cwd: &str) -> Option<String> {
        let argv: Vec<String> = cmdline.split_whitespace().map(str::to_string).collect();
        assess(program, &argv, Some(Path::new(cwd)), &intercept()).map(|f| f.reason)
    }

    #[test]
    fn recursive_deletes_of_system_paths_are_dangerous() {
        for (cmdline, cwd, reason) in [
            ("rm -rf /", "/", "recursively deletes /"),
            ("rm -r /etc", "/", "recursively deletes /etc"),
            ("rm -fr /home/alice", "/", "recursively deletes /home/alice"),
            (
                "rm --recursive --force /usr/lib",
                "/",
                "recursively deletes /usr/lib",
            ),
            ("rm -R /data", "/", "recursively deletes /data"),
            ("rm -rf -- /boot", "/", "recursively deletes /boot"),
        ] {
            assert_eq!(
                judge("/usr/bin/rm", cmdline, cwd).as_deref(),
                Some(reason),
                "{cmdline}"
            );
        }
    }

    #[test]
    fn relative_paths_resolve_against_the_working_directory() {
        // `cd / && rm -rf *`: the shell already expanded the glob.
        assert_eq!(
            judge("/usr/bin/rm", "rm -rf bin boot etc", "/").as_deref(),
            Some("recursively deletes /bin")
        );
        assert_eq!(
            judge("/usr/bin/rm", "rm -rf nginx", "/etc").as_deref(),
            Some("recursively deletes /etc/nginx")
        );
        assert_eq!(
            judge("/usr/bin/rm", "rm -rf ../..", "/home/alice").as_deref(),
            Some("recursively deletes /")
        );
        // The lab's harmless canary: normalizes to /etc, deletes nothing.
        assert_eq!(
            judge("/usr/bin/rm", "rm -rf canary/..", "/etc").as_deref(),
            Some("recursively deletes /etc")
        );
    }

    #[test]
    fn routine_deletes_are_not_dangerous() {
        for (cmdline, cwd) in [
            ("rm -rf /tmp/build", "/"),
            ("rm -rf node_modules", "/home/alice/project"),
            ("rm -rf /var/lib/apt/lists/partial", "/"),
            ("rm -rf /etc/nginx/sites-enabled", "/"),
            ("rm /etc/motd", "/"),           // not recursive
            ("rm -f -- -rf", "/home/alice"), // "-rf" is a file name here
        ] {
            assert_eq!(judge("/usr/bin/rm", cmdline, cwd), None, "{cmdline}");
        }
    }

    #[test]
    fn mentioning_a_command_is_not_running_it() {
        assert_eq!(
            judge("/usr/bin/grep", "grep -c rm -rf / /dev/null", "/"),
            None
        );
        assert_eq!(judge("/usr/bin/echo", "echo rm -rf /", "/"), None);
        assert_eq!(judge("/usr/bin/dash", "sh -c rm -rf /", "/"), None);
    }

    #[test]
    fn the_program_run_counts_not_what_argv0_claims() {
        // `exec -a rm sleep 60` runs sleep; `exec -a ls rm -rf /` runs rm.
        assert_eq!(judge("/usr/bin/sleep", "rm -rf /", "/"), None);
        assert_eq!(
            judge("/usr/bin/rm", "ls -rf /", "/").as_deref(),
            Some("recursively deletes /")
        );
    }

    #[test]
    fn no_preserve_root_is_always_dangerous() {
        assert!(judge("/usr/bin/rm", "rm --no-preserve-root /tmp/x", "/").is_some());
    }

    #[test]
    fn recursive_permission_and_ownership_changes_on_system_paths() {
        assert_eq!(
            judge("/usr/bin/chmod", "chmod -R 777 /etc", "/").as_deref(),
            Some("recursively changes permissions of /etc")
        );
        assert_eq!(
            judge("/usr/bin/chown", "chown -R alice: /usr", "/").as_deref(),
            Some("recursively changes ownership of /usr")
        );
        assert_eq!(
            judge("/usr/bin/chmod", "chmod -R 755 /home/alice/project", "/"),
            None
        );
        assert_eq!(judge("/usr/bin/chmod", "chmod 777 /etc", "/"), None);
        assert_eq!(judge("/usr/bin/chmod", "chmod -rwx /etc/nginx", "/"), None);
    }

    #[test]
    fn disk_level_commands() {
        assert_eq!(
            judge("/usr/bin/dd", "dd if=/dev/zero of=/dev/vda bs=1M", "/").as_deref(),
            Some("writes directly to /dev/vda")
        );
        assert_eq!(
            judge("/usr/bin/dd", "dd if=/dev/vda of=/tmp/disk.img", "/"),
            None
        );
        assert_eq!(
            judge(
                "/usr/bin/dd",
                "dd if=/dev/urandom of=/dev/null count=1",
                "/"
            ),
            None
        );

        assert_eq!(
            judge("/usr/sbin/mkfs.ext4", "mkfs.ext4 /dev/sdb1", "/").as_deref(),
            Some("creates a filesystem on /dev/sdb1")
        );
        assert_eq!(
            judge("/usr/sbin/mkfs.ext4", "mkfs.ext4 disk.img", "/tmp"),
            None
        );

        assert!(judge("/usr/sbin/fdisk", "fdisk /dev/sda", "/").is_some());
        assert_eq!(judge("/usr/sbin/fdisk", "fdisk -l /dev/sda", "/"), None);
        assert!(judge("/usr/sbin/parted", "parted /dev/sda mklabel gpt", "/").is_some());
        assert_eq!(
            judge("/usr/sbin/parted", "parted /dev/sda print", "/"),
            None
        );
    }

    #[test]
    fn moving_system_paths_away() {
        assert_eq!(
            judge("/usr/bin/mv", "mv /etc /etc.bak", "/").as_deref(),
            Some("moves /etc away")
        );
        assert_eq!(
            judge("/usr/bin/mv", "mv notes.txt /dev/null", "/home/alice").as_deref(),
            Some("moves files to /dev/null")
        );
        assert_eq!(judge("/usr/bin/mv", "mv a.txt b.txt", "/home/alice"), None);
    }

    #[test]
    fn commands_not_intercepted_are_not_judged() {
        let argv: Vec<String> = ["rm", "-rf", "/"].iter().map(|s| s.to_string()).collect();
        assert_eq!(
            assess(
                "/usr/bin/rm",
                &argv,
                Some(Path::new("/")),
                &["dd".to_string()]
            ),
            None
        );
    }

    #[test]
    fn relative_paths_without_a_working_directory_are_not_guessed() {
        let argv: Vec<String> = ["rm", "-rf", "etc"].iter().map(|s| s.to_string()).collect();
        assert_eq!(assess("/usr/bin/rm", &argv, None, &intercept()), None);
    }
}
