//! Black-box tests of grove running real programs: `grove -c "..."` and
//! `grove script`, checked by exit status and output.

#![cfg(unix)]

use std::path::Path;
use std::process::{Command, Output};

fn grove(script: &str) -> Output {
    grove_in(script, &std::env::temp_dir())
}

fn grove_in(script: &str, dir: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_grove"))
        .arg("-c")
        .arg(script)
        .current_dir(dir)
        .env_remove("GROVE_TEST_VAR")
        .output()
        .expect("failed to run grove")
}

fn stdout(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

#[test]
fn runs_programs_from_path_with_their_exit_status() {
    assert_eq!(grove("true").status.code(), Some(0));
    assert_eq!(grove("sh -c 'exit 7'").status.code(), Some(7));
    assert_eq!(stdout(&grove("printf '%s-%s' a b")), "a-b");
}

#[test]
fn missing_commands_exit_127_and_say_so() {
    let output = grove("definitely-not-a-command-xyz");
    assert_eq!(output.status.code(), Some(127));
    assert!(stderr(&output).contains("definitely-not-a-command-xyz: command not found"));
}

#[test]
fn a_program_killed_by_a_signal_exits_128_plus_signal() {
    assert_eq!(grove("sh -c 'kill -TERM $$'").status.code(), Some(143));
}

#[test]
fn pipelines_connect_stdout_to_stdin_and_keep_quoting() {
    assert_eq!(
        stdout(&grove("printf 'b\\na\\n' | sort | head -n 1")),
        "a\n"
    );
    assert_eq!(stdout(&grove("printf 'x y\\nz\\n' | grep 'x y'")), "x y\n");
    // The status of a pipeline is its last command's.
    assert_eq!(grove("false | true").status.code(), Some(0));
    assert_eq!(grove("true | false").status.code(), Some(1));
}

#[test]
fn builtins_take_part_in_pipelines() {
    assert_eq!(stdout(&grove("echo hello | tr a-z A-Z")), "HELLO\n");
}

#[test]
fn and_or_and_sequences() {
    assert_eq!(stdout(&grove("true && echo yes")), "yes\n");
    assert_eq!(stdout(&grove("false && echo no")), "");
    assert_eq!(grove("false && echo no").status.code(), Some(1));
    assert_eq!(stdout(&grove("false || echo recovered")), "recovered\n");
    assert_eq!(stdout(&grove("echo one; echo two")), "one\ntwo\n");
    assert_eq!(stdout(&grove("echo 'a;b' \"c&&d\"")), "a;b c&&d\n");
}

#[test]
fn redirections() {
    let dir = tempfile::tempdir().unwrap();
    let out = grove_in(
        "echo first > f.txt; echo second >> f.txt; cat < f.txt",
        dir.path(),
    );
    assert_eq!(stdout(&out), "first\nsecond\n");

    let err = grove_in("ls /definitely/missing 2> err.txt; cat err.txt", dir.path());
    assert!(stdout(&err).contains("definitely/missing"));

    let merged = grove("ls /definitely/missing 2>&1 | grep -c missing");
    assert_eq!(stdout(&merged), "1\n");
}

#[test]
fn variables_and_status_expand_but_not_inside_single_quotes() {
    assert_eq!(
        stdout(&grove(
            "export GROVE_TEST_VAR=leaf; echo $GROVE_TEST_VAR ${GROVE_TEST_VAR}s"
        )),
        "leaf leafs\n"
    );
    assert_eq!(stdout(&grove("echo '$HOME'")), "$HOME\n");
    assert_eq!(stdout(&grove("false; echo $?")), "1\n");
    assert_eq!(
        stdout(&grove("echo ~")),
        format!("{}\n", std::env::var("HOME").unwrap())
    );
}

#[test]
fn exported_variables_and_cd_reach_child_programs() {
    assert_eq!(
        stdout(&grove(
            "export GROVE_TEST_VAR=seen; sh -c 'echo $GROVE_TEST_VAR'"
        )),
        "seen\n"
    );
    assert_eq!(
        stdout(&grove("GROVE_TEST_VAR=once sh -c 'echo $GROVE_TEST_VAR'")),
        "once\n"
    );
    assert_eq!(stdout(&grove("cd /; sh -c pwd")), "/\n");
}

#[test]
fn globs_expand_to_matching_files_and_stay_literal_otherwise() {
    let dir = tempfile::tempdir().unwrap();
    for name in ["b.txt", "a.txt", "c.log"] {
        std::fs::write(dir.path().join(name), "").unwrap();
    }
    assert_eq!(stdout(&grove_in("echo *.txt", dir.path())), "a.txt b.txt\n");
    assert_eq!(stdout(&grove_in("echo *.none", dir.path())), "*.none\n");
    assert_eq!(stdout(&grove_in("echo '*.txt'", dir.path())), "*.txt\n");
}

#[test]
fn background_jobs_do_not_block_the_shell() {
    let started = std::time::Instant::now();
    // (Redirected: a background job holding the test's stdout/stderr pipes would
    // keep `output()` waiting for it, in any shell.)
    let output = grove("sleep 5 > /dev/null 2>&1 & echo after");
    assert!(stdout(&output).contains("after"));
    assert!(started.elapsed() < std::time::Duration::from_secs(4));
}

#[test]
fn runs_script_files() {
    let dir = tempfile::tempdir().unwrap();
    let script = dir.path().join("script.grove");
    std::fs::write(&script, "# a comment\necho from-script\nfalse\necho $?\n").unwrap();

    let output = Command::new(env!("CARGO_BIN_EXE_grove"))
        .arg(&script)
        .output()
        .unwrap();

    assert_eq!(stdout(&output), "from-script\n1\n");
}
